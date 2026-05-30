"""AuditAgent — wraps data quality audit and anomaly detection logic."""
import pandas as pd

from .base_agent import BaseAgent


class AuditAgent(BaseAgent):
    name = "AuditAgent"
    description = "数据审计与异常检测"

    async def execute(self, context: dict) -> dict:
        df = context.get("df")
        if df is None:
            self.add_step(context, "error", "无可用数据进行审计")
            return context

        self.add_step(context, "running", "开始数据审计...")

        try:
            audit_result = self.audit(df)
            context["audit_result"] = audit_result
            issues = audit_result.get("issues", [])
            score = audit_result.get("quality_score", 100)
            self.add_step(context, "done",
                f"数据审计完成: 质量评分 {score}/100, {len(issues)} 个问题")
        except Exception as e:
            self.add_step(context, "error", f"数据审计失败: {str(e)}")
            context.setdefault("errors", []).append(f"AuditAgent: {str(e)}")
            context["audit_result"] = {"quality_score": 0, "issues": [str(e)]}

        return context

    def audit(self, df: pd.DataFrame) -> dict:
        """Run complete data audit: nulls, duplicates, types, outliers."""
        issues = []
        total_rows = len(df)

        # 1. Null value check
        null_counts = df.isnull().sum()
        for col, cnt in null_counts.items():
            if cnt > 0:
                pct = round(cnt / total_rows * 100, 1)
                level = "error" if pct > 20 else ("warning" if pct > 5 else "info")
                issues.append({
                    "type": "null",
                    "column": str(col),
                    "count": int(cnt),
                    "percent": pct,
                    "level": level,
                    "message": f"列 '{col}' 存在 {cnt} 个空值 ({pct}%)",
                })

        # 2. Duplicate check
        dup_count = int(df.duplicated().sum())
        if dup_count > 0:
            dup_pct = round(dup_count / total_rows * 100, 1)
            issues.append({
                "type": "duplicate",
                "count": dup_count,
                "percent": dup_pct,
                "level": "warning",
                "message": f"存在 {dup_count} 行重复数据 ({dup_pct}%)",
            })

        # 3. Numeric column outlier check (Z-score method)
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        for col in numeric_cols[:6]:
            series = df[col].dropna()
            if len(series) < 3:
                continue
            mean, std = series.mean(), series.std()
            if std == 0:
                continue
            z_scores = ((series - mean) / std).abs()
            outliers = (z_scores > 3).sum()
            if outliers > 0:
                issues.append({
                    "type": "outlier",
                    "column": str(col),
                    "count": int(outliers),
                    "level": "warning",
                    "message": f"列 '{col}' 检测到 {outliers} 个异常值 (Z-score > 3)",
                })

        # 4. Quality score
        score = 100
        for issue in issues:
            if issue.get("level") == "error":
                score -= 15
            elif issue.get("level") == "warning":
                score -= 5
            else:
                score -= 1
        score = max(0, min(100, score))

        return {
            "quality_score": score,
            "total_rows": total_rows,
            "total_columns": len(df.columns),
            "numeric_columns": len(numeric_cols),
            "issues": issues,
            "quality_report": self.quality_summary(score, issues),
        }

    def quality_summary(self, score: int, issues: list[dict]) -> str:
        """Generate human-readable quality summary."""
        if score >= 95:
            grade = "优秀"
            advice = "数据质量良好，可直接用于分析。"
        elif score >= 80:
            grade = "良好"
            advice = "存在少量问题，建议在分析前处理。"
        elif score >= 60:
            grade = "一般"
            advice = "存在较多问题，可能影响分析准确性。"
        else:
            grade = "较差"
            advice = "数据质量问题严重，强烈建议先清洗数据。"

        parts = [f"数据质量评分: {score}/100 ({grade})"]
        error_count = sum(1 for i in issues if i.get("level") == "error")
        warn_count = sum(1 for i in issues if i.get("level") == "warning")
        if error_count or warn_count:
            parts.append(f"发现 {error_count} 个严重问题, {warn_count} 个警告")
        parts.append(advice)
        return "。".join(parts)
