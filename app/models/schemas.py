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

