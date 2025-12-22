# -*- coding: utf-8 -*-
"""LLM Tests"""
import pytest
from app.models.llm import ChatDeepSeek, make_llm


def test_make_llm_deepseek():
    """测试 LLM 工厂函数"""
    llm = make_llm("deepseek", model="deepseek-chat")
    assert isinstance(llm, ChatDeepSeek)
    assert llm.model == "deepseek-chat"


def test_make_llm_invalid_provider():
    """测试无效的 provider"""
    with pytest.raises(ValueError):
        make_llm("invalid_provider")


def test_chat_message_format():
    """测试消息格式"""
    llm = make_llm("deepseek")
    messages = [
        {"role": "system", "content": "你是一个助手"},
        {"role": "user", "content": "你好"}
    ]
    
    # 注意：这个测试需要有效的 API Key
    # 在 CI 环境中可能需要 mock
    # response = llm.chat(messages)
    # assert isinstance(response, str)
    # assert len(response) > 0
    pass  # 跳过实际调用

