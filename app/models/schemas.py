# -*- coding: utf-8 -*-
"""Pydantic Data Models for API"""
from pydantic import BaseModel, Field
from typing import List, Optional


class DocumentReference(BaseModel):
    """文档引用"""
    title: str = Field(..., description="文档标题")
    source_url: Optional[str] = Field(None, description="文档来源 URL")


class SearchPreviewItem(BaseModel):
    """检索预览项"""
    title: str = Field(..., description="文档标题")
    publish_date: Optional[str] = Field(None, description="发布日期")
    snippet: str = Field(..., description="文档摘要片段")
    source_url: Optional[str] = Field(None, description="文档来源 URL")


class ChatResponse(BaseModel):
    """问答响应"""
    query: str = Field(..., description="用户问题")
    answer: str = Field(..., description="生成的答案")
    references: List[DocumentReference] = Field(default_factory=list, description="参考文档列表")


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str = Field(..., description="错误信息")


class MediaReference(BaseModel):
    """媒体引用（图片/音频）"""
    media_type: str = Field(..., description="媒体类型: image/audio")
    media_url: str = Field(..., description="媒体文件URL或路径")
    thumbnail_url: Optional[str] = Field(None, description="缩略图URL（仅图片）")
    ocr_text: Optional[str] = Field(None, description="OCR提取的文字（仅图片）")
    transcription: Optional[str] = Field(None, description="转录文本（仅音频）")
    title: Optional[str] = Field(None, description="媒体标题")


class MultimodalChatResponse(BaseModel):
    """多模态 RAG 问答响应"""
    query: str = Field(..., description="用户问题")
    answer: str = Field(..., description="生成的答案")
    references: List[DocumentReference] = Field(default_factory=list, description="参考文档列表")
    media_references: List[MediaReference] = Field(default_factory=list, description="媒体引用")
    image_ocr_text: Optional[str] = Field(None, description="查询图片的OCR文字")
    audio_transcription: Optional[str] = Field(None, description="查询音频的转录文本")


class MultimodalSearchPreviewItem(BaseModel):
    """多模态检索预览项"""
    title: str = Field(..., description="文档标题")
    publish_date: Optional[str] = Field(None, description="发布日期")
    snippet: str = Field(..., description="文档摘要片段")
    source_url: Optional[str] = Field(None, description="文档来源 URL")
    media_type: Optional[str] = Field(None, description="关联媒体类型")
    media_url: Optional[str] = Field(None, description="关联媒体URL")
    similarity_score: Optional[float] = Field(None, description="相似度分数")


