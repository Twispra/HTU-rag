# -*- coding: utf-8 -*-
"""API Routes"""
from fastapi import APIRouter, Query, HTTPException
from typing import List, cast

from app.models.schemas import ChatResponse, SearchPreviewItem
from app.services.qa import QAService


router = APIRouter()


# 全局 QA 服务实例（由 main.py 注入）
_qa_service: QAService | None = None


def set_qa_service(qa_service: QAService) -> None:
    """设置全局 QA 服务实例（由 main.py 调用）"""
    global _qa_service
    _qa_service = qa_service


def get_qa_service() -> QAService:
    """获取 QA 服务实例"""
    if _qa_service is None:
        raise RuntimeError("QA Service not initialized")
    qa_service: QAService = _qa_service
    return qa_service


@router.get(
    "/ask",
    response_model=List[SearchPreviewItem],
    summary="检索预览",
    description="纯检索，不调用 LLM，快速返回相关文档摘要"
)
async def ask(q: str = Query(..., description="查询问题", min_length=1)):
    """
    纯检索预览接口

    - **q**: 用户问题
    - **返回**: 相关文档列表（包含高亮摘要）
    """
    try:
        qa = cast(QAService, get_qa_service())
        return qa.preview_search(q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/chat",
    response_model=ChatResponse,
    summary="RAG 问答",
    description="基于检索增强生成的智能问答"
)
async def chat(q: str = Query(..., description="查询问题", min_length=1)):
    """
    RAG 问答接口

    - **q**: 用户问题
    - **返回**: 生成的答案 + 参考文档
    """
    try:
        qa = cast(QAService, get_qa_service())
        return qa.answer_question(q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
