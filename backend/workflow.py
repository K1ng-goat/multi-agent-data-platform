import json
import os
import httpx

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


def build_planning_prompt(columns: list[str], dtypes: dict, sample: list[dict], user_request: str) -> str:
    return f"""你是一个数据分析工作流规划器。根据用户需求和数据列信息，规划分析步骤。

## 可用工具
- compute_stat: 计算平均值/最大值/最小值/总和/标准差/中位数 (参数: column, stat)
- sort_data: 排序取Top N (参数: column, order, top_n)
- group_by: 分组聚合 (参数: group_col, value_col, agg)
- analyze_trend: 趋势分析 (参数: order_col, value_col)
- filter_data: 条件筛选 (参数: column, op, value)
- describe_data: 整体描述统计 (参数: column 可选)

## 数据信息
- 列名: {columns}
- 数据类型: {json.dumps(dtypes, ensure_ascii=False)}
- 样本: {json.dumps(sample[:3], ensure_ascii=False)}

## 用户需求
{user_request}

## 要求
规划3-6个分析步骤，每步调用一个工具。返回纯JSON（不要markdown代码块）：

{{
  "title": "报告标题",
  "steps": [
    {{"name": "步骤名称", "tool": "工具名", "args": {{...}}}}
  ]
}}"""


async def plan_workflow(columns: list[str], dtypes: dict, sample: list[dict],
                        user_request: str, api_key: str) -> dict:
    """Ask AI to generate a workflow plan."""
    prompt = build_planning_prompt(columns, dtypes, sample, user_request)

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            },
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

    # Parse JSON from response
    content = content.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    return json.loads(content)


async def generate_report(plan_title: str, steps_with_results: list[dict],
                          user_request: str, api_key: str) -> str:
    """Ask AI to compile a final report from all step results."""
    results_text = "\n\n".join(
        f"## {s['name']}\n工具: {s['tool']}\n结果: {s['result']}"
        for s in steps_with_results
    )

    prompt = f"""根据以下分析结果，生成一份专业的数据分析报告。用中文，Markdown格式。

## 报告标题
{plan_title}

## 用户原始需求
{user_request}

## 分析步骤和结果
{results_text}

## 要求
- 结构清晰，包含：概述、详细分析、关键发现、建议
- 用数据说话，引用具体数值
- 指出异常和趋势
- 500字以内"""

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
