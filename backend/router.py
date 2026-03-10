"""
router.py - 查询路由模块（意图识别）
用 Claude 判断问题类型，分发到不同处理链路
"""

import requests
import re

import os
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
API_BASE = "https://openrouter.ai/api/v1"
MODEL = "anthropic/claude-3.5-haiku"


def classify_query(question: str) -> dict:
    """
    意图分类：判断问题属于哪类
    返回：{"type": "market"|"knowledge"|"both", "symbol_hint": "...", "days_hint": 7}
    """
    prompt = f"""分析以下金融问题，返回JSON格式的分类结果。

问题：{question}

返回格式（只返回JSON，不要其他文字）：
{{
  "type": "market" | "knowledge" | "both",
  "symbol_hint": "股票代码或资产名称，没有则为null",
  "days_hint": 数字（涉及的天数，默认7）,
  "reason": "分类原因（一句话）"
}}

分类规则：
- market：涉及具体资产的实时价格、涨跌幅、走势、为什么涨跌
- knowledge：金融概念解释、财务指标定义、投资知识问答
- both：同时需要实时数据和金融知识（如"市盈率多少算合理，BABA现在的市盈率是多少"）"""

    try:
        r = requests.post(
            f"{API_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=15,
        )
        content = r.json()["choices"][0]["message"]["content"].strip()
        # 提取JSON
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            import json
            return json.loads(match.group())
    except Exception as e:
        pass

    # fallback：简单关键词规则
    market_keywords = ["价格", "股价", "涨跌", "走势", "多少钱", "上涨", "下跌", "最近", "今天", "昨天", "7天", "30天", "大涨", "大跌"]
    knowledge_keywords = ["什么是", "是什么", "定义", "概念", "区别", "怎么计算", "为什么重要", "原理"]

    q_lower = question.lower()
    is_market = any(kw in question for kw in market_keywords)
    is_knowledge = any(kw in question for kw in knowledge_keywords)

    if is_market and is_knowledge:
        qtype = "both"
    elif is_market:
        qtype = "market"
    elif is_knowledge:
        qtype = "knowledge"
    else:
        qtype = "market"  # 默认市场类

    # 提取天数
    days = 7
    for pattern, d in [("7天", 7), ("7日", 7), ("一周", 7), ("30天", 30), ("一个月", 30), ("90天", 90), ("三个月", 90)]:
        if pattern in question:
            days = d
            break

    return {"type": qtype, "symbol_hint": None, "days_hint": days, "reason": "关键词规则"}


if __name__ == "__main__":
    tests = [
        "阿里巴巴当前股价是多少？",
        "BABA 最近7天涨跌情况如何？",
        "什么是市盈率？",
        "收入和净利润的区别是什么？",
        "特斯拉近期走势如何？",
        "阿里巴巴1月15日为什么大涨？",
    ]
    for q in tests:
        result = classify_query(q)
        print(f"Q: {q}")
        print(f"   → type={result['type']}, days={result.get('days_hint')}, reason={result.get('reason')}")
        print()
