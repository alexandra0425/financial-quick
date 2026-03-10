#!/bin/bash
# 启动 FinQA 后端
# 使用前先设置环境变量：export OPENROUTER_API_KEY=your_key

if [ -z "$OPENROUTER_API_KEY" ]; then
  echo "⚠️  请先设置 OPENROUTER_API_KEY："
  echo "   export OPENROUTER_API_KEY=your_key_here"
  exit 1
fi

echo "🚀 启动 FinQA 后端..."
cd "$(dirname "$0")"
python3 backend/main.py
