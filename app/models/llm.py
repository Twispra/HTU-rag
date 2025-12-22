# -*- coding: utf-8 -*-
"""LLM Client Implementations"""
from __future__ import annotations
from typing import List, Dict, Optional
import os
from openai import OpenAI

Message = Dict[str, str]  # {"role": "system|user|assistant", "content": "..."}


class ChatLLM:
    """LLM 统一接口基类"""

    def chat(self, messages: List[Message], **kwargs) -> str:
        """
        发送对话消息并获取回复

        Args:
            messages: OpenAI 格式的消息列表
            **kwargs: 其他参数（如 temperature, max_tokens）

        Returns:
            LLM 的回复内容
        """
        raise NotImplementedError


class ChatOpenAI(ChatLLM):
    """OpenAI 官方 API"""

    def __init__(self,
                 model: str = "gpt-3.5-turbo",
                 api_key: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: int = 2048):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def chat(self, messages: List[Message], **kwargs) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        return resp.choices[0].message.content


class ChatDeepSeek(ChatLLM):
    """DeepSeek（OpenAI 兼容）"""

    def __init__(self,
                 model: str = "deepseek-chat",
                 api_key: Optional[str] = None,
                 temperature: float = 0.7,
                 max_tokens: int = 2048):
        self.client = OpenAI(
            api_key=api_key or os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1"
        )
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def chat(self, messages: List[Message], **kwargs) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        return resp.choices[0].message.content


class ChatQwen(ChatLLM):
    """通义千问（OpenAI 兼容模式）"""

    def __init__(self,
                 model: str = "qwen-turbo",
                 api_key: Optional[str] = None,
                 temperature: float = 0.3,
                 max_tokens: int = 1024):
        self.client = OpenAI(
            api_key=api_key or os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def chat(self, messages: List[Message], **kwargs) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        return resp.choices[0].message.content


class ChatZhipu(ChatLLM):
    """智谱 GLM（OpenAI 兼容）"""

    def __init__(self,
                 model: str = "glm-4",
                 api_key: Optional[str] = None,
                 temperature: float = 0.3,
                 max_tokens: int = 1024):
        self.client = OpenAI(
            api_key=api_key or os.getenv("ZHIPU_API_KEY"),
            base_url="https://open.bigmodel.cn/api/paas/v4"
        )
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def chat(self, messages: List[Message], **kwargs) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        return resp.choices[0].message.content


def make_llm(provider: str, **kwargs) -> ChatLLM:
    """
    LLM 工厂函数

    Args:
        provider: LLM 提供商 (openai, deepseek, qwen, zhipu)
        **kwargs: 传递给具体 LLM 类的参数

    Returns:
        ChatLLM 实例

    Raises:
        ValueError: 未知的 provider
    """
    provider = provider.lower()
    if provider == "openai":
        return ChatOpenAI(**kwargs)
    if provider == "deepseek":
        return ChatDeepSeek(**kwargs)
    if provider == "qwen":
        return ChatQwen(**kwargs)
    if provider == "zhipu":
        return ChatZhipu(**kwargs)
    raise ValueError(f"Unknown provider: {provider}")

