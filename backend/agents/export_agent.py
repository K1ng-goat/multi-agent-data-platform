"""ExportAgent — wraps export_service functions for file export."""
import os
from pathlib import Path

from .base_agent import BaseAgent


class ExportAgent(BaseAgent):
    name = "ExportAgent"
    description = "文件导出 (Excel/Word/Chart)"

    async def execute(self, context: dict) -> dict:
        self.add_step(context, "running", "开始导出文件...")

        try:
            exports = []
            self._build_session(context)

            # Export Excel
            try:
                import export_service as es
                xlsx_path = es.export_excel(context)
                exports.append({"type": "excel", "path": xlsx_path, "filename": os.path.basename(xlsx_path)})
                self.add_step(context, "done", f"Excel导出完成: {os.path.basename(xlsx_path)}")
            except Exception as e:
                self.add_step(context, "error", f"Excel导出失败: {str(e)}")
                context.setdefault("errors", []).append(f"ExportAgent Excel: {str(e)}")

            # Export Word
            try:
                import export_service as es
                docx_path = es.export_word(context)
                exports.append({"type": "word", "path": docx_path, "filename": os.path.basename(docx_path)})
                self.add_step(context, "done", f"Word导出完成: {os.path.basename(docx_path)}")
            except Exception as e:
                self.add_step(context, "error", f"Word导出失败: {str(e)}")
                context.setdefault("errors", []).append(f"ExportAgent Word: {str(e)}")

            # Export charts as PNG
            charts = context.get("charts", [])
            if charts:
                import export_service as es
                base_name = es._base_name(context)
                for i, chart in enumerate(charts):
                    try:
                        chart_path = es.export_chart(chart, i, base_name, "png", session=context)
                        if chart_path:
                            exports.append({
                                "type": "chart",
                                "index": i,
                                "path": chart_path,
                                "filename": os.path.basename(chart_path),
                            })
                    except Exception as e:
                        context.setdefault("errors", []).append(f"ExportAgent Chart[{i}]: {str(e)}")

                self.add_step(context, "done", f"全部导出完成: {len(exports)} 个文件")
            else:
                self.add_step(context, "done", f"导出完成: {len(exports)} 个文件")

            context["exports"] = exports
        except Exception as e:
            self.add_step(context, "error", f"导出流程失败: {str(e)}")
            context.setdefault("errors", []).append(f"ExportAgent: {str(e)}")
            context["exports"] = []

        return context

    def _build_session(self, context: dict):
        """Ensure context has session-like keys needed by export_service."""
        context.setdefault("df", None)
        context.setdefault("data_summary", {})
        context.setdefault("analysis", {})
        context.setdefault("charts", [])
        context.setdefault("active_theme", "business")
        context.setdefault("style_overrides", {})
