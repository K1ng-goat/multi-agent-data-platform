"""Unified visual style configuration for Word, Excel, and Chart exports."""
from __future__ import annotations
import sys
from dataclasses import dataclass, field
from docx.shared import Pt, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH


# ── Fonts ──────────────────────────────────────────────
TITLE_FONT_NAME = "SimHei"          # 黑体
TITLE_FONT_NAME_FALLBACK = "Microsoft YaHei"
BODY_FONT_NAME = "Microsoft YaHei"  # 微软雅黑
BODY_FONT_NAME_FALLBACK = "SimSun"
TABLE_FONT_NAME = "Microsoft YaHei"

# ── Font Sizes ─────────────────────────────────────────
TITLE_SIZE = Pt(16)
H1_SIZE = Pt(14)
H2_SIZE = Pt(12)
BODY_SIZE = Pt(11)
TABLE_SIZE = Pt(10)
CHART_TITLE_SIZE = 14
CHART_LABEL_SIZE = 9
CHART_LEGEND_SIZE = 9

# ── Colors ─────────────────────────────────────────────
PRIMARY_COLOR = "1F4E79"       # 深蓝 — 表头/标题
ACCENT_COLOR = "2563EB"        # 亮蓝 — 强调
HEADER_BG_COLOR = "1F4E79"
HEADER_FG_COLOR = "FFFFFF"
BORDER_COLOR = "B0B0B0"
CHART_COLORS = ["#1F4E79", "#E67E22", "#27AE60", "#C0392B", "#8E44AD", "#2980B9"]

# ── Word Layout ────────────────────────────────────────
PAGE_MARGIN_TOP = Cm(2.5)
PAGE_MARGIN_BOTTOM = Cm(2.0)
PAGE_MARGIN_LEFT = Cm(2.5)
PAGE_MARGIN_RIGHT = Cm(2.0)
LINE_SPACING = 1.5
PARAGRAPH_SPACING_AFTER = Pt(6)
PARAGRAPH_SPACING_BEFORE = Pt(0)
TITLE_ALIGNMENT = WD_ALIGN_PARAGRAPH.CENTER
H1_ALIGNMENT = WD_ALIGN_PARAGRAPH.LEFT

# ── Excel Layout ───────────────────────────────────────
EXCEL_HEADER_FONT_NAME = "Microsoft YaHei"
EXCEL_HEADER_FONT_SIZE = 11
EXCEL_BODY_FONT_NAME = "Microsoft YaHei"
EXCEL_BODY_FONT_SIZE = 10
EXCEL_MIN_COL_WIDTH = 12
EXCEL_MAX_COL_WIDTH = 36
EXCEL_FREEZE_ROW = 1  # freeze first row

# ── Chart Layout ───────────────────────────────────────
CHART_DPI = 150
CHART_FIGSIZE = (9, 5)
CHART_GRID_ALPHA = 0.25
CHART_LINE_WIDTH = 2.0
CHART_BAR_RADIUS = 4
CHART_MARKER_SIZE = 5

# ── Dynamic override ───────────────────────────────────

def load_from_dict(config: dict):
    """Apply runtime style overrides from a flat config dict.
    Only updates attributes that already exist in this module."""
    module = sys.modules[__name__]
    for key, value in config.items():
        if hasattr(module, key) and not key.startswith("__"):
            setattr(module, key, value)
