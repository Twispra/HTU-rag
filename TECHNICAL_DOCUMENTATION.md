# HTU-RAG 技术文档

HTU-RAG 是河南师范大学（HTU）教务处通知公告的智能问答系统。该项目基于 RAG（检索增强生成）技术，结合大语言模型（LLM）和向量检索，能够根据教务处的历史通知文档回答用户问题。此外，系统还具备多模态能力，支持图片（OCR/CLIP）和音频（Whisper）作为查询输入。

---

## 1. 项目简介

本项目旨在解决校园信息检索困难的问题。通过爬取教务处通知公告，构建向量知识库，利用 LLM 的语义理解和生成能力，为师生提供准确、及时的问答服务。

### 核心特性

- **多源数据支持**：自动爬取并处理教务处网页通知。
- **高精度检索**：使用 BGE Embedding 模型 + FAISS 向量索引 + BGE Reranker 重排策略。
- **多模态交互**：
    - **图片**：支持上传图片，利用 PaddleOCR 提取文字，或使用 CLIP 模型进行语义检索。
    - **音频**：集成 OpenAI Whisper 模型，支持语音转文字查询。
- **灵活的 LLM 支持**：通过统一接口支持 OpenAI (GPT-3.5/4)、DeepSeek、Qwen 等多种模型。
- **高性能架构**：基于 FastAPI 构建异步 API 服务，支持高并发访问。

---

## 2. 系统架构

系统整体采用典型的 RAG 架构，包含数据处理流水线和在线服务两部分。

### 2.1 数据流水线 (Data Pipeline)

位于 `tools/` 目录下，负责数据的获取与索引构建：

1.  **数据采集 (Crawler)**：`tools/crawl/`
    -   爬取教务处网站通知，通过 `beautifulsoup4` 解析 HTML。
    -   数据清洗与结构化存储。
2.  **文本分块 (Chunking)**：`tools/chunking/`
    -   将长文档切分为语义完整的段落或句子块，便于检索。
3.  **向量化与索引 (Embedding & Indexing)**：`tools/index_embedding/`
    -   使用 `SentenceTransformer` (BGE-base) 将文本块转化为向量。
    -   使用 `FAISS` 构建高效的向量索引 (`faiss.index`)。
    -   (可选) 构建图片和音频的向量索引 (`faiss_image.index`, `faiss_audio.index`)。

### 2.2 在线服务 (Online Service)

位于 `app/` 目录下，负责处理用户请求：

1.  **API 层** (`app/api/`)：定义 RESTful 接口，处理请求参数验证。
2.  **服务层** (`app/services/`)：
    -   `retrisval.py`: 封装 FAISS 检索与 Reranker 重排逻辑。
    -   `qa.py`: 核心 RAG 流程，组装 Prompt 并调用 LLM。
    -   `multimodal*.py`: 处理多模态输入（OCR、语音识别）与多模态检索融合。
3.  **核心配置** (`app/core/`)：管理配置项 (`config.py`) 和 Prompt 模板 (`prompts.py`)。
4.  **模型层** (`app/models/`)：定义 LLM 客户端接口 (`llm.py`) 和数据模型 (`schemas.py`)。

---

## 3. 目录结构说明

```
HTU-RAG/
├── app/                        # 应用源码
│   ├── api/                    # API 路由定义
│   ├── core/                   # 核心配置与工具
│   ├── models/                 # Pydantic 模型与 LLM 客户端
│   ├── services/               # 业务逻辑服务
│   ├── main.py                 # FastAPI 入口文件
│   └── __init__.py
├── dataset/                    # 数据存储目录
│   ├── chunks/                 # 分块后的 JSONL 数据
│   ├── crawl_state.json        # 爬虫状态记录
│   ├── database/               # 原始或中间数据存储
│   ├── index/                  # FAISS 索引文件 (.index)
│   └── media/                  # 图片/音频媒体文件
├── templates/                  # 前端 HTML 模板
│   └── index.html              # 聊天界面
├── tools/                      # 工具脚本
│   ├── chunking/               # 文本分块工具
│   ├── crawl/                  # 爬虫工具
│   └── index_embedding/        # 索引构建工具
├── requirements.txt            # 项目依赖
├── TECHNICAL_DOCUMENTATION.md  # 本文档
└── .env                        # 环境变量配置文件
```

---

## 4. 安装与配置

### 4.1 环境依赖

请确保 Python 版本 >= 3.8。

```bash
# 安装基础依赖
pip install -r requirements.txt

# 如果需要 OCR 功能 (PaddlePaddle)
# CPU 版本
pip install paddlepaddle paddleocr
# GPU 版本 (请根据 CUDA 版本选择)
# pip install paddlepaddle-gpu paddleocr
```

### 4.2 配置文件 (.env)

在项目根目录创建 `.env` 文件，配置 LLM API Key 和其他选项：

```ini
# --- LLM 配置 ---
# 可选: openai, deepseek, qwen, zhipu
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
# API Key (根据所选 Provider 配置)
DEEPSEEK_API_KEY=your_deepseek_api_key
OPENAI_API_KEY=your_openai_api_key

# --- 检索配置 ---
# 嵌入模型 (默认 BAAI/bge-base-zh-v1.5)
EMBED_MODEL=BAAI/bge-base-zh-v1.5
# 重排模型 (默认 BAAI/bge-reranker-base)
RERANK_MODEL=BAAI/bge-reranker-base

# --- 多模态功能开关 ---
ENABLE_MULTIMODAL=true        # 是否启用多模态 API
ENABLE_MEDIA_RETRIEVAL=false  # 是否启用基于向量的媒体检索
USE_OCR=true                  # 是否启用 OCR 图片文字识别
```

---

## 5. 数据处理流程

### 第一步：爬取数据

```bash
cd tools/crawl
python run_crawler.py
```
此命令将抓取教务处通知并保存到 `dataset/` 目录。

### 第二步：数据分块

```bash
cd tools/chunking
python chunking.py
```
将爬取的数据处理为适合检索的小块 (chunks)。

### 第三步：构建索引

```bash
cd tools/index_embedding
python build_index.py
```
生成文本向量索引文件 `dataset/index/faiss.index` 及元数据。

如果启用了多模态检索：
```bash
python build_multimodal_index.py
```

---

## 6. 启动服务

在项目根目录下运行：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

服务启动后，访问：
- **Web 界面**: `http://127.0.0.1:8000/`
- **API 文档**: `http://127.0.0.1:8000/docs`

---

## 7. API 参考

### 基础问答

- **GET /chat**
    - 参数: `q` (问题文本)
    - 返回: JSON，包含 `answer` (LLM 回答) 和 `references` (参考文档片段)。

### 多模态问答 (Post)

- **POST /ask-multimodal**
- **POST /chat-multimodal**
    - 参数 (Form Data):
        - `text`: 文本问题 (可选)
        - `image`: 图片文件 (可选，支持 jpg/png)
        - `audio`: 音频文件 (可选，支持 mp3/wav)
    - 功能: 自动识别图片文字 (OCR) 或转换语音 (Whisper)，结合文本进行 RAG 检索回答。

---

## 8. 技术栈详情

- **Web 框架**: FastAPI, Uvicorn
- **向量检索**: FAISS (Facebook AI Similarity Search)
- **NLP 模型**:
    - Embedding: `Sentence-Transformers` (HuggingFace)
    - Rerank: `FlagEmbedding`
    - LLM SDK: `openai` (Official Python Client)
- **多模态**:
    - Image: OpenAI CLIP, PaddleOCR
    - Audio: OpenAI Whisper
- **工具库**: Pandas, Pydantic, NumPy

---

## 9. 常见问题 (FAQ)

**Q: 启动时报错 `ModuleNotFoundError: No module named 'paddle'`?**
A: 请确保已安装 `paddlepaddle` 和 `paddleocr`。如果不需要 OCR 功能，可在 `.env` 中设置 `USE_OCR=false` 并忽略相关导入错误。

**Q: 第一次运行非常慢？**
A: 首次运行时，需要下载 Embedding 模型 (BGE)、Reranker 模型、CLIP 模型和 Whisper 模型，请保持网络通畅。

**Q: 如何更换 LLM 模型？**
A: 修改 `.env` 中的 `LLM_PROVIDER` 和对应的 API Key 即可切换不同厂商的模型 (如 DeepSeek, OpenAI)。
