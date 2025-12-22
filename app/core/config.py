# -*- coding: utf-8 -*-
"""Application Configuration

注意：API Keys（如 DEEPSEEK_API_KEY, OPENAI_API_KEY 等）应该在 .env 文件中设置，
它们会通过 os.getenv() 在 LLM 客户端中读取，不需要在 Settings 中定义。
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类

    此类只包含应用级配置。
    API Keys 应在 .env 文件中设置，由各 LLM 客户端直接读取。
    """
    # 索引配置
    index_dir: str = "dataset/index"
    topk_faiss: int = 24
    topk_final: int = 8

    # 嵌入模型配置
    embed_model: str = "BAAI/bge-small-zh-v1.5"
    rerank_model: str | None = None  # 可选的重排模型，设为 None 禁用

    # LLM 配置
    llm_provider: str = "deepseek"  # openai/deepseek/qwen/zhipu
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048

    class Config:
        env_file = ".env"  # 可用 .env 覆盖
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略额外字段（如 API Keys）

