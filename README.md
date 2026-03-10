# FinQA — 金融资产智能问答系统

基于大模型的全栈金融资产问答系统，支持实时行情查询和金融知识问答。

---

## 系统架构

```
用户输入
    │
    ▼
┌─────────────────────────────────────────────┐
│              路由器 (router.py)               │
│  Claude 意图分类 → market / knowledge / both  │
└──────────────┬──────────────────────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
┌────────────┐   ┌─────────────┐
│  行情模块   │   │  RAG 模块   │
│ market.py  │   │   rag.py    │
│            │   │             │
│Yahoo Finance│  │ 字符n-gram  │
│实时价格    │   │ 向量检索    │
│历史走势    │   │ 金融知识库  │
└─────┬──────┘   └──────┬──────┘
      │                 │
      ▼                 ▼
┌─────────────────────────────┐
│         新闻模块             │
│        news.py              │
│  ES新闻搜索 / 影响因素分析   │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│       LLM 生成 (llm.py)     │
│   Claude 3.5 Sonnet         │
│   区分客观数据 vs 分析描述   │
│   防hallucination设计        │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│    Flask API (main.py)      │
│    POST /api/ask            │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│    前端 (frontend/index.html)│
│  对话界面 + 走势图 + 路由标签 │
└─────────────────────────────┘
```

---

## 快速开始

### 1. 安装依赖

```bash
pip3 install flask flask-cors requests numpy
```

### 2. 启动后端

```bash
python3 backend/main.py
```

后端运行在 `http://localhost:5001`

### 3. 打开前端

直接用浏览器打开 `frontend/index.html`

---

## 技术选型说明

| 模块 | 技术 | 选择原因 |
|---|---|---|
| 后端框架 | Flask | 轻量，适合快速原型 |
| 行情数据 | Yahoo Finance API | 免费，覆盖全球主流资产，无需注册 |
| LLM | Claude 3.5 Sonnet（via OpenRouter）| 金融分析能力强，支持中英文 |
| 向量检索 | 字符 n-gram + 余弦相似度 | 零依赖，支持中文，避免外部API依赖 |
| 意图分类 | Claude 3.5 Haiku | 用LLM做路由，准确率远超规则方法 |
| 前端 | 原生HTML + Chart.js | 无框架依赖，部署零成本 |
| 新闻数据 | ES新闻库（Wallstreetcn.com） | 接入现有数据基础设施 |

---

## Prompt 设计思路

### 1. 意图分类 Prompt（router.py）

**设计目标：** 准确区分行情类 / 知识类 / 综合类问题

**核心设计：**
- 要求返回结构化 JSON，避免自由发挥
- 同时提取 `symbol_hint`（资产代码）和 `days_hint`（时间范围）
- 内置 fallback 规则，防止 API 故障

### 2. 回答生成 Prompt（llm.py）

**核心原则：**
```
严格区分"客观数据"与"分析性描述"
- 客观数据（价格、涨跌幅）→ 直接陈述
- 分析性描述（原因、趋势）→ 明确标注「分析」或「可能原因」
```

**防 hallucination 设计：**
- 所有数据通过 context 注入，不让模型凭记忆回答行情数据
- 要求"数据不足时明确说不知道"
- 末尾强制添加免责声明

---

## 数据来源

| 数据类型 | 来源 | 说明 |
|---|---|---|
| 实时行情 | Yahoo Finance API | 免费，延迟约15分钟 |
| 历史价格 | Yahoo Finance API | 日线数据，最长5年 |
| 金融知识 | 内置知识库（12条） | 涵盖估值/财务/技术分析/宏观 |
| 相关新闻 | ES新闻库（wallstreetcn.com） | 近7天中文财经新闻 |

---

## 优化与扩展思考

### 当前版本的局限

1. **向量检索精度有限**：使用字符 n-gram 向量，准确率不如 embedding 模型（如 text-embedding-3-small）
2. **知识库规模小**：仅12条记录，实际应接入更大的金融知识库（如 Investopedia）
3. **行情数据延迟**：Yahoo Finance 免费接口有约15分钟延迟

### 生产环境改进方向

1. **向量检索升级**：使用 OpenAI embeddings + ChromaDB / Pinecone，精度大幅提升
2. **知识库扩充**：爬取 Investopedia、SEC 财报，构建更大规模知识库
3. **流式输出**：接入 Claude streaming API，提升回答体验
4. **多轮对话**：加入会话历史管理，支持追问
5. **实时数据**：接入付费行情 API（如 Alpha Vantage、Financial Modeling Prep）获取实时数据

---

## 项目结构

```
finqa/
├── backend/
│   ├── main.py       # Flask API 入口
│   ├── router.py     # 意图识别 / 查询路由
│   ├── market.py     # 行情数据（Yahoo Finance）
│   ├── rag.py        # RAG 向量检索
│   ├── llm.py        # LLM 回答生成
│   ├── news.py       # 新闻搜索
│   └── knowledge/
│       └── vector_db.json  # 向量数据库（自动生成）
├── frontend/
│   └── index.html    # 前端界面
└── README.md
```
