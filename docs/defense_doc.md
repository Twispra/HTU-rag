# HTU RAG 智能问答系统（FastAPI）项目总结文档（用于 PPT / 论文答辩）

> 适用场景：PPT 汇报、论文答辩、项目说明书。

---

## 1. 项目背景与目标

### 1.1 背景
高校教务通知具有 **时效性强、信息密度高、分散在多个页面** 等特点。用户（学生/教师）常见需求包括：
- 某类事项的时间节点（选课、考试、放假、毕业等）
- 流程要求与材料清单
- 最新通知与历史通知的差异

传统检索方式依赖关键词搜索与人工阅读，成本高、容易遗漏。

### 1.2 项目目标
本项目构建一个面向“教务处通知”场景的 **RAG（Retrieval-Augmented Generation）检索增强生成问答系统**：
- 支持“纯检索预览”（不调用 LLM，快速返回相关文档摘要）
- 支持“RAG 问答”（检索 + 生成），输出答案并附带参考文档
- 支持多 LLM 提供商可切换（DeepSeek / OpenAI / Qwen / 智谱）
- 提供从爬取、清洗、分块、向量索引构建到在线服务的一体化流程

---

## 2. 系统整体架构

系统分为两条链路：

### 2.1 离线数据与索引构建（Offline）
1) 网页爬取（教务处通知页）
2) 内容抽取与清洗（HTML → Markdown + 元信息）
3) 智能分块（结构感知：标题 / 列表 / 表格）
4) 向量化（embedding：BGE）
5) 构建 FAISS 索引（IndexFlatIP）与元数据表（meta.jsonl）

### 2.2 在线问答服务（Online）
1) 接收用户问题（Web UI / API）
2) 检索：向量搜索 topk_faiss
3) 重排：reranker 选取 topk_final（可选）
4) 组装 Prompt（包含标题/日期/链接/正文）
5) 调用 LLM 生成答案
6) 返回答案 + 引用来源（references）

---

## 3. 代码结构与模块说明（按目录）

### 3.1 在线服务：`app/`

#### 入口与生命周期：`app/main.py`
- 使用 FastAPI `lifespan` 管理启动过程
- 初始化组件：
  - `RetrievalService`（延迟加载 embedding / reranker / faiss index）
  - `LLM`（通过 `make_llm` 工厂构造）
  - `QAService`（编排检索与生成）
- 将 QA service 注入到路由层：`routes.set_qa_service(qa_service)`
- 额外提供：
  - `/` 首页（Jinja 模板 `templates/index.html`）
  - `/health` 健康检查

#### API 路由：`app/api/routes.py`
- `GET /ask`：纯检索预览
  - 返回类型：`List[SearchPreviewItem]`
- `GET /chat`：RAG 问答
  - 返回类型：`ChatResponse`（answer + references）

#### 问答编排：`app/services/qa.py`
核心逻辑：
- `answer_question(question)`
  1. `docs = retrieval.retrieve(question)`
  2. 若无结果：返回固定提示
  3. `messages = PromptTemplates.format_rag_prompt(question, docs)`
  4. 调用 `llm.chat(messages)` 生成答案
  5. 对引用文档基于 `source_url` 或标题去重，生成 `DocumentReference`
  6. 返回 `ChatResponse`
- LLM 异常时：降级为“返回检索摘要”（前 3 条）以保障可用性

#### 检索与重排：`app/services/retrieval.py`
- 索引与元数据：
  - `dataset/index/faiss.index`
  - `dataset/index/meta.jsonl`
- 模型：
  - embedding：`SentenceTransformer(settings.embed_model)`（默认 `BAAI/bge-base-zh-v1.5`）
  - reranker：`FlagReranker(settings.rerank_model)`（默认 `BAAI/bge-reranker-base`）
- 算法流程：
  1. **查询扩展**：`_expand_query(query)` 通过关键词映射增强召回（比如“选课/考试/放假”等）
  2. **向量检索**：对 expanded query 计算 embedding（normalize），用 FAISS topk_faiss 搜索候选
  3. **重排（可选）**：对 (query, doc) 做 rerank 得分，截取 topk_final
  4. 若无 reranker：回退到余弦相似度（候选向量与 query 向量内积）

#### Prompt 管理：`app/core/prompts.py`
- `RAG_SYSTEM`：角色与约束
  - 强调日期/时间/地点
  - 多文档冲突时优先最新
  - 不过度推测，信息缺失要诚实说明
- `RAG_USER`：用户模板
  - 注入 `question` 和 `context`
- `format_rag_prompt()`：将 docs 格式化为：标题、发布日期、链接（若有）、全文 chunk

#### 配置：`app/core/config.py`
- 使用 `pydantic_settings.BaseSettings`，支持 `.env` 覆盖
- 关键参数：
  - `index_dir=dataset/index`
  - `topk_faiss=40`、`topk_final=12`
  - `embed_model=BAAI/bge-base-zh-v1.5`
  - `rerank_model=BAAI/bge-reranker-base`
  - LLM：provider/model/temperature/max_tokens

#### LLM 抽象：`app/models/llm.py`
- 统一接口：`ChatLLM.chat(messages) -> str`
- OpenAI Compatible 客户端：`openai.OpenAI`
- 支持提供商：
  - `openai`（`OPENAI_API_KEY`）
  - `deepseek`（`DEEPSEEK_API_KEY`，base_url = https://api.deepseek.com/v1）
  - `qwen`（`DASHSCOPE_API_KEY`）
  - `zhipu`（`ZHIPU_API_KEY`）
- 工厂：`make_llm(provider, **kwargs)`

#### 数据模型：`app/models/schemas.py`
- `SearchPreviewItem`：title / publish_date / snippet / source_url
- `ChatResponse`：query / answer / references(List[DocumentReference])

---

## 4. 离线数据处理与索引构建（tools/）

### 4.1 爬虫：`tools/crawl/`
- 入口脚本：`tools/crawl/run_crawler.py`
- 默认 start_url：`https://www.htu.edu.cn/teaching/3251/list.htm`
- 支持断点续跑与 `--force` 全量重爬
- 产物目录：`dataset/`（包含 crawl_state、database 等）

### 4.2 智能分块：`tools/chunking/chunking.py`
- `SmartChunker`：结构感知分块（Markdown）
  - 识别 heading/table/list/text
  - text 基于句子边界切分 + overlap
- 默认参数（优化后，偏向保留更多上下文）：
  - target_size=600, max_size=1200, overlap=120

### 4.3 向量索引构建：`tools/index_embedding/build_index.py`
- embedding 模型：`BAAI/bge-base-zh-v1.5`
- 索引：`faiss.IndexFlatIP(dim)`
- 输出：
  - `dataset/index/faiss.index`
  - `dataset/index/meta.jsonl`

---

## 5. 核心方法（论文/答辩可用表述）

### 5.1 为什么使用 RAG
- 通知类信息 **依赖事实细节**（时间/地点/对象/要求）
- LLM 直接生成易出现“幻觉”
- RAG 通过检索提供可追溯的上下文，实现“有据可依”的生成

### 5.2 检索：FAISS + 归一化向量（余弦相似度）
- 对 embedding 做 `normalize_embeddings=True`
- 使用 `IndexFlatIP` 的内积等价于余弦相似度

### 5.3 两阶段检索（Retrieval + Rerank）
- 第 1 阶段：向量检索扩大候选（topk_faiss=40）
- 第 2 阶段：reranker 精排输出（topk_final=12）
- 目的：兼顾 **召回** 与 **精度**

### 5.4 查询扩展（Query Expansion）
- 针对教务领域的高频口语问题做关键词增强
- 典型映射：选课/考试/放假/开学/成绩/毕业…
- 目标：提升短 query 的召回鲁棒性

### 5.5 Prompt 约束（Grounded + 最新优先）
- 强化“引用文档、关注日期、冲突取最新、缺失要说明”的行为规范
- 将文档标题/发布日期/链接直接注入上下文，利于可解释性

---

## 6. 接口与演示（PPT 可直接引用）

### 6.1 检索预览接口（不调用 LLM）
- `GET /ask?q=...`
- 返回：相关文档列表（含高亮摘要 snippet）
- 优点：速度快、成本低，适合“我想先看有哪些相关通知”

### 6.2 RAG 问答接口
- `GET /chat?q=...`
- 返回：
  - `answer`：生成答案
  - `references`：引用文档（title + source_url）

---

## 7. 工程亮点（可作为答辩加分点）

1) **延迟加载**：embedding / reranker / index 首次请求时才加载，降低启动成本。
2) **降级策略**：LLM 不可用时返回检索摘要，保证核心功能可用。
3) **多模型与多提供商适配**：LLM 抽象统一，配置切换即可更换供应商。
4) **结构化 chunking**：尽量保持表格/列表完整，减少语义破碎。
5) **接口拆分**：`/ask` 与 `/chat` 分离，便于评估检索与生成分别带来的收益。

---

## 8. 评估方案建议（论文可写，项目可补充实验）

> 仓库当前更偏工程实现，未看到专门的自动评测脚本；建议用以下方案补齐论文“实验”部分。

### 8.1 检索评估（Retrieval）
- 人工构造 Q-A/关联文档标注集（例如 50~200 条）
- 指标：Recall@K、MRR、nDCG@K
- 对比：
  - 仅 embedding 检索 vs embedding + reranker
  - 是否开启 query expansion

### 8.2 端到端回答评估（RAG Answering）
- 人工打分（Likert 1~5）：
  - 正确性（facts）
  - 是否引用到正确通知
  - 是否关注日期并给出明确结论
  - 语言清晰度
- 统计平均分 + 典型案例分析

### 8.3 性能评估（Latency）
- 分解耗时：embedding、FAISS、rerank、LLM
- 输出 P50/P95

---

## 9. PPT 建议结构（可直接照搬）

1. 标题与成员
2. 研究背景与痛点
3. 目标与功能
4. 系统总体架构（Offline + Online）
5. 数据获取与预处理（爬虫/清洗/元信息）
6. 分块策略（结构感知、参数、示例）
7. 向量化与索引（BGE + FAISS）
8. 检索与重排（两阶段、topk、query expansion）
9. Prompt 设计（关键约束）
10. LLM 适配与工程实现（provider abstraction）
11. API 设计与演示截图（/ask vs /chat）
12. 实验与评估（指标、对比、案例）
13. 结论与展望（混合检索、缓存、grounding 校验等）

---

## 10. 论文写作模板（章节建议）

1. 引言（背景、问题、贡献）
2. 相关工作（RAG、向量检索、reranking、中文 embedding 模型）
3. 数据集构建（爬虫、清洗、元数据、分块）
4. 方法（embedding、FAISS、两阶段检索、prompt）
5. 系统实现（FastAPI、模块设计、接口、容错）
6. 实验（检索指标、端到端评估、消融实验）
7. 结论与未来工作

---

## 11. 可复现实验/复现流程（简版）

1) 运行爬虫构建 `dataset/database`
2) 分块生成 `dataset/chunks/*.jsonl`
3) 构建向量索引 `dataset/index/faiss.index` + `meta.jsonl`
4) 启动 FastAPI 服务并访问 `/ask` 与 `/chat`

---

## 12. 附录：关键默认配置（来自 `app/core/config.py`）

- `topk_faiss = 40`
- `topk_final = 12`
- `embed_model = BAAI/bge-base-zh-v1.5`
- `rerank_model = BAAI/bge-reranker-base`
- `llm_provider = deepseek`
- `llm_model = deepseek-chat`

---

### 备注（答辩彩蛋点）
- 强调“通知类问答最容易答错的是 **日期/对象/地点**”，本项目的 Prompt 与输出引用都围绕这个风险设计。
- `/ask` 与 `/chat` 的分离可以用于论文消融实验：
  - 先验证检索质量，再验证生成质量。

