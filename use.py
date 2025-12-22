# -*- coding: utf-8 -*-
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

# 设置模板目录
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
import re, json, faiss, numpy as np
from sentence_transformers import SentenceTransformer
from FlagEmbedding import FlagReranker
from typing import List
from settings import Settings
from llm import make_llm

S = Settings()

# ===== 预加载索引/模型 =====
embed_model = SentenceTransformer(S.embed_model)
reranker = FlagReranker(S.rerank_model, use_fp16=False) if S.rerank_model else None
index = faiss.read_index(f"{S.index_dir}/faiss.index")
with open(f"{S.index_dir}/meta.jsonl", encoding="utf-8") as f:
    METAS = [json.loads(l) for l in f]

# ===== LLM：可插拔 =====
llm = make_llm(
    provider=S.llm_provider,
    model=S.llm_model,
    temperature=S.llm_temperature,
    max_tokens=S.llm_max_tokens,
)

# 创建应用并挂载静态文件
app = FastAPI(
    title="HTU RAG API (Modular LLM)",
    version="3.0",
    description="河南师范大学RAG系统API服务"
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

def highlight(text: str, keywords: List[str]) -> str:
    for kw in keywords:
        if not kw.strip():
            continue
        text = re.sub(re.escape(kw), lambda m: f"**{m.group(0)}**", text, flags=re.I)
    return text

def retrieve(query: str):
    qv = embed_model.encode([query], normalize_embeddings=True).astype("float32")
    D, I = index.search(qv, S.topk_faiss)
    cands = [METAS[i] for i in I[0]]
    
    if reranker is not None:
        # 如果有重排模型，使用重排模型对结果进行重排
        pairs = [(query, " ".join(c["titles"]) + " " + c["text"]) for c in cands]
        scores = reranker.compute_score(pairs)
        top_idx = np.argsort(scores)[::-1][:S.topk_final]
    else:
        # 否则直接使用嵌入向量的余弦相似度
        cand_vecs = [embed_model.encode(" ".join(c["titles"]) + " " + c["text"], 
                     normalize_embeddings=True) for c in cands]
        sims = np.array(cand_vecs) @ qv.T
        top_idx = np.argsort(sims.ravel())[::-1][:S.topk_final]
        
    return [cands[i] for i in top_idx]

def build_prompt(query: str, docs: List[dict]) -> List[dict]:
    """返回 OpenAI 格式 messages"""
    context = ""
    for i, d in enumerate(docs, 1):
        context += f"[文档{i}] {d['titles'][0]}（{d.get('publish_date','未知日期')}）\n{d['text']}\n\n"
    user = f"""你是一位熟悉河南师范大学教务与校园事务的助手。使用以上下文来回答用户的问题。如果你不知道答案，就说你“未在学校文件中找到明确规定”。总是使用中文回答。
        问题: {query}
        可参考的上下文：
        ···
        {context}
        ···
        如果给定的上下文无法让你做出回答，请回答数据库中没有这个内容，你不知道。
        有用的回答:
"""
    return [
        {"role": "system", "content": "你是河南师范大学教务处智能助手。"},
        {"role": "user", "content": user}
    ]

@app.get("/ask", response_class=JSONResponse)
async def ask(q: str = Query(..., description="纯检索预览")):  # 添加 async 关键字
    docs = retrieve(q)
    kws = re.split(r"[，。；,.!?、\s]", q)
    return [{
        "title": d["titles"][0],
        "publish_date": d.get("publish_date"),
        "snippet": highlight(d["text"], kws)[:200],
        "source_url": d.get("source_url")
    } for d in docs]

@app.get("/chat", response_class=JSONResponse)
async def chat(q: str = Query(..., description="RAG 生成回答")):  # 添加 async 关键字
    docs = retrieve(q)
    if not docs:
        return {"answer": "未找到相关内容。"}
    messages = build_prompt(q, docs)
    try:
        answer = llm.chat(messages)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    # 使用字典去重，以 source_url 或 titles[0] 作为唯一标识
    unique_refs = {}
    for d in docs:
        key = d.get("source_url") or d["titles"][0]  # 使用 URL 或标题作为唯一标识
        if key not in unique_refs:
            unique_refs[key] = {
                "title": d["titles"][0],
                "source_url": d.get("source_url")
            }
    
    return {
        "query": q, 
        "answer": answer, 
        "references": list(unique_refs.values())  # 转换为列表返回
    }

# 启动：
# uvicorn use:app --reload --port 8000


