# 快速入门指南

## 🎯 5 分钟上手新版 RAG 系统

### 步骤 1: 确认环境

```bash
# 确认 Python 版本（需要 3.10+）
python --version

# 确认在项目目录
cd E:\coding\RAG\rag
```

### 步骤 2: 安装依赖（如果还没安装）

```bash
pip install -r requirements.txt
```

### 步骤 3: 配置 API Key

#### 选项 A：使用环境变量（推荐）

复制 `.env.example` 为 `.env`：
```bash
copy .env.example .env
```

编辑 `.env` 文件，添加你的 API Key：
```env
DEEPSEEK_API_KEY=sk-your-api-key-here
```

#### 选项 B：直接设置环境变量

PowerShell:
```powershell
$env:DEEPSEEK_API_KEY="sk-your-api-key-here"
```

### 步骤 4: 启动服务

```bash
python start.py
```

或者：
```bash
uvicorn app.main:app --reload --port 8000
```

### 步骤 5: 访问应用

打开浏览器访问：
- **Web 界面**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

---

## 🧪 测试 API

### 1. 检索预览（不调用 LLM，速度快）

```bash
# PowerShell
curl "http://localhost:8000/ask?q=运动会"
```

或在浏览器访问：
```
http://localhost:8000/ask?q=运动会
```

### 2. RAG 问答（调用 LLM，生成答案）

```bash
# PowerShell
curl "http://localhost:8000/chat?q=学校运动会什么时候举行"
```

或在浏览器访问：
```
http://localhost:8000/chat?q=学校运动会什么时候举行
```

---

## 🔧 配置说明

### 切换 LLM 提供商

编辑 `.env` 文件：

```env
# 使用 OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-3.5-turbo
OPENAI_API_KEY=sk-your-key

# 使用 DeepSeek（默认）
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
DEEPSEEK_API_KEY=sk-your-key

# 使用通义千问
LLM_PROVIDER=qwen
LLM_MODEL=qwen-turbo
DASHSCOPE_API_KEY=sk-your-key

# 使用智谱 GLM
LLM_PROVIDER=zhipu
LLM_MODEL=glm-4
ZHIPU_API_KEY=your-key
```

### 启用重排模型（可选）

在 `.env` 中添加：
```env
RERANK_MODEL=BAAI/bge-reranker-base
```

这会在首次检索后使用重排模型提升结果质量（但会增加延迟）。

---

## 🐛 常见问题

### Q1: 启动时报错 "FileNotFoundError: 索引文件不存在"

**原因**: 还没有构建索引

**解决**:
```bash
cd tools
python build_index.py
```

### Q2: 启动时报错 "pydantic.errors.PydanticUserError"

**原因**: 配置文件格式错误

**解决**: 检查 `.env` 文件格式，确保没有多余空格

### Q3: API 返回 500 错误 "Incorrect API key"

**原因**: API Key 未配置或配置错误

**解决**: 
1. 检查 `.env` 文件中的 API Key
2. 确认对应的提供商 Key 名称正确（DEEPSEEK_API_KEY/OPENAI_API_KEY 等）

### Q4: 模型加载很慢

**说明**: 这是正常的！新版本使用**延迟加载**：
- 首次请求时才加载模型（约 5-10 秒）
- 后续请求会直接使用已加载的模型（毫秒级）

---

## 📚 进阶使用

### 添加新数据

1. **爬取数据**:
```bash
cd tools
python crawl.py --start "https://..." --out ../dataset
```

2. **分块处理**:
```bash
python chunking.py
```

3. **重建索引**:
```bash
python build_index.py
```

4. **重启服务** 即可使用新数据

### 使用 Python API

```python
from app.core.config import Settings
from app.models.llm import make_llm
from app.services.retrieval import RetrievalService
from app.services.qa import QAService

# 初始化
settings = Settings()
retrieval = RetrievalService(
    index_dir=settings.index_dir,
    embed_model_name=settings.embed_model,
    topk_final=8
)
llm = make_llm("deepseek")
qa = QAService(retrieval, llm)

# 使用
response = qa.answer_question("学校运动会什么时候举行？")
print(response.answer)
print(response.references)
```

---

## 🎓 架构说明

```
你的请求 → API层 → 服务层 → 模型层 → 外部服务
           (路由)   (业务)   (数据)   (LLM/索引)
```

**优势**:
- ✅ 每层职责单一
- ✅ 易于测试和维护
- ✅ 可独立替换组件

---

## 📞 获取帮助

- 查看详细文档: `README.md`
- 查看重构总结: `REFACTORING_SUMMARY.md`
- 查看项目结构: `PROJECT_STRUCTURE.md`
- API 交互式文档: http://localhost:8000/docs

---

**祝您使用愉快！** 🎉

