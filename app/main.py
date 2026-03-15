# -*- coding: utf-8 -*-
"""FastAPI Application Entry Point"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from app.core.config import Settings
from app.models.llm import make_llm
from app.services.retrieval import RetrievalService
from app.services.qa import QAService
from app.api import routes


# 配置
settings = Settings()
BASE_DIR = Path(__file__).parent.parent


# 全局服务实例
retrieval_service: Optional[RetrievalService] = None
qa_service: Optional[QAService] = None
multimodal_qa_service = None  # 多模态服务（可选）


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global retrieval_service, qa_service, multimodal_qa_service

    print("\n" + "="*60)
    print("HTU RAG System 启动中...")
    print("="*60)

    # 初始化检索服务（延迟加载）
    retrieval_service = RetrievalService(
        index_dir=settings.index_dir,
        embed_model_name=settings.embed_model,
        rerank_model_name=settings.rerank_model,
        topk_faiss=settings.topk_faiss,
        topk_final=settings.topk_final
    )

    # 初始化 LLM
    print(f"正在初始化 LLM: {settings.llm_provider} - {settings.llm_model}")
    llm = make_llm(
        provider=settings.llm_provider,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens
    )
    print("LLM 初始化完成")

    # 初始化问答服务
    qa_service = QAService(retrieval_service, llm)

    # 注入到路由模块
    routes.set_qa_service(qa_service)

    # 初始化多模态服务（如果启用）
    if settings.enable_multimodal:
        print("\n" + "="*60)
        print("多模态功能已启用，正在初始化...")
        print("="*60)

        try:
            from app.services.multimodal import MultimodalService
            from app.services.multimodal_retrieval import MultimodalRetrievalService
            from app.services.multimodal_qa import MultimodalQAService

            # 初始化多模态服务
            multimodal_service = MultimodalService(
                clip_model_name=settings.clip_model,
                whisper_model_name=settings.whisper_model,
                use_ocr=settings.use_ocr,
                media_dir=settings.media_dir
            )

            # 初始化多模态检索服务
            multimodal_retrieval = MultimodalRetrievalService(
                text_retrieval=retrieval_service,
                multimodal_service=multimodal_service,
                index_dir=settings.index_dir,
                topk_per_modality=20,
                topk_final=settings.topk_final,
                fusion_weights=settings.multimodal_fusion_weights,
                enable_media_retrieval=settings.enable_media_retrieval
            )

            # 初始化多模态问答服务
            multimodal_qa_service = MultimodalQAService(multimodal_retrieval, llm)

            # 注入到路由模块
            routes.set_multimodal_qa_service(multimodal_qa_service)

            print("多模态服务初始化完成")
            print("提示：多模态模型将在首次请求时自动加载")
        except Exception as e:
            print(f"多模态服务初始化失败: {e}")
            print("将以纯文本模式运行")

    print("\n提示：模型将在首次请求时自动加载（延迟加载）")
    print("="*60)
    print("系统启动完成！")
    print("="*60 + "\n")

    yield

    # 关闭时清理（如需要）
    print("\n系统关闭中...")


# 创建 FastAPI 应用
app = FastAPI(
    title="HTU RAG API",
    version="5.0.0",
    description="河南师范大学 RAG 智能问答系统 - 多模态版",
    lifespan=lifespan
)

# 挂载静态文件
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# 配置模板
templates_dir = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root(request: Request):
    """首页"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "version": "5.0.0",
        "llm_provider": settings.llm_provider,
        "embed_model": settings.embed_model,
        "multimodal_enabled": settings.enable_multimodal
    }


# 注册 API 路由
app.include_router(routes.router, tags=["RAG API"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

