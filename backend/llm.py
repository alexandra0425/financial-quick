"""
llm.py - LLM 生成模块
把行情数据 + RAG检索结果交给 Claude，生成结构化回答
"""

import requests
import json

import os
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
API_BASE = "https://openrouter.ai/api/v1"
MODEL = "anthropic/claude-3.5-sonnet"

SYSTEM_PROMPT = """你是一个专业的金融资产问答助手。

## 回答原则
1. **严格区分客观数据与分析性描述**
   - 客观数据（价格、涨跌幅）：直接陈述，不加修饰
   - 分析性描述（原因分析、趋势判断）：明确标注「分析」或「可能原因」
2. **不得编造数据**：如果没有相关数据，明确说"暂无数据"，不要推测
3. **结构清晰**：使用 Markdown 格式，数据优先，分析其次
4. **防止幻觉**：对于不确定的信息，使用「可能」「据报道」等限定语
5. **末尾必须加免责声明**：「⚠️ 以上内容仅供参考，不构成投资建议」

## 回答结构（根据问题类型选用）
- 行情问题：当前价格 → 涨跌幅 → 趋势总结 → 可能影响因素
- 知识问题：概念定义 → 计算方法 → 实际意义 → 示例
- 综合问题：数据部分 + 知识部分分开展示"""


def generate_answer(question: str, market_data: dict = None, rag_results: list = None, news_context: str = None) -> str:
    """
    生成最终回答
    - market_data: 行情数据（来自 market.py）
    - rag_results: RAG检索结果（来自 rag.py）
    """
    context_parts = []

    if market_data and "error" not in market_data:
        quote = market_data.get("quote", {})
        history = market_data.get("history", {})
        symbol = market_data.get("symbol", "")

        market_context = f"## 行情数据（实时，来源：Yahoo Finance）\n"
        market_context += f"- 资产代码：{symbol}\n"

        if quote and "error" not in quote:
            market_context += f"- 当前价格：{quote.get('currency', 'USD')} {quote.get('price', 'N/A')}\n"
            market_context += f"- 较昨收涨跌：{quote.get('change_pct', 0):+.2f}%（{quote.get('change', 0):+.4f}）\n"
            market_context += f"- 市场状态：{quote.get('market_state', '未知')}\n"

        if history and "error" not in history:
            market_context += f"\n## 历史走势（近{history.get('period_days', '?')}个交易日）\n"
            market_context += f"- 区间涨跌：{history.get('change_pct', 0):+.2f}%\n"
            market_context += f"- 最高价：{history.get('high', 'N/A')}\n"
            market_context += f"- 最低价：{history.get('low', 'N/A')}\n"
            market_context += f"- 趋势判断：{history.get('trend', '未知')}\n"

            points = history.get("points", [])
            if points:
                market_context += f"\n价格明细：\n"
                for p in points[-7:]:  # 最多显示7天
                    market_context += f"  - {p['date']}: {p['close']}\n"

        context_parts.append(market_context)

    if rag_results:
        rag_context = "## 相关金融知识（来源：知识库）\n"
        for text, score, meta in rag_results:
            if score > 0.15:  # 只用高相关度的
                rag_context += f"\n{text}\n"
        if len(rag_context) > 50:  # 确实有检索到内容
            context_parts.append(rag_context)

    if news_context:
        context_parts.append(news_context)

    if not context_parts:
        context_str = "（无额外数据）"
    else:
        context_str = "\n\n---\n\n".join(context_parts)

    user_message = f"""以下是相关数据，请回答用户的问题。

{context_str}

---

用户问题：{question}"""

    try:
        r = requests.post(
            f"{API_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "max_tokens": 1500,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            },
            timeout=60,
        )
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"生成回答时出错：{str(e)}"


if __name__ == "__main__":
    # 测试
    answer = generate_answer(
        "什么是市盈率？",
        rag_results=[("市盈率（P/E Ratio）是股票价格与每股收益的比值...", 0.8, {})]
    )
    print(answer)
