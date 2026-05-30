"""Document theme system — 4 preset themes + AI style parsing + merge logic."""
from __future__ import annotations
import json
import re
import httpx

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# ── Theme Definitions ──────────────────────────────────
# Each theme is a flat dict mapping style_config attribute names → values.
# pt/cm values are stored as strings and resolved at apply time.

BUSINESS = {
    "name": "商务风格",
    "description": "专业深蓝主色，适合领导汇报、正式报告",
    "TITLE_FONT_NAME": "SimHei",
    "BODY_FONT_NAME": "Microsoft YaHei",
    "TABLE_FONT_NAME": "Microsoft YaHei",
    "TITLE_SIZE": "Pt(18)",
    "H1_SIZE": "Pt(14)",
    "H2_SIZE": "Pt(12)",
    "BODY_SIZE": "Pt(11)",
    "TABLE_SIZE": "Pt(9.5)",
    "PRIMARY_COLOR": "1F4E79",
    "ACCENT_COLOR": "2563EB",
    "HEADER_BG_COLOR": "1F4E79",
    "HEADER_FG_COLOR": "FFFFFF",
    "BORDER_COLOR": "B0B0B0",
    "CHART_COLORS": '["#1F4E79","#E67E22","#27AE60","#C0392B","#8E44AD","#2980B9"]',
    "EXCEL_HEADER_FONT_NAME": "Microsoft YaHei",
    "EXCEL_BODY_FONT_NAME": "Microsoft YaHei",
    "EXCEL_HEADER_FONT_SIZE": "11",
    "EXCEL_BODY_FONT_SIZE": "10",
    "CHART_DPI": "150",
    "CHART_FIGSIZE": "(9, 5)",
    "LINE_SPACING": "1.5",
}

SIMPLE = {
    "name": "简洁风格",
    "description": "极简灰白配色，适合日常汇报、快速查阅",
    "TITLE_FONT_NAME": "Microsoft YaHei",
    "BODY_FONT_NAME": "Microsoft YaHei",
    "TABLE_FONT_NAME": "Microsoft YaHei",
    "TITLE_SIZE": "Pt(16)",
    "H1_SIZE": "Pt(13)",
    "H2_SIZE": "Pt(11)",
    "BODY_SIZE": "Pt(10.5)",
    "TABLE_SIZE": "Pt(9)",
    "PRIMARY_COLOR": "333333",
    "ACCENT_COLOR": "555555",
    "HEADER_BG_COLOR": "333333",
    "HEADER_FG_COLOR": "FFFFFF",
    "BORDER_COLOR": "CCCCCC",
    "CHART_COLORS": '["#333333","#888888","#AAAAAA","#CCCCCC","#666666","#999999"]',
    "EXCEL_HEADER_FONT_NAME": "Microsoft YaHei",
    "EXCEL_BODY_FONT_NAME": "Microsoft YaHei",
    "EXCEL_HEADER_FONT_SIZE": "10",
    "EXCEL_BODY_FONT_SIZE": "9",
    "CHART_DPI": "120",
    "CHART_FIGSIZE": "(8, 4.5)",
    "LINE_SPACING": "1.3",
}

DARK = {
    "name": "深色风格",
    "description": "深色主题，适合大屏展示、科技感报告",
    "TITLE_FONT_NAME": "SimHei",
    "BODY_FONT_NAME": "Microsoft YaHei",
    "TABLE_FONT_NAME": "Microsoft YaHei",
    "TITLE_SIZE": "Pt(16)",
    "H1_SIZE": "Pt(13)",
    "H2_SIZE": "Pt(11)",
    "BODY_SIZE": "Pt(10)",
    "TABLE_SIZE": "Pt(9)",
    "PRIMARY_COLOR": "1A1A2E",
    "ACCENT_COLOR": "E94560",
    "HEADER_BG_COLOR": "1A1A2E",
    "HEADER_FG_COLOR": "EEEEEE",
    "BORDER_COLOR": "444466",
    "CHART_COLORS": '["#E94560","#0F3460","#533483","#16213E","#F5A623","#7B68EE"]',
    "EXCEL_HEADER_FONT_NAME": "Microsoft YaHei",
    "EXCEL_BODY_FONT_NAME": "Microsoft YaHei",
    "EXCEL_HEADER_FONT_SIZE": "10",
    "EXCEL_BODY_FONT_SIZE": "9",
    "CHART_DPI": "150",
    "CHART_FIGSIZE": "(9, 5.5)",
    "LINE_SPACING": "1.4",
}

ACADEMIC = {
    "name": "学术风格",
    "description": "传统宋体，适合论文、研究报告、学术发表",
    "TITLE_FONT_NAME": "SimHei",
    "BODY_FONT_NAME": "SimSun",
    "TABLE_FONT_NAME": "SimSun",
    "TITLE_SIZE": "Pt(16)",
    "H1_SIZE": "Pt(14)",
    "H2_SIZE": "Pt(12)",
    "BODY_SIZE": "Pt(12)",
    "TABLE_SIZE": "Pt(10)",
    "PRIMARY_COLOR": "000000",
    "ACCENT_COLOR": "333333",
    "HEADER_BG_COLOR": "333333",
    "HEADER_FG_COLOR": "FFFFFF",
    "BORDER_COLOR": "666666",
    "CHART_COLORS": '["#333333","#666666","#999999","#AAAAAA","#555555","#777777"]',
    "EXCEL_HEADER_FONT_NAME": "SimHei",
    "EXCEL_BODY_FONT_NAME": "SimSun",
    "EXCEL_HEADER_FONT_SIZE": "10",
    "EXCEL_BODY_FONT_SIZE": "10",
    "CHART_DPI": "200",
    "CHART_FIGSIZE": "(8, 5)",
    "LINE_SPACING": "1.5",
}

THEMES: dict[str, dict] = {
    "business": BUSINESS,
    "simple": SIMPLE,
    "dark": DARK,
    "academic": ACADEMIC,
}

# ── Keyword → theme mapping ────────────────────────────
THEME_KEYWORDS: dict[str, str] = {
    "商务": "business", "专业": "business", "领导": "business", "汇报": "business",
    "简洁": "simple", "简单": "simple", "干净": "simple", "清爽": "simple",
    "深色": "dark", "黑暗": "dark", "暗色": "dark", "科技": "dark", "大屏": "dark",
    "学术": "academic", "论文": "academic", "期刊": "academic", "正式": "academic",
}

FONT_KEYWORDS: dict[str, str] = {
    "黑体": "SimHei", "宋体": "SimSun", "微软雅黑": "Microsoft YaHei",
    "楷体": "KaiTi", "仿宋": "FangSong",
}

STYLE_DETECT_KEYWORDS = [
    "标题", "正文", "字体", "字号", "颜色", "风格", "主题",
    "黑体", "宋体", "微软雅黑", "楷体", "仿宋",
    "商务", "简洁", "深色", "学术", "暗色",
    "font", "style", "theme", "color",
]

# ── Style detection ────────────────────────────────────

def detect_style_intent(question: str) -> bool:
    """Check if user message is about style/theme changes."""
    q = question.lower()
    return any(kw in q for kw in STYLE_DETECT_KEYWORDS)


def quick_parse_style(question: str) -> dict:
    """Fast keyword-based style extraction without AI. Returns {attr: value}."""
    overrides: dict = {}
    q = question.lower()

    # Theme detection
    for kw, theme_key in THEME_KEYWORDS.items():
        if kw in q:
            overrides["_theme"] = theme_key
            break

    # Font detection — check what text role the font applies to
    for kw, font_name in FONT_KEYWORDS.items():
        if kw in q:
            if "标题" in q:
                overrides["TITLE_FONT_NAME"] = font_name
            elif "正文" in q:
                overrides["BODY_FONT_NAME"] = font_name
            elif "表格" in q:
                overrides["TABLE_FONT_NAME"] = font_name
            else:
                # Apply to both title and body if not specified
                overrides["TITLE_FONT_NAME"] = font_name
                overrides["BODY_FONT_NAME"] = font_name

    # Size hints (Chinese typographic sizes)
    size_map = {
        "三号": 16, "小三": 15, "四号": 14, "小四": 12,
        "五号": 10.5, "小五": 9,
    }
    for size_name, size_pt in size_map.items():
        if size_name in q:
            if "标题" in q:
                overrides["TITLE_SIZE"] = f"Pt({size_pt})"
            else:
                overrides["BODY_SIZE"] = f"Pt({size_pt})"

    # Color hints
    color_map = {
        "蓝色": "1F4E79", "红色": "C0392B", "绿色": "27AE60",
        "橙色": "E67E22", "紫色": "8E44AD", "黑色": "333333",
    }
    for color_name, hex_color in color_map.items():
        if color_name in q:
            if "图表" in q:
                overrides["CHART_COLORS"] = json.dumps([f"#{hex_color}", "#E67E22", "#27AE60", "#C0392B", "#8E44AD", "#2980B9"])
            else:
                overrides["PRIMARY_COLOR"] = hex_color
                overrides["HEADER_BG_COLOR"] = hex_color

    return overrides


async def ai_parse_style(question: str, api_key: str) -> dict:
    """Use AI to extract structured style parameters from natural language."""
    prompt = f"""Extract document style preferences from this user request. Return ONLY a JSON object.

## User request
{question}

## Available style parameters (all optional):
- _theme: one of "business", "simple", "dark", "academic"
- TITLE_FONT_NAME: font name for titles (e.g. "SimHei", "Microsoft YaHei", "SimSun")
- BODY_FONT_NAME: font name for body text
- TABLE_FONT_NAME: font name for table text
- TITLE_SIZE: title font size in pt (number only)
- BODY_SIZE: body font size in pt (number only)
- PRIMARY_COLOR: hex color for headers/accents (without #)
- CHART_COLORS: array of 6 hex colors (without #)
- _description: brief Chinese description of the style change

Return JSON:
{{"_theme": "business", "TITLE_FONT_NAME": "SimHei", ...}}

Only include parameters the user explicitly or implicitly requested. If the user didn't specify, omit the field."""

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "temperature": 0.1},
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", content)
        return json.loads(m.group()) if m else {}


# ── Style resolution ───────────────────────────────────

def get_effective_config(session: dict) -> dict:
    """Merge base theme + session overrides into a flat config dict. Returns {ATTR: python_value}."""
    from docx.shared import Pt

    theme_key = session.get("active_theme", "business")
    theme = THEMES.get(theme_key, BUSINESS)
    overrides = session.get("style_overrides", {})

    # Merge: theme base + overrides
    merged = dict(theme)
    for k, v in overrides.items():
        if v is not None:
            merged[k] = v

    # Resolve string values to Python objects
    result: dict = {}
    for k, v in merged.items():
        # Skip metadata keys
        if k in ("name", "description"):
            continue
        if not isinstance(v, str):
            result[k] = v
        elif v.startswith("Pt("):
            result[k] = Pt(float(v[3:-1]))
        elif v.startswith("(") and v.endswith(")"):
            parts = v[1:-1].split(",")
            result[k] = (float(parts[0].strip()), float(parts[1].strip()))
        elif v.startswith("["):
            result[k] = json.loads(v)
        elif "COLOR" in k:
            result[k] = v  # keep hex color strings as-is
        elif v.lstrip("-").isdigit():
            result[k] = int(v)
        elif v.replace(".", "").lstrip("-").isdigit():
            result[k] = float(v)
        else:
            result[k] = v

    return result


def summarize_changes(session: dict) -> str:
    """Return a human-readable summary of current style settings."""
    theme_key = session.get("active_theme", "business")
    theme = THEMES.get(theme_key, BUSINESS)
    overrides = session.get("style_overrides", {})
    desc = theme.get("name", theme_key)
    lines = [f"当前主题：{desc}"]
    for k, v in overrides.items():
        if k.startswith("_"):
            continue
        lines.append(f"  {k} = {v}")
    return "\n".join(lines)
