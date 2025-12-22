# 河南师范大学 RAG 智能问答系统 v4.0
**注意**：旧版文件已备份为 `*_old.py`，可随时参考或回滚。

---

欢迎提交 Issue 和 Pull Request！

## 👥 贡献

MIT License

## 📄 License

- 基础 RAG 功能实现

### v3.0.0（旧版）

- 🗑️ 移除冗余的 mLLM.py
- 🐛 修复 ChatOpenAI 缺失问题
- ✨ 完善文档和类型提示
- ✨ 添加单元测试框架
- ✨ 统一 Prompt 管理
- ✨ 添加 Pydantic 模型验证
- ✨ 实现延迟加载优化启动时间
- ✨ 完全重构为三层架构

### v4.0.0 (2025-12-22)

## 📝 更新日志

在 `app/api/routes.py` 中添加新路由。

### 添加新的 API 端点

编辑 `app/core/prompts.py` 中的 `PromptTemplates` 类。

### 自定义 Prompt

3. 更新配置和文档
2. 在 `make_llm()` 工厂函数中注册
1. 在 `app/models/llm.py` 中创建新类继承 `ChatLLM`

### 添加新的 LLM 提供商

## 🛠️ 开发指南

| **代码复用** | 困难 | Service 层可独立使用 |
| **扩展性** | 修改影响广 | 符合开闭原则 |
| **启动时间** | 立即加载所有模型 | 延迟加载 |
| **测试性** | 难以测试 | 易于单元测试 |
| **耦合度** | 高（use.py 包含所有逻辑） | 低（职责分离） |
| **架构** | 单文件混杂 | 三层架构 |
|------|-------------|-------------|
| 维度 | v3.0（旧版） | v4.0（新版） |

## 📊 重构对比

```
pytest tests/ -v
pip install pytest pytest-asyncio
```bash

## 🧪 运行测试

| `topk_final` | 最终返回数 | 8 |
| `topk_faiss` | FAISS 召回数 | 24 |
| `rerank_model` | 重排模型（可选） | None |
| `embed_model` | 嵌入模型 | BAAI/bge-small-zh-v1.5 |
| `llm_model` | 模型名称 | deepseek-chat |
| `llm_provider` | LLM 提供商 | deepseek |
|--------|------|--------|
| 配置项 | 说明 | 默认值 |

在 `app/core/config.py` 或 `.env` 中配置：

## 🎛️ 配置说明

```
python build_index.py
```bash

### 3. 构建索引

```
python chunking.py
```bash

### 2. 文本分块

```
python crawl.py --start "https://www.htu.edu.cn/teaching/3251/list.htm" --out ../dataset
cd tools
```bash

### 1. 爬取数据

## 🔧 数据处理流程

```
}
  ]
    }
      "source_url": "https://..."
      "title": "第62届运动会调、停课通知",
    {
  "references": [
  "answer": "根据学校通知，第62届运动会...",
  "query": "学校运动会是什么时候？",
{
```json
返回：

```
GET /chat?q=学校运动会是什么时候？
```bash

### 2. RAG 问答（调用 LLM）

```
]
  }
    "source_url": "https://..."
    "snippet": "关于**运动会**期间调课停课的通知...",
    "publish_date": "2025-04-14",
    "title": "第62届运动会调、停课通知",
  {
[
```json
返回：

```
GET /ask?q=学校运动会是什么时候？
```bash

### 1. 检索预览（不调用 LLM）

## 📡 API 接口

- **健康检查**: http://localhost:8000/health
- **API 文档**: http://localhost:8000/docs
- **Web 界面**: http://localhost:8000

### 4. 访问应用

```
python -m app.main
# 或直接运行

uvicorn app.main:app --reload --port 8000
# 开发模式（热重载）
```bash

### 3. 启动服务

```
INDEX_DIR=dataset/index
EMBED_MODEL=BAAI/bge-small-zh-v1.5
LLM_MODEL=deepseek-chat
LLM_PROVIDER=deepseek
# 可选配置（覆盖默认值）

ZHIPU_API_KEY=your_key_here
DASHSCOPE_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
DEEPSEEK_API_KEY=your_key_here
# LLM API Keys（根据使用的提供商配置）
```env

创建 `.env` 文件：

### 2. 配置环境变量

```
pip install -r requirements.txt
```bash

### 1. 安装依赖

## 🚀 快速开始

```
└── mLLM_old.py             # 旧版 Prompt
├── settings_old.py         # 旧版配置
├── llm_old.py              # 旧版 LLM
├── use_old.py              # 旧版主文件
# 已弃用（已备份）

└── tests/                   # 单元测试
├── static/                  # 静态资源
├── templates/               # HTML 模板
├── dataset/                 # 数据集
│   └── build_index.py      # 索引构建
│   ├── chunking.py         # 文本分块
│   ├── crawl.py            # 数据爬取
├── tools/                   # 工具脚本
│       └── prompts.py      # Prompt 模板
│       ├── config.py       # 配置管理
│   └── core/                # 核心配置
│   │   └── schemas.py      # Pydantic 模型
│   │   ├── llm.py          # LLM 客户端
│   ├── models/              # 数据模型层
│   │   └── qa.py           # 问答服务
│   │   ├── retrieval.py    # 文档检索服务
│   ├── services/            # 业务逻辑层
│   │   └── routes.py
│   ├── api/                 # API 路由层
│   ├── main.py              # FastAPI 入口
├── app/                      # 主应用
rag/
```

## 🏗️ 项目结构

- ✅ **易于测试**：服务层与业务逻辑分离
- ✅ **类型安全**：完整的类型提示和 Pydantic 模型
- ✅ **可插拔重排**：可选的重排模型提升检索精度
- ✅ **多 LLM 支持**：支持 OpenAI、DeepSeek、通义千问、智谱 GLM
- ✅ **延迟加载**：模型按需加载，减少启动时间
- ✅ **模块化架构**：清晰的三层架构（API/Service/Model）

## 📋 项目特性

基于检索增强生成（RAG）的智能问答系统，用于回答河南师范大学教务处相关问题。


