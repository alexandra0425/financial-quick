"""
news.py - 新闻搜索模块
复用 NashNova 的 ES 新闻搜索能力
"""

import subprocess
import json
import sys
import os

# ES搜索脚本路径（NashNova demo里已有）
ES_SCRIPT = os.path.join(
    os.path.dirname(__file__),
    "../../nashnova/demo/tools/es_news_search.py"
)

# 资产名称到搜索词映射
ASSET_NEWS_TERMS = {
    "BABA": ["阿里巴巴", "BABA", "阿里"],
    "TSLA": ["特斯拉", "Tesla", "TSLA"],
    "NVDA": ["英伟达", "NVIDIA", "NVDA"],
    "AAPL": ["苹果", "Apple", "AAPL"],
    "GOOGL": ["谷歌", "Google", "GOOGL"],
    "MSFT": ["微软", "Microsoft", "MSFT"],
    "AMZN": ["亚马逊", "Amazon", "AMZN"],
    "BTC-USD": ["比特币", "Bitcoin", "BTC"],
    "GC=F": ["黄金", "Gold", "XAUUSD"],
    "0700.HK": ["腾讯", "Tencent"],
}


def search_news(symbol: str, size: int = 5) -> list:
    """搜索资产相关新闻"""
    entities = ASSET_NEWS_TERMS.get(symbol, [symbol])

    # 如果ES脚本存在，使用它
    if os.path.exists(ES_SCRIPT):
        try:
            cmd = [sys.executable, ES_SCRIPT, "--entities"] + entities[:2] + ["--size", str(size)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            data = json.loads(result.stdout)
            news = data.get("results", [])
            return [
                {
                    "title": n.get("title", ""),
                    "url": n.get("url", ""),
                    "timestamp": n.get("timestamp", ""),
                }
                for n in news if n.get("title")
            ]
        except Exception:
            pass

    # Fallback: 用 web search 获取新闻（不依赖ES）
    return _fallback_news(symbol, entities)


def _fallback_news(symbol: str, entities: list) -> list:
    """备用新闻获取（模拟数据，真实环境应接入真实API）"""
    # 实际部署时可接入 NewsAPI、Alpha Vantage News 等
    return []


def get_news_context(symbol: str) -> str:
    """生成新闻上下文字符串，供LLM使用"""
    news = search_news(symbol, size=5)
    if not news:
        return ""

    lines = ["## 相关新闻（近期）"]
    for n in news:
        ts = n.get("timestamp", "")[:10] if n.get("timestamp") else ""
        title = n.get("title", "")
        url = n.get("url", "")
        lines.append(f"- [{title}]({url}) `{ts}`")

    return "\n".join(lines)


if __name__ == "__main__":
    ctx = get_news_context("BABA")
    print(ctx or "（无新闻数据）")
