"""
main.py - Flask API 后端入口
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from router import classify_query
from market import get_market_data, resolve_symbol
from rag import search, init_knowledge_base
from llm import generate_answer
from news import get_news_context

app = Flask(__name__)
CORS(app)  # 允许前端跨域访问

# 启动时初始化知识库
init_knowledge_base()


@app.route("/api/ask", methods=["POST"])
def ask():
    """主问答接口"""
    data = request.get_json()
    question = data.get("question", "").strip()

    if not question:
        return jsonify({"error": "请输入问题"}), 400

    try:
        # 1. 意图分类
        route = classify_query(question)
        query_type = route.get("type", "market")
        days = route.get("days_hint", 7)

        market_data = None
        rag_results = None
        news_context = None

        # 2. 获取行情数据（market 或 both）
        if query_type in ("market", "both"):
            symbol_hint = route.get("symbol_hint") or question
            market_data = get_market_data(symbol_hint, days=days)

            # 同时获取新闻（用于原因分析）
            if market_data and "error" not in market_data:
                news_context = get_news_context(market_data.get("symbol", ""))

        # 3. RAG 检索（knowledge 或 both）
        if query_type in ("knowledge", "both"):
            rag_results = search(question, top_k=3)

        # 4. LLM 生成回答
        answer = generate_answer(
            question,
            market_data=market_data,
            rag_results=rag_results,
            news_context=news_context
        )

        # 提取走势图数据给前端
        chart_data = []
        if market_data and "history" in market_data and "error" not in market_data.get("history", {}):
            chart_data = market_data["history"].get("points", [])

        return jsonify({
            "question": question,
            "answer": answer,
            "meta": {
                "query_type": query_type,
                "symbol": market_data.get("symbol") if market_data else None,
                "rag_used": rag_results is not None and len(rag_results) > 0,
                "route_reason": route.get("reason", ""),
                "chart_data": chart_data,
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Financial QA System running"})


@app.route("/api/symbols", methods=["GET"])
def symbols():
    """返回支持的资产列表"""
    from market import SYMBOL_MAP
    return jsonify({"symbols": SYMBOL_MAP})


if __name__ == "__main__":
    print("🚀 Financial QA Backend starting on http://localhost:5001")
    app.run(host="0.0.0.0", port=5001, debug=False)
