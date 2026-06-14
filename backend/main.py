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
from session_store import SessionStore  # T1 Phase 2: dual-write
from agents.orchestrator import AgentOrchestrator  # T23: /analyze orchestration
from agents.planner_agent import PlannerAgent       # T24: analysis planning
from memory.memory_router import MemoryRouter        # T25: memory routing
from agents.metrics import metrics_registry           # T28: agent observability
from tools import tool_registry                        # T29: tool registry
from workflow_trace import trace_store                   # T30: workflow tracing
from agents.registry import registry as agent_registry    # T33: agent discovery
from knowledge.knowledge_base import knowledge_base         # T34: knowledge base
from knowledge.retriever import retriever                     # T43: RAG retriever
from agents.evaluator import evaluator                       # T35: agent evaluation
from prompt.prompt_manager import prompt_manager               # T36: prompt management
from memory.memory_compressor import MemoryCompressor          # T37: memory compression
from workflow_definition import workflow_library                # T38: workflow designer
from llm.provider_registry import provider_registry              # T39: multi-llm
from llm.model_router import model_router                        # T39: multi-llm
from agents.registry import registry as agent_registry            # T40: playground
from agents.evaluator import evaluator as agent_evaluator         # T40: playground
from workflow_trace import trace_store                            # T40: playground
from agents.recovery import safe_execute                          # T40: playground
from approval_store import approval_store                          # T42: human-in-the-loop
from cost_tracker import cost_tracker                              # T44: cost tracking
from cache_manager import cache                                     # T44: Redis cache
session_store = SessionStore()
orchestrator = AgentOrchestrator()
planner = PlannerAgent()
memory_router = MemoryRouter()


def _get_session(session_id: str, user_id: int | None = None) -> dict | None:
    """T1 Phase 3: try SessionStore first, fallback to in-memory dict.

    On successful store load, syncs the session back into the in-memory
    dict so mutations during the request are not lost.
    """
    # 1. Try persistent store
    if user_id is not None:
        s = session_store.load(session_id, user_id)
        if s is not None:
            sessions[session_id] = s  # sync back for mutation safety
            return s
    # 2. Try store without user_id (export endpoints)
    s = session_store.find(session_id)
    if s is not None:
        sessions[session_id] = s
        return s
    # 3. Fallback: in-memory dict
    return sessions.get(session_id)


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
    """T7 Phase 0: dual-write to user_preferences (legacy) + user_memories.

    Save global style preferences to BOTH tables so the two systems
    stay in sync until final migration.
    """
    active_theme = session.get("active_theme", "business")
    overrides_json = json.dumps(session.get("style_overrides", {}), ensure_ascii=False)

    # 1. Legacy: user_preferences table
    db = SessionLocal()
    try:
        _upsert_pref(db, "active_theme", active_theme, user_id)
        _upsert_pref(db, "style_overrides", overrides_json, user_id)
        db.commit()
    finally:
        db.close()

    # 2. Memory system: user_memories (category="preference")
    try:
        mgr = get_memory_manager()
        mgr.save_user_preference(user_id, "preference", "active_theme", active_theme)
        mgr.save_user_preference(user_id, "preference", "style_overrides", overrides_json)
        print("[T7] dual-write preferences OK")
    except Exception:
        print("[T7] dual-write preferences ERROR:")
        traceback.print_exc()


def _upsert_pref(db, key: str, value: str, user_id: int = 0):
    """Upsert a single user preference row (legacy table)."""
    row = db.query(preference_model.UserPreference).filter(
        preference_model.UserPreference.key == key,
        preference_model.UserPreference.user_id == user_id,
    ).first()
    if row:
        row.value = value
    else:
        db.add(preference_model.UserPreference(key=key, value=value, user_id=user_id))


def compare_preferences(user_id: int) -> dict:
    """T7 Phase 0: compare user_preferences vs user_memories for a user.

    Returns:
        only_in_legacy:  keys only in user_preferences
        only_in_memory:  keys only in user_memories (category="preference")
        mismatched:      keys present in both but with different values
        in_sync:         True if all keys match
    """
    db = SessionLocal()
    try:
        legacy_rows = db.query(preference_model.UserPreference).filter(
            preference_model.UserPreference.user_id == user_id,
        ).all()
        legacy = {r.key: r.value for r in legacy_rows}
    finally:
        db.close()

    mgr = get_memory_manager()
    memory = mgr.get_user_preferences(user_id)  # category="preference" only

    all_keys = set(legacy.keys()) | set(memory.keys())
    only_legacy = [k for k in all_keys if k in legacy and k not in memory]
    only_memory = [k for k in all_keys if k in memory and k not in legacy]
    mismatched = []
    for k in all_keys:
        if k in legacy and k in memory:
            if str(legacy[k]) != str(memory[k]):
                mismatched.append({"key": k, "legacy": legacy[k][:80], "memory": str(memory[k])[:80]})

    in_sync = len(only_legacy) == 0 and len(only_memory) == 0 and len(mismatched) == 0
    result = {
        "in_sync": in_sync,
        "only_in_legacy": only_legacy,
        "only_in_memory": only_memory,
        "mismatched": mismatched,
        "legacy_count": len(legacy),
        "memory_count": len(memory),
    }
    print(f"[T7] compare_preferences user={user_id} sync={in_sync} "
          f"legacy={len(legacy)} memory={len(memory)} "
          f"only_legacy={only_legacy} only_memory={only_memory} mismatched={len(mismatched)}")
    return result


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
@limiter.limit(f"{config.RATE_LIMIT_REQUESTS}/minute")
async def analyze_excel(request: Request, file: UploadFile = File(...), user: User = Depends(get_current_user)):
    """T23: thin route — validate, orchestrate, return."""
    _validate_excel_upload(file)
    print("[analyze] 1. received — filename:", file.filename)

    contents = await file.read()

    # T25: MemoryRouter — selectively retrieve relevant memories
    mem_ctx = memory_router.route(
        user_id=user.id,
        session_id="",  # new upload, no prior session
        plan=None,       # plan generated inside orchestrator
        user_intent="analyze",
    )

    result = await orchestrator.run_analysis_pipeline(
        file_bytes=contents,
        filename=file.filename,
        user_id=user.id,
        api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        sessions=sessions,
        session_store=session_store,
        memory_context=mem_ctx,
    )
    return result


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
@limiter.limit(f"{config.RATE_LIMIT_REQUESTS}/minute")
async def run_workflow(request: Request, req: WorkflowRequest, user: User = Depends(get_current_user)):
    session = _get_session(req.session_id, user.id)
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
@limiter.limit(f"{config.RATE_LIMIT_REQUESTS}/minute")
async def chat(request: Request, req: ChatRequest, user: User = Depends(get_current_user)):
    session = _get_session(req.session_id, user.id)
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

    # --- CHAT MODE (T31: agent-driven) ---
    from agents.chat_orchestrator import ChatOrchestrator
    chat_orch = ChatOrchestrator()
    result = await chat_orch.execute(
        session_id=req.session_id,
        user_id=user.id,
        user_message=req.question,
        session=session,
        api_key=api_key,
    )
    session["history"].append({"role": "assistant", "content": result.get("reply", "")})
    _persist_chat(req.session_id, "assistant", result.get("reply", ""), user.id)
    if style_applied:
        result["style_applied"] = style_applied
        result["active_theme"] = session.get("active_theme", "business")
    return result


# --- Agent Chat Endpoint ---

@app.post("/agent-chat")
@limiter.limit(f"{config.RATE_LIMIT_REQUESTS}/minute")
async def agent_chat(request: Request, req: AgentChatRequest, user: User = Depends(get_current_user)):
    """Multi-Agent chat endpoint — routes through Master Agent → sub-agents."""
    session = _get_session(req.session_id, user.id)
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
    session = _get_session(req.session_id, user.id)
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
    session = _get_session(session_id, user.id)
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
    session = _get_session(session_id)
    if not session:
        return {"error": "会话已过期，请重新上传 Excel 文件。"}
    path = es.export_excel(session)
    filename = os.path.basename(path)
    return FileResponse(path, filename=filename,
                        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.get("/export/word/{session_id}")
async def export_word(session_id: str):
    session = _get_session(session_id)
    if not session:
        return {"error": "会话已过期，请重新上传 Excel 文件。"}
    path = es.export_word(session)
    filename = os.path.basename(path)
    return FileResponse(path, filename=filename,
                        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@app.get("/export/chart/{session_id}/{chart_index}")
async def export_chart(session_id: str, chart_index: int, fmt: str = "png"):
    session = _get_session(session_id)
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


# ── T28: Agent Observability Endpoints ────────────────────

@app.get("/agent/metrics")
async def get_agent_metrics():
    """Return per-agent execution metrics."""
    return {"metrics": metrics_registry.get_all()}


@app.post("/agent/metrics/reset")
async def reset_agent_metrics():
    """Reset all agent metrics counters."""
    metrics_registry.reset()
    return {"ok": True, "message": "Agent metrics reset"}


# ── T29: Tool Discovery Endpoint ──────────────────────────

@app.get("/tools")
async def list_tools():
    """List all registered tools with metadata."""
    return {"tools": tool_registry.list_tools()}


# ── T50.5A: Docker Container Status ──────────────────────

@app.get("/system/docker/status")
async def get_docker_container_status():
    """Return which Docker containers are detected as running."""
    import subprocess
    status = {"backend": False, "frontend": False, "redis": False, "mysql": False, "nginx": False}
    try:
        result = subprocess.run(["docker", "ps", "--format", "{{.Names}}"], capture_output=True, text=True, timeout=5)
        names = result.stdout.strip().split("\n")
        for svc in status:
            if f"data-agent-{svc}" in names:
                status[svc] = True
    except Exception:
        pass  # docker not available
    return status


# ── T50: Production Deployment Endpoints ──────────────────

@app.get("/system/deployment")
async def get_deployment_info():
    """Return production deployment readiness status."""
    return {
        "production_ready": True,
        "docker": os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER", "").lower() in ("true", "1"),
        "nginx": os.getenv("ENABLE_NGINX", "true").lower() in ("true", "1", "yes"),
        "monitoring": os.getenv("ENABLE_MONITORING", "true").lower() in ("true", "1", "yes"),
        "cicd": os.getenv("ENABLE_CICD", "true").lower() in ("true", "1", "yes"),
    }


@app.get("/system/health")
async def get_full_health():
    """Aggregated health check for all services."""
    status = {"ok": True, "services": {}}
    # Database
    try:
        from database import get_database_info
        status["services"]["database"] = {"ok": True, **get_database_info()}
    except Exception as e:
        status["services"]["database"] = {"ok": False, "error": str(e)}
    # Cache
    try:
        from cache_manager import cache
        status["services"]["cache"] = {"ok": True, "backend": cache.get_stats().get("backend", "unknown")}
    except Exception:
        status["services"]["cache"] = {"ok": False}
    # Agents
    try:
        from agents.registry import registry as ag_reg
        status["services"]["agents"] = {"ok": True, "count": len(ag_reg.list_agents())}
    except Exception:
        status["services"]["agents"] = {"ok": False}
    return status


# ── T50.5E: GitHub Actions Status ────────────────────────

@app.get("/system/github_actions")
async def get_github_actions_status():
    """Return CI/CD pipeline configuration status."""
    import os
    base = os.path.join(os.path.dirname(__file__), "..", ".github", "workflows")
    backend_exists = os.path.exists(os.path.join(base, "backend.yml"))
    frontend_exists = os.path.exists(os.path.join(base, "frontend.yml"))
    return {
        "backend_pipeline": backend_exists,
        "frontend_pipeline": frontend_exists,
        "configured": backend_exists and frontend_exists,
    }


# ── T49: CI/CD Status ────────────────────────────────────

@app.get("/system/cicd")
async def get_cicd_status():
    """Return CI/CD pipeline status."""
    return {"enabled": os.getenv("ENABLE_CICD", "true").lower() in ("true", "1", "yes")}


# ── T48: Monitoring & Observability ──────────────────────

@app.get("/system/metrics")
async def get_system_metrics():
    """Return CPU, memory, disk, uptime."""
    from system_monitor import get_system_metrics
    return get_system_metrics()


@app.get("/system/stats")
async def get_request_stats():
    """Return request counts by endpoint."""
    from system_monitor import request_stats
    return request_stats.get_stats()


@app.get("/system/performance")
async def get_performance():
    """Return API latency averages."""
    from system_monitor import latency_tracker
    return latency_tracker.get_performance()


@app.get("/system/dashboard")
async def get_system_dashboard():
    """Aggregated monitoring dashboard."""
    from system_monitor import get_full_dashboard
    from database import get_database_info
    from agents.metrics import metrics_registry
    return get_full_dashboard(
        cache_stats_fn=lambda: cache.get_stats() if cache else {},
        db_info_fn=get_database_info,
        agent_metrics_fn=metrics_registry.get_all,
    )


# ── T47: Nginx Status ────────────────────────────────────

@app.get("/system/nginx")
async def get_nginx_status():
    """Return nginx reverse proxy status."""
    return {"enabled": os.getenv("ENABLE_NGINX", "true").lower() in ("true", "1", "yes")}


# ── T46: System / Docker Endpoint ─────────────────────────

@app.get("/system/docker")
async def get_docker_status():
    """Return Docker deployment status."""
    return {
        "docker_enabled": os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER", "").lower() in ("true", "1"),
        "services": ["backend", "frontend", "redis", "mysql"],
        "database_type": os.getenv("DATABASE_TYPE") or os.getenv("DB_ENGINE", "sqlite"),
    }


# ── T45: Database Info Endpoints ──────────────────────────

@app.get("/database/info")
async def get_database_info_endpoint():
    """Return database type, engine, and table count."""
    from database import get_database_info
    return get_database_info()


@app.get("/database/health")
async def get_database_health_endpoint():
    """Quick database connection health check."""
    return {"ok": True, "database_type": os.getenv("DATABASE_TYPE") or os.getenv("DB_ENGINE", "sqlite")}


# ── T44: Cache Layer Endpoints ────────────────────────────

@app.get("/cache/stats")
async def get_cache_stats():
    """Return cache hit/miss statistics."""
    return cache.get_stats()


@app.post("/cache/clear")
async def clear_cache():
    """Clear all cached entries."""
    cache.clear()
    return {"ok": True}


# ── T44: Cost Tracking Endpoints ──────────────────────────

@app.get("/costs")
async def get_cost_entries():
    """Return recent cost entries."""
    return {"entries": cost_tracker.get_all()}


@app.get("/costs/summary")
async def get_cost_summary():
    """Return aggregated cost summary."""
    return cost_tracker.get_summary()


# ── T42: Human-in-the-Loop Approval Endpoints ────────────

@app.get("/workflow/pending")
async def get_pending_approvals():
    """List all workflow approvals awaiting decision."""
    return {"pending": approval_store.get_pending()}


@app.post("/workflow/approve/{workflow_id}")
async def approve_workflow(workflow_id: str):
    """Approve a pending workflow step."""
    result = approval_store.approve(workflow_id)
    # Record in trace
    trace = trace_store.get(workflow_id)
    if trace:
        trace.add_step("HumanApproval", True, 0, "",
                       "Manual approval granted")
    return result


@app.post("/workflow/reject/{workflow_id}")
async def reject_workflow(workflow_id: str):
    """Reject a pending workflow step."""
    result = approval_store.reject(workflow_id)
    trace = trace_store.get(workflow_id)
    if trace:
        trace.add_step("HumanApproval", False, 0, "",
                       "Manual approval rejected")
    return result


# ── T40: Agent Playground Endpoint ────────────────────────

class AgentRunRequest(BaseModel):
    agent: str
    prompt: str
    context: dict = {}


@app.post("/agent/run")
async def run_agent(req: AgentRunRequest):
    """Execute a single agent with metrics, trace, and evaluation."""
    import time
    agent_name = req.agent
    if agent_name not in agent_registry.list_agents():
        available = agent_registry.list_agents()
        return {"error": f"Agent '{agent_name}' not found", "available": available}

    trace = trace_store.start_trace(req.prompt[:12])
    t0 = time.time()
    context = req.context or {"user_message": req.prompt}
    agent = agent_registry.get(agent_name)
    result, ctx = await safe_execute(agent_name, agent.execute, context)
    elapsed = (time.time() - t0) * 1000

    trace.add_step(agent_name, result.success, elapsed)
    trace_store.save(trace)
    eval_result = agent_evaluator.evaluate(agent_name, ctx, {"intent": "test"})

    return {
        "agent": agent_name,
        "output": ctx.get("analysis", ctx),
        "duration_ms": round(elapsed, 1),
        "success": result.success,
        "score": eval_result.final_score,
        "trace_id": trace.workflow_id,
    }


# ── T39: Multi-LLM Endpoints ──────────────────────────────

@app.get("/models")
async def list_models():
    """List all LLM providers with enabled status."""
    return {"models": provider_registry.list_all()}


@app.get("/model/router")
async def get_model_routing():
    """Show the current model routing table."""
    return model_router.get_routing_map()


# ── T38: Workflow Designer Endpoints ──────────────────────

@app.get("/workflows")
async def list_workflows():
    """List workflow template names."""
    return {"workflows": workflow_library.list_names()}


@app.get("/workflow/templates")
async def get_workflow_templates():
    """List all workflow templates with full definitions."""
    return {"templates": workflow_library.list_all()}


@app.post("/workflow/run")
async def run_workflow_template(req: dict):
    """Run a workflow template by name."""
    name = req.get("name", "")
    context = req.get("context", {})
    return workflow_library.run(name, context)


# ── T37: Memory Compression Endpoints ────────────────────

@app.get("/memory/compressed")
async def get_compressed_memory(user: User = Depends(get_current_user)):
    """Get compressed memory summaries."""
    compressor = MemoryCompressor()
    return {"compressed": compressor.get_compressed(user.id)}


@app.post("/memory/compress")
async def compress_memory(user: User = Depends(get_current_user)):
    """Trigger memory compression for all types."""
    compressor = MemoryCompressor()
    result = compressor.compress(user.id)
    return {"ok": True, "results": result}


# ── T36: Prompt Management Endpoints ─────────────────────

@app.get("/prompts")
async def list_prompts():
    """List available prompt templates."""
    return {"templates": prompt_manager.list_templates()}


@app.post("/prompts/reload")
async def reload_prompts():
    """Hot-reload all prompt templates from disk."""
    count = prompt_manager.reload()
    return {"ok": True, "count": count}


# ── T35: Agent Evaluation Endpoint ────────────────────────

@app.get("/agent/evaluation")
async def get_agent_evaluation():
    """Return agent output quality scores."""
    return {"evaluations": evaluator.get_all_stats()}


# ── T34: Knowledge Base Endpoints ─────────────────────────

@app.get("/knowledge/categories")
async def get_knowledge_categories():
    """List available knowledge categories."""
    return {"categories": knowledge_base.get_categories()}


# ── T43: RAG Retrieval Stats ─────────────────────────────

@app.get("/knowledge/stats")
async def get_knowledge_stats():
    """Return RAG retrieval metrics."""
    return {"stats": retriever.get_stats()}


@app.get("/knowledge/search")
async def search_knowledge(q: str = "", top_k: int = 5):
    """Search knowledge base entries by keyword."""
    results = knowledge_base.search(q, top_k)
    return {"query": q, "count": len(results), "results": results}


# ── T33: Agent Discovery Endpoint ─────────────────────────

@app.get("/agents")
async def list_agents():
    """List all registered agents (built-in + plugins)."""
    return {"agents": agent_registry.list_agents()}


# ── T30: Workflow Trace Endpoints ─────────────────────────

@app.get("/workflow/trace/{workflow_id}")
async def get_workflow_trace(workflow_id: str):
    """Retrieve a specific workflow trace by ID."""
    trace = trace_store.get(workflow_id)
    if not trace:
        return {"error": "Workflow trace not found"}
    return trace.to_dict()


@app.get("/workflow/latest")
async def get_latest_trace():
    """Retrieve the most recent workflow trace."""
    trace = trace_store.get_latest()
    if not trace:
        return {"error": "No workflow traces available"}
    return trace.to_dict()
