import os
import io
import json
import re
import uuid
import traceback
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import httpx

import config
import workflow as wf
import export_service as es
import theme_service as ts
import dashboard_service as ds
import reports_service as rs
import workflow_engine as we
from middleware import limiter, rate_limit_exceeded_handler, MaxBodySizeMiddleware
from slowapi.errors import RateLimitExceeded
from memory.memory_manager import get_memory_manager
from database import init_db, SessionLocal
from chat_model import ChatMessage
import preference_model
from user_model import User
from auth_service import hash_password, verify_password, create_token, get_current_user

app = FastAPI(title=config.API_TITLE)

# ── Middleware (order matters: size check → rate limit → CORS) ────
app.add_middleware(MaxBodySizeMiddleware, max_size=config.MAX_UPLOAD_SIZE_BYTES)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_origin_regex=config.CORS_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

DEEPSEEK_BASE_URL = config.DEEPSEEK_BASE_URL
sessions: dict[str, dict] = {}


@app.on_event("startup")
async def on_startup():
    init_db()


# ── File Upload Validation (T4) ───────────────────────────────────


def _validate_excel_upload(file: UploadFile) -> None:
    """Validate uploaded file: extension, MIME type, and size.

    Raises HTTPException on failure — no return value.
    """
    errors: list[str] = []

    # 1. Extension check
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in config.ALLOWED_EXTENSIONS:
        errors.append(f"不支持的文件类型 '{ext}'，仅接受 .xlsx / .xls")

    # 2. MIME type check
    content_type = file.content_type or ""
    if content_type and content_type not in config.ALLOWED_MIME_TYPES:
        errors.append(f"无效的文件格式，请上传 Excel 文件")

    # 3. File empty check
    if not filename:
        errors.append("文件名为空")

    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(errors),
        )


def _persist_chat(session_id: str, role: str, content: str, user_id: int = 0):
    """Save a chat message to the database."""
    db = SessionLocal()
    try:
        db.add(ChatMessage(
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            created_at=datetime.now().isoformat(),
        ))
        db.commit()
    finally:
        db.close()


def _persist_preferences(session: dict, user_id: int = 0):
    """Save global style preferences from session to DB."""
    db = SessionLocal()
    try:
        _upsert_pref(db, "active_theme", session.get("active_theme", "business"), user_id)
        _upsert_pref(db, "style_overrides", json.dumps(session.get("style_overrides", {}), ensure_ascii=False), user_id)
        db.commit()
    finally:
        db.close()


def _upsert_pref(db, key: str, value: str, user_id: int = 0):
    """Upsert a single user preference row."""
    row = db.query(preference_model.UserPreference).filter(
        preference_model.UserPreference.key == key,
        preference_model.UserPreference.user_id == user_id,
    ).first()
    if row:
        row.value = value
    else:
        db.add(preference_model.UserPreference(key=key, value=value, user_id=user_id))


from intent_classifier import classify_for_chat as _classify_intent


class ChatRequest(BaseModel):
    session_id: str
    question: str


class WorkflowRequest(BaseModel):
    session_id: str
    request: str


class AgentChatRequest(BaseModel):
    session_id: str
    message: str
    mode: str = "auto"  # "auto" | "chat" | "agent"


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "compute_stat",
            "description": "计算指定列的统计值。例如：平均值、最大值、最小值、总和、标准差",
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {"type": "string", "description": "要计算的列名"},
                    "stat": {"type": "string", "enum": ["mean", "max", "min", "sum", "std", "median"],
                             "description": "统计类型: mean(平均值), max(最大值), min(最小值), sum(总和), std(标准差), median(中位数)"},
                },
                "required": ["column", "stat"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sort_data",
            "description": "按指定列排序并返回前N行。用于找最高/最低的记录",
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {"type": "string", "description": "排序的列名"},
                    "order": {"type": "string", "enum": ["desc", "asc"], "description": "降序(desc)或升序(asc)"},
                    "top_n": {"type": "integer", "description": "返回前N行，默认5"},
                },
                "required": ["column", "order"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "group_by",
            "description": "按分类列分组，聚合数值列。用于分析各分类的汇总情况",
            "parameters": {
                "type": "object",
                "properties": {
                    "group_col": {"type": "string", "description": "用于分组的列名"},
                    "value_col": {"type": "string", "description": "要聚合的数值列名"},
                    "agg": {"type": "string", "enum": ["sum", "mean", "count"], "description": "聚合方式: sum, mean, count"},
                },
                "required": ["group_col", "value_col", "agg"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_trend",
            "description": "按指定列（通常是日期列）排序后返回数值列的序列，用于分析趋势变化",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_col": {"type": "string", "description": "用于排序的列名，通常是日期或序号列"},
                    "value_col": {"type": "string", "description": "要分析趋势的数值列名"},
                },
                "required": ["order_col", "value_col"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "filter_data",
            "description": "根据条件筛选数据。支持大于(>)、小于(<)、等于(==)操作",
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {"type": "string", "description": "筛选的列名"},
                    "op": {"type": "string", "enum": [">", "<", "=="], "description": "比较操作符"},
                    "value": {"type": "number", "description": "比较的阈值"},
                },
                "required": ["column", "op", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_data",
            "description": "获取数值列的整体描述统计（计数、平均值、标准差、最小值、四分位数、最大值），或查看所有列的基本信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "column": {"type": "string", "description": "要描述的列名，留空则返回所有列的概览"},
                },
                "required": [],
            },
        },
    },
]


@app.get("/")
async def root():
    return {"message": "AI Excel Data Agent API is running"}


# --- Auth Request Models ---

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


# --- Auth Endpoints ---

@app.post("/register")
async def register(req: RegisterRequest):
    print("[register] 1. request received — email:", req.email, "username:", req.username)
    db = SessionLocal()
    try:
        print("[register] 2. checking existing user")
        existing = db.query(User).filter(
            (User.email == req.email) | (User.username == req.username)
        ).first()
        if existing:
            print("[register] 3. user already exists, returning error")
            return {"error": "邮箱或用户名已存在。"}
        print("[register] 3. user not found, hashing password")
        try:
            hashed = hash_password(req.password)
        except Exception:
            print("[register] ERROR hashing password")
            traceback.print_exc()
            return {"error": "密码加密失败，请重试。"}
        print("[register] 4. password hashed, inserting user into DB")
        user = User(
            username=req.username,
            email=req.email,
            password_hash=hashed,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
        db.add(user)
        try:
            db.commit()
            print("[register] 5. DB commit done")
        except Exception:
            print("[register] ERROR on DB commit:")
            traceback.print_exc()
            return {"error": "数据库写入失败，请重试。"}
        db.refresh(user)
        print("[register] 6. creating JWT token")
        try:
            token = create_token(user.id, user.username)
        except Exception:
            print("[register] ERROR creating JWT")
            traceback.print_exc()
            return {"error": "令牌生成失败，请重试。"}
        print("[register] 7. response return — user_id:", user.id)
        return {
            "access_token": token,
            "user": {"id": user.id, "username": user.username, "email": user.email},
        }
    finally:
        db.close()


@app.post("/login")
async def login(req: LoginRequest):
    print("[login] 1. request received — email:", req.email)
    db = SessionLocal()
    try:
        print("[login] 2. querying user by email")
        user = db.query(User).filter(User.email == req.email).first()
        if not user:
            print("[login] 3. user not found")
            return {"error": "用户不存在。"}
        print("[login] 3. user found, verifying password")
        try:
            pw_ok = verify_password(req.password, user.password_hash)
        except Exception:
            print("[login] ERROR verifying password")
            traceback.print_exc()
            return {"error": "密码验证失败，请重试。"}
        if not pw_ok:
            print("[login] 4. password mismatch")
            return {"error": "密码错误。"}
        print("[login] 4. password verified, creating JWT")
        try:
            token = create_token(user.id, user.username)
        except Exception:
            print("[login] ERROR creating JWT")
            traceback.print_exc()
            return {"error": "令牌生成失败，请重试。"}
        print("[login] 5. response return — user_id:", user.id)
        return {
            "access_token": token,
            "user": {"id": user.id, "username": user.username, "email": user.email},
        }
    finally:
        db.close()


@app.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at,
    }


@app.post("/upload")
async def upload_excel(file: UploadFile = File(...)):
    _validate_excel_upload(file)  # T4: validate before processing
    contents = await file.read()
    df = pd.read_excel(io.BytesIO(contents), engine="openpyxl")

    result = {
        "filename": file.filename,
        "shape": {"rows": df.shape[0], "columns": df.shape[1]},
        "columns": df.columns.tolist(),
        "data": df.fillna("").to_dict(orient="records"),
        "describe": df.describe(include="all").fillna("").to_dict(),
    }

    return result


def _convert_excel_dates(df: pd.DataFrame) -> pd.DataFrame:
    date_keywords = ["date", "日期", "时间", "time", "year", "month", "day",
                     "年", "月", "日", "created", "updated", "modified", "创建", "修改"]
    for col in df.columns:
        if not pd.api.types.is_numeric_dtype(df[col]):
            continue
        s = df[col].dropna()
        if len(s) == 0:
            continue

        col_lower = str(col).lower()
        has_date_name = any(kw in col_lower for kw in date_keywords)
        mn, mx = s.min(), s.max()

        # 列名含日期关键词：宽松范围；否则只处理近期日期（>30000 ≈ 1982年后）
        if has_date_name:
            is_date_col = 1 <= mn <= 200000 and 1 <= mx <= 200000
        else:
            is_date_col = 30000 <= mn <= 200000 and 30000 <= mx <= 200000

        if is_date_col:
            try:
                converted = pd.to_datetime(df[col], origin="1899-12-30", unit="D", errors="coerce")
                valid_ratio = converted.notna().sum() / len(s)
                if valid_ratio > 0.8:
                    df[col] = converted.dt.strftime("%Y-%m-%d")
            except Exception:
                pass
    return df


def _generate_charts(df: pd.DataFrame) -> list[dict]:
    charts = []
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if not numeric_cols:
        return charts

    str_cols = [c for c in df.columns if pd.api.types.is_string_dtype(df[c]) or df[c].dtype == "object"]
    date_cols = [c for c in str_cols if any(kw in str(c).lower() for kw in
                 ["date", "日期", "时间", "time", "year", "month", "day", "年", "月", "日", "created"])]
    # 选取标签列：优先日期列，其次低基数的字符串列
    label_col = None
    if date_cols:
        label_col = date_cols[0]
    elif str_cols:
        candidates = [(c, df[c].nunique()) for c in str_cols if df[c].nunique() <= 50]
        if candidates:
            label_col = min(candidates, key=lambda x: x[1])[0]

    head = df.head(50)

    # 1. 折线图 — 趋势
    if label_col:
        labels = head[label_col].astype(str).tolist()
    else:
        labels = [str(i + 1) for i in range(len(head))]
    charts.append({
        "type": "line",
        "title": "数据趋势",
        "labels": labels,
        "datasets": [
            {"name": col, "data": head[col].fillna(0).tolist()}
            for col in numeric_cols[:3]
        ],
    })

    # 2. 柱状图 — 分类汇总
    if label_col and numeric_cols:
        grouped = df.groupby(label_col)[numeric_cols[0]].sum().sort_values(ascending=False)
        top = grouped.head(10)
        charts.append({
            "type": "bar",
            "title": f"{numeric_cols[0]} 分类统计",
            "labels": top.index.astype(str).tolist(),
            "datasets": [{"name": numeric_cols[0], "data": top.tolist()}],
        })

    # 3. 饼图 — 占比分布
    if label_col and numeric_cols:
        grouped = df.groupby(label_col)[numeric_cols[0]].sum().sort_values(ascending=False)
        top = grouped.head(10)
        charts.append({
            "type": "pie",
            "title": f"{numeric_cols[0]} 占比分布",
            "labels": top.index.astype(str).tolist(),
            "datasets": [{"name": numeric_cols[0], "data": top.tolist()}],
        })

    return charts


@app.post("/analyze")
@limiter.limit(f"{config.RATE_LIMIT_REQUESTS} per {config.RATE_LIMIT_WINDOW_SEC}s")
async def analyze_excel(request: Request, file: UploadFile = File(...), user: User = Depends(get_current_user)):
    _validate_excel_upload(file)  # T4: validate before processing
    print("[analyze] 1. 收到请求 — filename:", file.filename)

    contents = await file.read()
    df = pd.read_excel(io.BytesIO(contents), engine="openpyxl")
    print("[analyze] 2. Excel读取完成 — shape:", df.shape)

    df = _convert_excel_dates(df)
    charts = _generate_charts(df)
    print("[analyze] 3. pandas分析完成 — charts:", len(charts))

    data_summary = {
        "filename": file.filename,
        "shape": {"rows": int(df.shape[0]), "columns": int(df.shape[1])},
        "columns": df.columns.tolist(),
        "dtypes": {k: str(v) for k, v in df.dtypes.to_dict().items()},
        "describe": df.describe(include="all").fillna("").to_dict(),
        "sample": df.head(20).fillna("").to_dict(orient="records"),
        "null_counts": {k: int(v) for k, v in df.isnull().sum().to_dict().items()},
    }

    session_id = uuid.uuid4().hex[:12]
    sessions[session_id] = {
        "df": df,
        "data_summary": data_summary,
        "history": [],
        "analysis": {},
        "charts": [],
        "session_id": session_id,
        "active_theme": "business",
        "style_overrides": {},
    }

    # Load persisted global preferences into this session
    db_pref = SessionLocal()
    try:
        theme_row = db_pref.query(preference_model.UserPreference).filter(
            preference_model.UserPreference.key == "active_theme",
            preference_model.UserPreference.user_id == user.id,
        ).first()
        if theme_row:
            try:
                sessions[session_id]["active_theme"] = json.loads(theme_row.value)
            except (json.JSONDecodeError, TypeError):
                pass
        overrides_row = db_pref.query(preference_model.UserPreference).filter(
            preference_model.UserPreference.key == "style_overrides",
            preference_model.UserPreference.user_id == user.id,
        ).first()
        if overrides_row:
            try:
                sessions[session_id]["style_overrides"] = json.loads(overrides_row.value)
            except (json.JSONDecodeError, TypeError):
                pass
    finally:
        db_pref.close()

    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    print("[analyze] API KEY:", api_key[:8] + "..." if api_key else "NOT SET")

    if not api_key:
        sessions[session_id]["analysis"] = {
            "summary": "未配置 DEEPSEEK_API_KEY 环境变量，无法进行 AI 分析。",
            "anomaly": "请在终端执行: `$env:DEEPSEEK_API_KEY='your_key'` 后重新上传文件。",
            "trend": "",
        }
        sessions[session_id]["charts"] = charts
        print("[analyze] 6. Dashboard写入开始 (no-API path)")
        try:
            ds.update_snapshot(session_id, data_summary, sessions[session_id]["analysis"], charts, user.id)
            print("[analyze] 9. 写入完成 (no-API path)")
        except Exception:
            print("[analyze] ERROR in update_snapshot:")
            traceback.print_exc()
        # Save memory in no-API path too
        try:
            print("[analyze] 10. Memory写入开始 (no-API path)")
            mgr = get_memory_manager()
            mgr.save_workspace(user.id, session_id, data_summary["filename"],
                               data_summary, charts, sessions[session_id]["analysis"],
                               sessions[session_id].get("active_theme", "business"))
            mgr.save_analysis_memory(user.id, session_id, data_summary["filename"],
                                     sessions[session_id]["analysis"], charts)
            print("[analyze] 11. Memory写入完成 (no-API path)")
        except Exception:
            print("[analyze] ERROR saving memory (no-API path):")
            traceback.print_exc()

        print("[analyze] 12. 返回前端 (no-API path)")
        return {
            "session_id": session_id,
            "data_summary": data_summary,
            "charts": charts,
            "analysis": sessions[session_id]["analysis"],
        }

    print("[analyze] 4. DeepSeek请求开始 — model=deepseek-chat")

    prompt = f"""You are a data analyst. Analyze this Excel data and provide insights in Chinese.

Data Summary:
- Filename: {data_summary['filename']}
- Shape: {data_summary['shape']['rows']} rows × {data_summary['shape']['columns']} columns
- Columns: {data_summary['columns']}
- Data Types: {json.dumps(data_summary['dtypes'], ensure_ascii=False)}
- Statistical Summary: {json.dumps(data_summary['describe'], ensure_ascii=False)}
- Sample Data (first 20 rows): {json.dumps(data_summary['sample'], ensure_ascii=False)}
- Null Value Counts: {json.dumps(data_summary['null_counts'], ensure_ascii=False)}

Please return ONLY a JSON object (no markdown, no code block) in this exact format:
{{"summary": "数据总结...", "anomaly": "异常分析...", "trend": "趋势分析..."}}
Keep each section within 150-200 Chinese characters."""

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
            },
        )
        print("[analyze] 5. DeepSeek请求完成 — status:", resp.status_code)
        if resp.status_code != 200:
            print("[analyze] DeepSeek API error body:", resp.text)
        resp.raise_for_status()
        ai_data = resp.json()

    content = ai_data["choices"][0]["message"]["content"]

    try:
        analysis = json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", content)
        analysis = json.loads(m.group()) if m else {"summary": content, "anomaly": "", "trend": ""}

    analysis_result = {
        "summary": analysis.get("summary", ""),
        "anomaly": analysis.get("anomaly", ""),
        "trend": analysis.get("trend", ""),
    }
    sessions[session_id]["analysis"] = analysis_result
    sessions[session_id]["charts"] = charts

    print("[analyze] 6. Dashboard写入开始")
    try:
        ds.update_snapshot(session_id, data_summary, analysis_result, charts, user.id)
        print("[analyze] 7. Dashboard写入完成 (inside update_snapshot includes Report write)")
    except Exception:
        print("[analyze] ERROR in update_snapshot:")
        traceback.print_exc()

    # Save memory (workspace + analysis)
    try:
        mgr = get_memory_manager()
        mgr.save_workspace(user.id, session_id, data_summary["filename"],
                           data_summary, charts, analysis_result,
                           sessions[session_id].get("active_theme", "business"))
        mgr.save_analysis_memory(user.id, session_id, data_summary["filename"],
                                 analysis_result, charts)
        print("[analyze] 10. Memory saved")
    except Exception:
        print("[analyze] ERROR saving memory:")
        traceback.print_exc()

    print("[analyze] 12. 返回前端")
    return {
        "session_id": session_id,
        "data_summary": {
            "filename": data_summary["filename"],
            "shape": data_summary["shape"],
            "columns": data_summary["columns"],
        },
        "charts": charts,
        "analysis": analysis_result,
    }


def _execute_tool(df: pd.DataFrame, tool_name: str, args: dict) -> str:
    try:
        if tool_name == "compute_stat":
            col = args["column"]
            stat = args["stat"]
            if col not in df.columns:
                return f"错误：列 '{col}' 不存在。可用列: {list(df.columns)}"
            series = df[col].dropna()
            if not pd.api.types.is_numeric_dtype(series):
                series = pd.to_numeric(series, errors="coerce").dropna()
            if stat == "mean":
                return f"{col} 平均值: {series.mean():.2f}"
            elif stat == "max":
                return f"{col} 最大值: {series.max():.2f}"
            elif stat == "min":
                return f"{col} 最小值: {series.min():.2f}"
            elif stat == "sum":
                return f"{col} 总和: {series.sum():.2f}"
            elif stat == "std":
                return f"{col} 标准差: {series.std():.2f}"
            elif stat == "median":
                return f"{col} 中位数: {series.median():.2f}"
            return f"{col} {stat}: 计算完成"

        elif tool_name == "sort_data":
            col = args["column"]
            order = args.get("order", "desc")
            top_n = args.get("top_n", 5)
            if col not in df.columns:
                return f"错误：列 '{col}' 不存在。可用列: {list(df.columns)}"
            ascending = order == "asc"
            sorted_df = df.sort_values(by=col, ascending=ascending).head(top_n)
            result = sorted_df[df.columns.tolist()].fillna("").to_dict(orient="records")
            return json.dumps(result, ensure_ascii=False, default=str)

        elif tool_name == "group_by":
            group_col = args["group_col"]
            value_col = args["value_col"]
            agg = args.get("agg", "sum")
            if group_col not in df.columns:
                return f"错误：列 '{group_col}' 不存在。可用列: {list(df.columns)}"
            if value_col not in df.columns:
                return f"错误：列 '{value_col}' 不存在。可用列: {list(df.columns)}"
            grouped = df.groupby(group_col)[value_col].agg(agg).sort_values(ascending=False)
            result = {str(k): round(float(v), 2) for k, v in grouped.to_dict().items()}
            return json.dumps(result, ensure_ascii=False)

        elif tool_name == "analyze_trend":
            order_col = args["order_col"]
            value_col = args["value_col"]
            if order_col not in df.columns:
                return f"错误：列 '{order_col}' 不存在。可用列: {list(df.columns)}"
            if value_col not in df.columns:
                return f"错误：列 '{value_col}' 不存在。可用列: {list(df.columns)}"
            sorted_df = df.sort_values(by=order_col)
            data = sorted_df[[order_col, value_col]].fillna("").head(50)
            result = data.to_dict(orient="records")
            return json.dumps(result, ensure_ascii=False, default=str)

        elif tool_name == "filter_data":
            col = args["column"]
            op = args["op"]
            value = args["value"]
            if col not in df.columns:
                return f"错误：列 '{col}' 不存在。可用列: {list(df.columns)}"
            if op == ">":
                filtered = df[df[col] > value]
            elif op == "<":
                filtered = df[df[col] < value]
            elif op == "==":
                filtered = df[df[col] == value]
            else:
                return f"不支持的操作符: {op}"
            result = filtered.fillna("").to_dict(orient="records")
            return f"共 {len(result)} 条记录:\n{json.dumps(result[:10], ensure_ascii=False, default=str)}"

        elif tool_name == "describe_data":
            col = args.get("column", "")
            if col and col in df.columns:
                desc = df[col].describe().to_dict()
                return json.dumps({k: round(float(v), 2) for k, v in desc.items()}, ensure_ascii=False)
            elif col and col not in df.columns:
                return f"错误：列 '{col}' 不存在。可用列: {list(df.columns)}"
            else:
                info = {
                    "shape": list(df.shape),
                    "columns": df.columns.tolist(),
                    "dtypes": {k: str(v) for k, v in df.dtypes.to_dict().items()},
                    "numeric_stats": df.describe().fillna("").to_dict(),
                }
                return json.dumps(info, ensure_ascii=False, default=str)

        return f"未知工具: {tool_name}"
    except Exception as e:
        return f"工具执行出错: {str(e)}"


@app.post("/workflow")
@limiter.limit(f"{config.RATE_LIMIT_REQUESTS} per {config.RATE_LIMIT_WINDOW_SEC}s")
async def run_workflow(request: Request, req: WorkflowRequest, user: User = Depends(get_current_user)):
    session = sessions.get(req.session_id)
    if not session:
        return {"error": "会话已过期，请重新上传 Excel 文件。"}

    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        return {"error": "未配置 DEEPSEEK_API_KEY 环境变量。"}

    df = session["df"]
    ds = session["data_summary"]

    # Step 1: AI plans the workflow
    print(f"Workflow: planning for '{req.request}'")
    try:
        plan = await wf.plan_workflow(
            columns=ds["columns"],
            dtypes=ds["dtypes"],
            sample=ds["sample"],
            user_request=req.request,
            api_key=api_key,
        )
    except Exception as e:
        print(f"Plan error: {e}")
        return {"error": f"任务规划失败: {str(e)}"}

    # Step 2: Execute each step
    timeline: list[dict] = []
    for i, step in enumerate(plan.get("steps", [])):
        name = step.get("name", f"步骤{i + 1}")
        tool_name = step.get("tool", "")
        args = step.get("args", {})
        print(f"  Step {i + 1}: {name} → {tool_name}({args})")

        try:
            result = _execute_tool(df, tool_name, args)
            status = "done"
        except Exception as e:
            result = str(e)
            status = "error"

        timeline.append({
            "step": i + 1,
            "name": name,
            "tool": tool_name,
            "args": args,
            "result": result,
            "status": status,
        })

    # Step 3: AI generates the final report
    print("Workflow: generating report")
    try:
        report = await wf.generate_report(
            plan_title=plan.get("title", "数据分析报告"),
            steps_with_results=timeline,
            user_request=req.request,
            api_key=api_key,
        )
    except Exception as e:
        print(f"Report error: {e}")
        report = f"报告生成失败: {str(e)}"

    return {
        "plan": plan,
        "timeline": timeline,
        "report": report,
    }


@app.post("/chat")
@limiter.limit(f"{config.RATE_LIMIT_REQUESTS} per {config.RATE_LIMIT_WINDOW_SEC}s")
async def chat(request: Request, req: ChatRequest, user: User = Depends(get_current_user)):
    session = sessions.get(req.session_id)
    if not session:
        return {"mode": "chat", "reply": "会话已过期，请重新上传 Excel 文件。", "steps": []}

    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        return {"mode": "chat", "reply": "未配置 DEEPSEEK_API_KEY，无法使用 AI 对话功能。", "steps": []}

    # ── Style detection ──────────────────────────────
    style_applied = None
    if ts.detect_style_intent(req.question):
        overrides = ts.quick_parse_style(req.question)
        if overrides:
            theme_name = overrides.pop("_theme", None)
            if theme_name and theme_name in ts.THEMES:
                session["active_theme"] = theme_name
            if overrides:
                session.setdefault("style_overrides", {}).update(overrides)
            style_applied = ts.summarize_changes(session)
            print(f"Style applied: {style_applied}")
            # Persist global preferences when chat changes style
            _persist_preferences(session, user.id)
            # If message is purely style-related (no data keywords), return confirmation
            data_keywords = ["数据", "分析", "统计", "图表", "计算", "查询", "多少", "哪个",
                           "怎么", "为什么", "趋势", "异常", "总结", "汇总", "排序", "筛选"]
            if not any(kw in req.question for kw in data_keywords):
                return {
                    "mode": "chat", "style_applied": style_applied,
                    "active_theme": session.get("active_theme", "business"),
                    "reply": f"已应用样式设置：\n{style_applied}\n\n导出文档时将使用此样式。",
                    "steps": [],
                }

    intent = _classify_intent(req.question)
    print(f"Intent: {intent} for '{req.question[:50]}'")

    df = session["df"]
    ds = session["data_summary"]

    session.setdefault("history", []).append({"role": "user", "content": req.question})
    _persist_chat(req.session_id, "user", req.question, user.id)

    # --- WORKFLOW MODE ---
    if intent == "workflow":
        try:
            plan = await wf.plan_workflow(
                columns=ds["columns"], dtypes=ds["dtypes"],
                sample=ds["sample"], user_request=req.question, api_key=api_key,
            )
        except Exception as e:
            print(f"Plan error: {e}")
            return {"mode": "workflow", "reply": f"任务规划失败: {str(e)}", "steps": []}

        timeline: list[dict] = []
        steps: list[dict] = []
        for i, step in enumerate(plan.get("steps", [])):
            name = step.get("name", f"步骤{i + 1}")
            tool_name = step.get("tool", "")
            args = step.get("args", {})
            print(f"  Step {i + 1}: {name} -> {tool_name}({args})")
            try:
                result = _execute_tool(df, tool_name, args)
                status = "done"
            except Exception as e:
                result = str(e)
                status = "error"
            timeline.append({"step": i + 1, "name": name, "tool": tool_name, "args": args, "result": result, "status": status})
            steps.append({"tool": tool_name, "args": args, "result": result})

        print("Workflow: generating report")
        try:
            report = await wf.generate_report(
                plan_title=plan.get("title", "数据分析报告"),
                steps_with_results=timeline, user_request=req.question, api_key=api_key,
            )
        except Exception as e:
            print(f"Report error: {e}")
            report = f"报告生成失败: {str(e)}"

        session["history"].append({"role": "assistant", "content": report})
        _persist_chat(req.session_id, "assistant", report, user.id)
        result = {"mode": "workflow", "reply": report, "steps": steps, "plan": plan, "timeline": timeline}
        if style_applied:
            result["style_applied"] = style_applied
            result["active_theme"] = session.get("active_theme", "business")
        return result

    # --- CHAT MODE ---
    data_context = f"""当前 Excel 数据概览：
- 文件名: {ds['filename']}
- 行列: {ds['shape']['rows']} 行 x {ds['shape']['columns']} 列
- 列名: {ds['columns']}
- 数据类型: {json.dumps(ds['dtypes'], ensure_ascii=False)}
- 统计摘要: {json.dumps(ds['describe'], ensure_ascii=False)}
- 空值统计: {json.dumps(ds['null_counts'], ensure_ascii=False)}
- 前20行样本: {json.dumps(ds['sample'], ensure_ascii=False)}"""

    messages = [
        {"role": "system", "content": "你是一个专业的数据分析师。你可以使用工具来查询和分析 Excel 数据。先调用工具获取精确数据，再用中文生成简洁回答。用数据说话，主动发现异常并给出建议。"},
        {"role": "user", "content": f"以下是我上传的 Excel 数据，请记住这些数据：\n{data_context}"},
        {"role": "assistant", "content": "好的，我已了解这份数据。请随时向我提问，我会基于这些数据为你分析。"},
    ]
    for msg in session.get("history", []):
        messages.append(msg)
    messages.append({"role": "user", "content": req.question})

    steps: list[dict] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": messages, "tools": TOOLS, "temperature": 0.3},
        )
        print("Chat API status:", resp.status_code)
        if resp.status_code != 200:
            print("Chat API error:", resp.text)
            return {"mode": "chat", "reply": f"AI 服务请求失败: {resp.status_code}", "steps": []}
        ai_data = resp.json()

        msg = ai_data["choices"][0]["message"]

        max_rounds = 3
        for _ in range(max_rounds):
            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    func = tc["function"]
                    tool_name = func["name"]
                    args = json.loads(func["arguments"])
                    print(f"  Tool call: {tool_name}({args})")
                    result = _execute_tool(df, tool_name, args)
                    steps.append({"tool": tool_name, "args": args, "result": result})
                    messages.append({"role": "assistant", "content": None, "tool_calls": [tc]})
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

                resp2 = await client.post(
                    f"{DEEPSEEK_BASE_URL}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": "deepseek-chat", "messages": messages, "tools": TOOLS, "temperature": 0.7},
                )
                ai_data2 = resp2.json()
                msg = ai_data2["choices"][0]["message"]
            else:
                break

    reply = msg.get("content", "")
    session["history"].append({"role": "assistant", "content": reply})
    _persist_chat(req.session_id, "assistant", reply, user.id)
    result = {"mode": "chat", "reply": reply, "steps": steps}
    if style_applied:
        result["style_applied"] = style_applied
        result["active_theme"] = session.get("active_theme", "business")
    return result


# --- Agent Chat Endpoint ---

@app.post("/agent-chat")
@limiter.limit(f"{config.RATE_LIMIT_REQUESTS} per {config.RATE_LIMIT_WINDOW_SEC}s")
async def agent_chat(request: Request, req: AgentChatRequest, user: User = Depends(get_current_user)):
    """Multi-Agent chat endpoint — routes through Master Agent → sub-agents."""
    session = sessions.get(req.session_id)
    if not session:
        return {"mode": "chat", "reply": "会话已过期，请重新上传 Excel 文件。", "steps": []}

    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        return {"mode": "chat", "reply": "未配置 DEEPSEEK_API_KEY，无法使用 AI 功能。", "steps": []}

    mgr = get_memory_manager()

    # Retrieve relevant memories and inject into session context
    try:
        memories = mgr.retrieve_relevant_memories(user.id, {
            "session_id": req.session_id,
            "user_message": req.message,
            "data_summary": session.get("data_summary", {}),
        })
        memory_prompt = mgr.build_memory_prompt(memories)
        session["_memory_context"] = memory_prompt
    except Exception:
        print("[agent-chat] ERROR retrieving memories:")
        traceback.print_exc()
        session["_memory_context"] = ""

    # Persist user message
    session.setdefault("history", []).append({"role": "user", "content": req.message})
    _persist_chat(req.session_id, "user", req.message, user.id)
    try:
        mgr.save_conversation_message(user.id, req.session_id, "user", req.message, req.mode)
    except Exception:
        print("[agent-chat] ERROR saving user conversation:")
        traceback.print_exc()

    engine = we.WorkflowEngine()

    if req.mode == "chat":
        # Lightweight: DataAgent only
        result = await engine.run_chat(req.message, session, req.session_id)
    else:
        # Full multi-agent pipeline
        result = await engine.run(req.message, session, req.session_id)

    # Persist assistant reply
    _persist_chat(req.session_id, "assistant", result.get("reply", ""), user.id)
    session["history"].append({"role": "assistant", "content": result.get("reply", "")})
    try:
        steps_data = result.get("steps", [])
        mgr.save_conversation_message(user.id, req.session_id, "ai",
                                      result.get("reply", ""), result.get("mode", "agent"), steps_data)
    except Exception:
        print("[agent-chat] ERROR saving AI conversation:")
        traceback.print_exc()

    # Debug: log response structure
    try:
        import json as _json
        tmp = _json.dumps(result, ensure_ascii=False, default=str)
        print(f"[agent-chat] response size: {len(tmp)} bytes, keys: {list(result.keys())}")
        print(f"[agent-chat] reply length: {len(result.get('reply', ''))}, steps: {len(result.get('steps', []))}")
    except Exception:
        print("[agent-chat] unable to measure response")

    # Sync style changes if any
    if result.get("style_applied"):
        style_config = result.get("style_config", {})
        theme_name = style_config.get("_theme")
        if theme_name and theme_name in ts.THEMES:
            session["active_theme"] = theme_name
        overrides = style_config.get("overrides", {})
        if overrides:
            session.setdefault("style_overrides", {}).update(overrides)
        _persist_preferences(session, user.id)

    return result


# --- Memory Endpoints ---

class SavePreferenceRequest(BaseModel):
    category: str
    key: str
    value: str


@app.get("/memory/preferences")
async def get_memory_preferences(user: User = Depends(get_current_user)):
    mgr = get_memory_manager()
    prefs = mgr.get_user_preferences(user.id)
    return {"preferences": prefs}


@app.post("/memory/preferences")
async def save_memory_preference(req: SavePreferenceRequest, user: User = Depends(get_current_user)):
    mgr = get_memory_manager()
    mgr.save_user_preference(user.id, req.category, req.key, req.value)
    return {"ok": True}


@app.get("/memory/recent")
async def get_recent_memories(user: User = Depends(get_current_user)):
    mgr = get_memory_manager()
    analyses = mgr.get_recent_analyses(user.id, limit=10)
    workspaces = mgr.get_workspaces(user.id, limit=5)
    return {"recent_analyses": analyses, "recent_workspaces": workspaces}


@app.get("/memory/conversations/{session_id}")
async def get_conversation_memory(session_id: str, user: User = Depends(get_current_user)):
    mgr = get_memory_manager()
    history = mgr.get_conversation_history(user.id, session_id)
    return {"session_id": session_id, "messages": history}


@app.get("/memory/retrieve")
async def retrieve_memory_context(session_id: str, message: str = "", user: User = Depends(get_current_user)):
    mgr = get_memory_manager()
    memories = mgr.retrieve_relevant_memories(user.id, {
        "session_id": session_id,
        "user_message": message,
    })
    return {"memories": memories, "prompt": mgr.build_memory_prompt(memories)}


@app.get("/memory/summary")
async def get_memory_summary(user: User = Depends(get_current_user)):
    """Return aggregated memory stats for the Memory page."""
    mgr = get_memory_manager()
    return mgr.get_memory_summary(user.id)


class ClearMemoryRequest(BaseModel):
    type: str  # "analyses" | "workspaces" | "preferences" | "all"


@app.post("/memory/clear")
async def clear_memory(req: ClearMemoryRequest, user: User = Depends(get_current_user)):
    """Clear specific memory types for the current user."""
    mgr = get_memory_manager()
    results = {}
    if req.type in ("analyses", "all"):
        results["analyses_deleted"] = mgr.clear_analyses(user.id)
    if req.type in ("workspaces", "all"):
        results["workspaces_deleted"] = mgr.clear_workspaces(user.id)
    if req.type in ("preferences", "all"):
        results["preferences_deleted"] = mgr.clear_preferences(user.id)
    return {"ok": True, **results}


class DeletePreferenceRequest(BaseModel):
    key: str


@app.delete("/memory/preferences")
async def delete_memory_preference(req: DeletePreferenceRequest, user: User = Depends(get_current_user)):
    """Delete a single preference by key."""
    mgr = get_memory_manager()
    deleted = mgr.delete_preference(user.id, req.key)
    return {"ok": deleted}


# --- Reports Endpoints ---

@app.get("/reports")
async def list_reports(user: User = Depends(get_current_user)):
    return {"reports": rs.get_reports(user.id)}


@app.get("/reports/{report_id}")
async def get_report(report_id: str, user: User = Depends(get_current_user)):
    report = rs.get_report(report_id, user.id)
    if not report:
        return {"error": "报告未找到。"}
    return report


# --- Dashboard Endpoint ---

@app.get("/dashboard")
async def get_dashboard(user: User = Depends(get_current_user)):
    return ds.get_dashboard(user.id)


# --- Theme / Style Endpoints ---

class StyleApplyRequest(BaseModel):
    session_id: str
    theme: str | None = None
    overrides: dict | None = None


@app.get("/themes")
async def list_themes():
    return {
        "themes": [
            {"id": k, "name": v["name"], "description": v["description"],
             "primary_color": f"#{v['PRIMARY_COLOR']}"}
            for k, v in ts.THEMES.items()
        ],
        "current_default": "business",
    }


@app.post("/style/apply")
async def apply_style(req: StyleApplyRequest, user: User = Depends(get_current_user)):
    session = sessions.get(req.session_id)
    if not session:
        return {"error": "会话已过期，请重新上传 Excel 文件。"}
    if req.theme and req.theme in ts.THEMES:
        session["active_theme"] = req.theme
    if req.overrides:
        session.setdefault("style_overrides", {}).update(req.overrides)
    _persist_preferences(session, user.id)
    return {
        "active_theme": session.get("active_theme", "business"),
        "style_overrides": session.get("style_overrides", {}),
        "summary": ts.summarize_changes(session),
    }


@app.get("/style/preview/{session_id}")
async def preview_style(session_id: str, user: User = Depends(get_current_user)):
    session = sessions.get(session_id)
    if not session:
        return {"error": "会话已过期，请重新上传 Excel 文件。"}
    cfg = ts.get_effective_config(session)
    return {
        "active_theme": session.get("active_theme", "business"),
        "style_overrides": session.get("style_overrides", {}),
        "preview": {
            "primary_color": f"#{cfg.get('PRIMARY_COLOR', '1F4E79')}",
            "header_bg": f"#{cfg.get('HEADER_BG_COLOR', '1F4E79')}",
            "header_fg": f"#{cfg.get('HEADER_FG_COLOR', 'FFFFFF')}",
            "title_font": cfg.get("TITLE_FONT_NAME", "SimHei"),
            "body_font": cfg.get("BODY_FONT_NAME", "Microsoft YaHei"),
            "chart_colors": cfg.get("CHART_COLORS", ["#1F4E79"]),
            "theme_name": ts.THEMES.get(session.get("active_theme", "business"), {}).get("name", "商务风格"),
        },
    }


# --- Export Endpoints ---

@app.get("/export/excel/{session_id}")
async def export_excel(session_id: str):
    session = sessions.get(session_id)
    if not session:
        return {"error": "会话已过期，请重新上传 Excel 文件。"}
    path = es.export_excel(session)
    filename = os.path.basename(path)
    return FileResponse(path, filename=filename,
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.get("/export/word/{session_id}")
async def export_word(session_id: str):
    session = sessions.get(session_id)
    if not session:
        return {"error": "会话已过期，请重新上传 Excel 文件。"}
    path = es.export_word(session)
    filename = os.path.basename(path)
    return FileResponse(path, filename=filename,
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@app.get("/export/chart/{session_id}/{chart_index}")
async def export_chart(session_id: str, chart_index: int, fmt: str = "png"):
    session = sessions.get(session_id)
    if not session:
        return {"error": "会话已过期，请重新上传 Excel 文件。"}
    charts = session.get("charts", [])
    if chart_index < 0 or chart_index >= len(charts):
        return {"error": f"图表索引 {chart_index} 无效，共 {len(charts)} 个图表。"}
    base_name = es._base_name(session)
    path = es.export_chart(charts[chart_index], chart_index, base_name, fmt, session=session)
    if path is None:
        return {"error": "图表生成失败。"}
    filename = os.path.basename(path)
    media_type = "image/jpeg" if fmt == "jpg" else "image/png"
    return FileResponse(path, filename=filename, media_type=media_type)
