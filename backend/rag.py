"""
rag.py - RAG 检索模块
使用 numpy 手写轻量向量检索，不依赖 chromadb
原理：把文档和问题都转成向量，计算余弦相似度，找最相关片段
"""

import json
import os
import numpy as np
import requests
from typing import List, Tuple

import os
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
EMBED_MODEL = "text-embedding-3-small"  # OpenAI embedding


# ---------------------------------------------------------------------------
# 向量化（调用 OpenAI embeddings API）
# ---------------------------------------------------------------------------

def get_embedding(text: str) -> List[float]:
    """把文本转成向量（1536维）"""
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if not openai_key:
        return _simple_embedding(text)
    try:
        r = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {openai_key}"},
            json={"model": EMBED_MODEL, "input": text},
            timeout=15,
        )
        return r.json()["data"][0]["embedding"]
    except Exception:
        return _simple_embedding(text)


def _simple_embedding(text: str, dim: int = 512) -> List[float]:
    """备用：字符级 n-gram 向量（支持中文）"""
    import hashlib
    vec = [0.0] * dim
    # 字符级 unigram
    for ch in text:
        idx = int(hashlib.md5(ch.encode('utf-8')).hexdigest(), 16) % dim
        vec[idx] += 1.0
    # 字符级 bigram
    for i in range(len(text) - 1):
        bigram = text[i:i+2]
        idx = int(hashlib.md5(bigram.encode('utf-8')).hexdigest(), 16) % dim
        vec[idx] += 2.0  # bigram 权重更高
    # 空格分词（英文）
    for word in text.lower().split():
        idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % dim
        vec[idx] += 1.5
    norm = sum(v**2 for v in vec) ** 0.5
    return [v / norm if norm > 0 else 0.0 for v in vec]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """计算余弦相似度"""
    a, b = np.array(a), np.array(b)
    if np.linalg.norm(a) == 0 or np.linalg.norm(b) == 0:
        return 0.0
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# ---------------------------------------------------------------------------
# 知识库管理
# ---------------------------------------------------------------------------

DB_PATH = os.path.join(os.path.dirname(__file__), "knowledge", "vector_db.json")


def load_db() -> List[dict]:
    """加载向量数据库"""
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_db(docs: List[dict]):
    """保存向量数据库"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)


def add_document(text: str, metadata: dict = None):
    """添加文档到知识库"""
    db = load_db()
    embedding = _simple_embedding(text)  # 用简单向量，不消耗API
    db.append({
        "text": text,
        "metadata": metadata or {},
        "embedding": embedding,
    })
    save_db(db)
    return len(db)


def search(query: str, top_k: int = 3) -> List[Tuple[str, float]]:
    """检索最相关的文档片段"""
    db = load_db()
    if not db:
        return []

    query_vec = _simple_embedding(query)
    scored = [
        (doc["text"], cosine_similarity(query_vec, doc["embedding"]), doc.get("metadata", {}))
        for doc in db
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [(text, score, meta) for text, score, meta in scored[:top_k] if score > 0.1]


# ---------------------------------------------------------------------------
# 初始化知识库（内置金融知识）
# ---------------------------------------------------------------------------

FINANCIAL_KNOWLEDGE = [
    {
        "text": "市盈率（P/E Ratio）是股票价格与每股收益的比值。公式：P/E = 股价 / EPS。市盈率越高，说明市场对公司未来增长预期越高，但也意味着估值越贵。一般来说，科技公司市盈率较高（20-50倍），传统行业较低（10-20倍）。",
        "metadata": {"topic": "估值", "type": "基础概念"}
    },
    {
        "text": "市净率（P/B Ratio）是股票价格与每股净资产的比值。公式：P/B = 股价 / 每股净资产。P/B < 1 可能意味着股票被低估，但也可能说明公司盈利能力差。银行、保险等金融公司常用P/B估值。",
        "metadata": {"topic": "估值", "type": "基础概念"}
    },
    {
        "text": "收入（Revenue）是公司销售产品或服务的总收入，又称营业收入。净利润（Net Income）是收入扣除所有成本、费用和税收后剩余的利润。毛利润（Gross Profit）= 收入 - 直接成本（COGS）。净利润率 = 净利润 / 收入 × 100%。",
        "metadata": {"topic": "财务指标", "type": "基础概念"}
    },
    {
        "text": "自由现金流（Free Cash Flow，FCF）= 经营现金流 - 资本支出。FCF是公司真正可以自由支配的资金，比净利润更难造假。巴菲特非常重视FCF，认为它是衡量公司真实盈利能力的最重要指标。",
        "metadata": {"topic": "现金流", "type": "基础概念"}
    },
    {
        "text": "EPS（每股收益，Earnings Per Share）= 净利润 / 流通股总数。EPS增长是股价上涨的核心驱动力。财报季最重要的两个数字：实际EPS是否超预期（Beat），以及下季度EPS指引是否上调。",
        "metadata": {"topic": "财务指标", "type": "基础概念"}
    },
    {
        "text": "ROE（股本回报率，Return on Equity）= 净利润 / 股东权益。ROE衡量公司用股东的钱赚钱的效率。巴菲特认为优秀公司应长期保持ROE > 15%。ROE可以通过提高利润率、提高资产周转率或增加财务杠杆来提升（杜邦分析）。",
        "metadata": {"topic": "盈利能力", "type": "基础概念"}
    },
    {
        "text": "Beta值衡量股票相对市场的波动性。Beta=1：与市场同步波动；Beta>1：波动比市场大（风险更高）；Beta<1：波动比市场小（更稳定）；Beta<0：与市场反向运动（如黄金ETF）。科技股Beta通常>1，公用事业股Beta通常<1。",
        "metadata": {"topic": "风险指标", "type": "基础概念"}
    },
    {
        "text": "股息率（Dividend Yield）= 年度每股股息 / 当前股价。成熟的公司通常定期支付股息（如可口可乐、宝洁）。成长型公司（如亚马逊早期）不派息，把利润用于再投资。高股息率可能是好事（稳定现金流），也可能是警示（股价大跌导致股息率虚高）。",
        "metadata": {"topic": "股息", "type": "基础概念"}
    },
    {
        "text": "技术分析中常用的均线系统：MA5（5日均线）、MA10（10日）、MA20（20日）、MA50（50日）、MA200（200日）。短期均线上穿长期均线（金叉）通常视为买入信号；下穿（死叉）视为卖出信号。但均线滞后，不能预测未来。",
        "metadata": {"topic": "技术分析", "type": "基础概念"}
    },
    {
        "text": "美联储（Federal Reserve）通过调整联邦基金利率影响经济。加息：抑制通胀，但可能减缓经济增长，对高估值成长股不利；降息：刺激经济，有利于股市，尤其利好成长股和房地产。2022-2023年美联储激进加息，导致纳斯达克大幅下跌。",
        "metadata": {"topic": "宏观经济", "type": "基础概念"}
    },
    {
        "text": "做多（Long）：买入资产，预期价格上涨后卖出获利。做空（Short）：借入资产卖出，预期价格下跌后低价买回归还，赚取差价。做空风险理论上无限（价格可以无限上涨），因此做空需要保证金。轧空（Short Squeeze）：当做空者集中平仓时，价格被急速推高，如2021年GameStop事件。",
        "metadata": {"topic": "交易概念", "type": "基础概念"}
    },
    {
        "text": "ETF（交易所交易基金）是一种可以像股票一样在交易所买卖的基金，通常跟踪某个指数。常见ETF：SPY（追踪标普500）、QQQ（追踪纳斯达克100）、GLD（追踪黄金价格）、XLE（能源板块）。ETF费率低，分散风险，适合长期投资。",
        "metadata": {"topic": "投资工具", "type": "基础概念"}
    },
]


def init_knowledge_base():
    """初始化金融知识库"""
    if os.path.exists(DB_PATH):
        db = load_db()
        if len(db) >= len(FINANCIAL_KNOWLEDGE):
            return len(db)  # 已初始化

    print("正在初始化金融知识库...")
    db = []
    for item in FINANCIAL_KNOWLEDGE:
        embedding = _simple_embedding(item["text"])
        db.append({
            "text": item["text"],
            "metadata": item["metadata"],
            "embedding": embedding,
        })
    save_db(db)
    print(f"知识库初始化完成，共 {len(db)} 条记录")
    return len(db)


if __name__ == "__main__":
    init_knowledge_base()
    results = search("什么是市盈率")
    for text, score, meta in results:
        print(f"[{score:.3f}] {text[:100]}")
