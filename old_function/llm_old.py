# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import List, Dict, Any, Optional
import os
from openai import OpenAI

Message = Dict[str, str]  # {"role": "system|user|assistant", "content": "..."}

class ChatLLM:
    """统一接口"""
    def chat(self, messages: List[Message], **kwargs) -> str:
        raise NotImplementedError


class ChatDeepSeek(ChatLLM):
    """DeepSeek（OpenAI 兼容）"""
    def __init__(self, model: str = "deepseek-chat",
                 api_key: Optional[str] = None,
                 temperature: float = 0.7, max_tokens: int = 2048):
        self.client = OpenAI(api_key=api_key or os.getenv("DEEPSEEK_API_KEY"),
                             base_url="https://api.deepseek.com/v1")
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
    def __init__(self, model: str = "qwen-turbo",
                 api_key: Optional[str] = None,
                 temperature: float = 0.3, max_tokens: int = 1024):
        self.client = OpenAI(api_key=api_key or os.getenv("DASHSCOPE_API_KEY"),
                             base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
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
    def __init__(self, model: str = "glm-4",
                 api_key: Optional[str] = None,
                 temperature: float = 0.3, max_tokens: int = 1024):
        self.client = OpenAI(api_key=api_key or os.getenv("ZHIPU_API_KEY"),
                             base_url="https://open.bigmodel.cn/api/paas/v4")
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
    """简单工厂：provider in {openai, deepseek, qwen, zhipu}"""
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
