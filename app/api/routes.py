# -*- coding: utf-8 -*-
"""API Routes"""
from fastapi import APIRouter, Query, HTTPException, File, UploadFile, Form
from typing import Any, Dict, List, cast, Optional

from app.models.schemas import (
    ChatResponse, SearchPreviewItem,
    MultimodalChatResponse, MultimodalSearchPreviewItem
)
from app.services.qa import QAService


router = APIRouter()


# 全局 QA 服务实例（由 main.py 注入）
_qa_service: Optional[QAService] = None
_multimodal_qa_service = None  # 多模态 QA 服务（可选）


def set_qa_service(qa_service: QAService) -> None:
    """设置全局 QA 服务实例（由 main.py 调用）"""
    global _qa_service
    _qa_service = qa_service


def set_multimodal_qa_service(multimodal_qa_service) -> None:
    """设置全局多模态 QA 服务实例（由 main.py 调用）"""
    global _multimodal_qa_service
    _multimodal_qa_service = multimodal_qa_service


def get_qa_service() -> QAService:
    """获取 QA 服务实例"""
    if _qa_service is None:
        raise RuntimeError("QA Service not initialized")
    qa_service: QAService = _qa_service
    return qa_service


def get_multimodal_qa_service():
    """获取多模态 QA 服务实例"""
    if _multimodal_qa_service is None:
        raise RuntimeError("Multimodal QA Service not initialized or not enabled")
    return _multimodal_qa_service

def _has_multimodal_service() -> bool:
    """???????????"""
    return _multimodal_qa_service is not None


async def _read_audio_upload(audio: Optional[UploadFile]) -> Optional[Dict[str, Any]]:
    """Read an uploaded audio file while preserving format hints for Whisper."""
    if audio is None:
        return None
    audio_bytes = await audio.read()
    print(
        "[ASR] upload received: "
        f"filename={audio.filename!r}, content_type={audio.content_type!r}, bytes={len(audio_bytes)}"
    )
    return {
        "bytes": audio_bytes,
        "filename": audio.filename or "",
        "content_type": audio.content_type or "",
    }



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


# ============ ????? ============

@router.post(
    "/ask-multimodal",
    response_model=List[MultimodalSearchPreviewItem],
    summary="???????",
    description="????+??+??????????"
)
async def ask_multimodal(
    text: Optional[str] = Form(None, description="????"),
    image: Optional[UploadFile] = File(None, description="????"),
    audio: Optional[UploadFile] = File(None, description="????")
):
    """
    ?????????

    - **text**: ????????
    - **image**: ????????
    - **audio**: ????????
    - **??**: ??????????????
    """
    try:
        if not text and image is None and audio is None:
            raise HTTPException(status_code=400, detail="??????????/??")

        # ??????????????
        if _has_multimodal_service():
            multimodal_qa = get_multimodal_qa_service()
            image_bytes = await image.read() if image else None
            audio_payload = await _read_audio_upload(audio)
            return multimodal_qa.preview_search_multimodal(text, image_bytes, audio_payload)

        # ????????????????????
        if text:
            qa = cast(QAService, get_qa_service())
            results = qa.preview_search(text)
            return [
                MultimodalSearchPreviewItem(
                    title=item.title,
                    publish_date=item.publish_date,
                    snippet=item.snippet,
                    source_url=item.source_url,
                    media_type=None,
                    media_url=None,
                    similarity_score=None
                )
                for item in results
            ]

        raise HTTPException(
            status_code=400,
            detail="????????????????/?????????????????"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/chat-multimodal",
    response_model=MultimodalChatResponse,
    summary="??? RAG ??",
    description="????+??+??????????"
)
async def chat_multimodal(
    text: Optional[str] = Form(None, description="????"),
    image: Optional[UploadFile] = File(None, description="????"),
    audio: Optional[UploadFile] = File(None, description="????")
):
    """
    ??? RAG ????

    - **text**: ????????
    - **image**: ????????
    - **audio**: ????????
    - **??**: ????? + ???? + ????
    """
    try:
        if not text and image is None and audio is None:
            raise HTTPException(status_code=400, detail="??????????/??")

        # ??????????????
        if _has_multimodal_service():
            multimodal_qa = get_multimodal_qa_service()
            image_bytes = await image.read() if image else None
            audio_payload = await _read_audio_upload(audio)
            return multimodal_qa.answer_question_multimodal(text, image_bytes, audio_payload)

        # ????????????????????
        if text:
            qa = cast(QAService, get_qa_service())
            result = qa.answer_question(text)
            note = ""
            if image is not None or audio is not None:
                note = "\n\n??????????????????????????/???????"
            return MultimodalChatResponse(
                query=result.query,
                answer=result.answer + note,
                references=result.references,
                media_references=[],
                image_ocr_text=None,
                audio_transcription=None
            )

        raise HTTPException(
            status_code=400,
            detail="????????????????/?????????????????"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/search-images",
    response_model=List[MultimodalSearchPreviewItem],
    summary="图片搜索",
    description="基于文本描述搜索相似图片（CLIP跨模态检索）"
)
async def search_images(
    q: str = Query(..., description="文本描述", min_length=1),
    topk: int = Query(12, description="返回结果数量", ge=1, le=50)
):
    """
    图片搜索接口（使用 CLIP 跨模态检索）

    - **q**: 文本描述
    - **topk**: 返回结果数量
    - **返回**: 相似图片列表
    """
    try:
        multimodal_qa = get_multimodal_qa_service()
        return multimodal_qa.search_images_by_text(q, topk)
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

