# -*- coding: utf-8 -*-
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 索引
    index_dir: str = "dataset/index"
    topk_faiss: int = 24
    topk_final: int = 8

    # 嵌入/重排
    embed_model: str = "BAAI/bge-small-zh-v1.5"
    rerank_model: str | None = None  # 可选的重排模型，设为 None 禁用

    # LLM
    llm_provider: str = "deepseek"  # openai/deepseek/qwen/zhipu
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048

    class Config:
        env_file = ".env"  # 可用 .env 覆盖
