"""
market.py - 行情数据模块
通过 Yahoo Finance API 获取实时和历史行情
"""

import requests
from datetime import datetime, timedelta
from typing import Optional

SYMBOL_MAP = {
    "阿里巴巴": "BABA", "阿里": "BABA", "alibaba": "BABA",
    "腾讯": "0700.HK", "tencent": "0700.HK",
    "特斯拉": "TSLA", "tesla": "TSLA",
    "英伟达": "NVDA", "nvidia": "NVDA",
    "苹果": "AAPL", "apple": "AAPL",
    "谷歌": "GOOGL", "google": "GOOGL",
    "微软": "MSFT", "microsoft": "MSFT",
    "亚马逊": "AMZN", "amazon": "AMZN",
    "比特币": "BTC-USD", "bitcoin": "BTC-USD", "btc": "BTC-USD",
    "黄金": "GC=F", "gold": "GC=F",
    "标普500": "^GSPC", "s&p500": "^GSPC", "sp500": "^GSPC",
    "纳斯达克": "^IXIC", "nasdaq": "^IXIC",
    "原油": "CL=F", "oil": "CL=F",
}

HEADERS = {"User-Agent": "Mozilla/5.0"}


def resolve_symbol(query: str) -> Optional[str]:
    """将中英文资产名称解析为 Yahoo Finance 代码"""
    query_lower = query.lower().strip()
    # 直接是代码（大写字母数字）
    if query.upper() == query and len(query) <= 6:
        return query.upper()
    # 名称映射
    for name, sym in SYMBOL_MAP.items():
        if name in query_lower or name in query:
            return sym
    return None


def get_market_data(query: str, days: int = 7) -> dict:
    """主入口：从自然语言问题提取资产并获取行情数据（覆盖原函数）"""
    symbol = resolve_symbol(query)
    if not symbol:
        symbol = query.upper().replace(" ", "")

    quote = get_quote(symbol)
    if "error" in quote:
        return {"error": f"无法获取 {symbol} 的行情数据", "symbol": symbol}

    history = get_history(symbol, days)
    return {"symbol": symbol, "quote": quote, "history": history}


def get_quote(symbol: str) -> dict:
    """获取实时报价"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=2d"
        r = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
        result = data["chart"]["result"][0]
        meta = result["meta"]

        price = meta.get("regularMarketPrice")
        prev = meta.get("previousClose") or meta.get("chartPreviousClose")
        change = price - prev if price and prev else 0
        change_pct = change / prev * 100 if prev else 0

        return {
            "symbol": symbol,
            "price": round(price, 4) if price else None,
            "prev_close": round(prev, 4) if prev else None,
            "change": round(change, 4),
            "change_pct": round(change_pct, 2),
            "currency": meta.get("currency", "USD"),
            "exchange": meta.get("exchangeName", ""),
            "market_state": meta.get("marketState", ""),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


def get_history(symbol: str, days: int = 7) -> dict:
    """获取历史价格和涨跌幅"""
    try:
        range_map = {7: "10d", 30: "1mo", 90: "3mo", 180: "6mo", 365: "1y"}
        range_str = range_map.get(days, "1mo")

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range={range_str}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        data = r.json()
        result = data["chart"]["result"][0]

        timestamps = result["timestamp"]
        closes = result["indicators"]["quote"][0]["close"]

        # 过滤掉 None 值
        points = [
            {
                "date": datetime.fromtimestamp(ts).strftime("%Y-%m-%d"),
                "close": round(c, 4),
            }
            for ts, c in zip(timestamps, closes)
            if c is not None
        ]

        # 只取最近 days 个交易日
        points = points[-days:]

        if len(points) < 2:
            return {"symbol": symbol, "error": "数据不足"}

        start_price = points[0]["close"]
        end_price = points[-1]["close"]
        total_change = end_price - start_price
        total_change_pct = total_change / start_price * 100

        # 趋势判断
        if total_change_pct > 3:
            trend = "上涨"
        elif total_change_pct < -3:
            trend = "下跌"
        else:
            trend = "震荡"

        # 最高/最低
        all_closes = [p["close"] for p in points]
        high = max(all_closes)
        low = min(all_closes)

        return {
            "symbol": symbol,
            "period_days": len(points),
            "start_price": start_price,
            "end_price": end_price,
            "change": round(total_change, 4),
            "change_pct": round(total_change_pct, 2),
            "high": high,
            "low": low,
            "trend": trend,
            "points": points,
        }
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}


if __name__ == "__main__":
    # 测试
    result = get_market_data("阿里巴巴", days=7)
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
