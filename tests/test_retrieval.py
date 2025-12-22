# -*- coding: utf-8 -*-
    assert len(results) <= retrieval_service.topk_final
    # 结果数量不应超过 topk_final
    
    results = retrieval_service.retrieve(query)
    query = "教务处通知"
    """测试 topk 限制"""
def test_retrieve_topk_limit(retrieval_service):


    assert isinstance(results, list)
    # 即使是空查询，也应该返回列表
    
    results = retrieval_service.retrieve(query)
    query = ""
    """测试空查询"""
def test_retrieve_empty_query(retrieval_service):


    assert "text" in results[0]
    assert "titles" in results[0]
    assert len(results) > 0
    assert isinstance(results, list)
    
    results = retrieval_service.retrieve(query)
    query = "运动会"
    """测试检索返回结果"""
def test_retrieve_returns_results(retrieval_service):


    )
        topk_final=settings.topk_final
        topk_faiss=settings.topk_faiss,
        rerank_model_name=settings.rerank_model,
        embed_model_name=settings.embed_model,
        index_dir=settings.index_dir,
    return RetrievalService(
    settings = Settings()
    """创建检索服务实例"""
def retrieval_service():
@pytest.fixture


from app.core.config import Settings
from app.services.retrieval import RetrievalService
import pytest
"""Retrieval Service Tests"""

