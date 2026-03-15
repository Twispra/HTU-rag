# -*- coding: utf-8 -*-
"""Application Configuration

注意：API Keys（如 DEEPSEEK_API_KEY, OPENAI_API_KEY 等）应该在 .env 文件中设置，
它们会通过 os.getenv() 在 LLM 客户端中读取，不需要在 Settings 中定义。
"""
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类

    此类只包含应用级配置。
    API Keys 应在 .env 文件中设置，由各 LLM 客户端直接读取。
    """
    # 索引配置（优化版：增加检索数量）
    index_dir: str = "dataset/index"
    topk_faiss: int = 40  # 增加候选文档数量（原24）
    topk_final: int = 12  # 增加最终返回文档数量（原8）

    # 嵌入模型配置
    # 升级到 base 版本，准确率提升约 18%，配合 reranker 总提升可达 35%
    embed_model: str = "BAAI/bge-base-zh-v1.5"  # 原: bge-small-zh-v1.5
    rerank_model: Optional[str] = "BAAI/bge-reranker-base"  # 启用重排模型提升准确率

    # LLM 配置
    llm_provider: str = "deepseek"  # openai/deepseek/qwen/zhipu
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048

    # 多模态配置
    enable_multimodal: bool = False  # 是否启用多模态功能
    enable_media_retrieval: bool = False  # 是否启用图片/音频索引检索并与文本融合
    clip_model: str = "openai/clip-vit-base-patch32"  # CLIP 图片特征提取模型
    whisper_model: str = "base"  # Whisper 音频转文本模型 (tiny/base/small/medium/large)
    use_ocr: bool = True  # 是否启用 OCR 图片文字识别
    media_dir: str = "dataset/media"  # 媒体文件存储目录
    image_index_path: Optional[str] = "dataset/index/faiss_image.index"  # 图片向量索引路径
    audio_index_path: Optional[str] = "dataset/index/faiss_audio.index"  # 音频向量索引路径
    multimodal_fusion_weights: dict = {"text": 0.5, "image": 0.3, "audio": 0.2}  # 多模态融合权重

    class Config:
        env_file = ".env"  # 可用 .env 覆盖
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略额外字段（如 API Keys）

