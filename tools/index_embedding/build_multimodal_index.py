# -*- coding: utf-8 -*-
"""
构建多模态索引（图片和音频）
用于将包含图片和音频的文档构建向量索引
"""
import os
import sys
import json
import pathlib
from pathlib import Path
import numpy as np
import faiss
from tqdm import tqdm
from typing import List, Dict

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.multimodal import MultimodalService


# 目录配置
CHUNK_DIR = "../../dataset/chunks"
MEDIA_DIR = "../../dataset/media"
INDEX_DIR = "../../dataset/index"

os.makedirs(INDEX_DIR, exist_ok=True)
os.makedirs(MEDIA_DIR, exist_ok=True)


def build_image_index(
    clip_model_name: str = "openai/clip-vit-base-patch32",
    use_ocr: bool = True
):
    """
    构建图片向量索引

    Args:
        clip_model_name: CLIP 模型名称
        use_ocr: 是否使用 OCR 提取图片文字
    """
    print("="*60)
    print("开始构建图片向量索引")
    print("="*60)

    # 初始化多模态服务
    multimodal_service = MultimodalService(
        clip_model_name=clip_model_name,
        whisper_model_name="base",
        use_ocr=use_ocr,
        media_dir=MEDIA_DIR
    )

    # 收集所有图片文件
    image_dir = Path(MEDIA_DIR) / "image"
    if not image_dir.exists():
        print(f"图片目录不存在: {image_dir}")
        print("请先将图片文件放置在 dataset/media/image/ 目录下")
        return

    image_files = list(image_dir.glob("*.jpg")) + list(image_dir.glob("*.png")) + \
                  list(image_dir.glob("*.jpeg")) + list(image_dir.glob("*.webp"))

    if not image_files:
        print(f"未找到图片文件")
        return

    print(f"找到 {len(image_files)} 张图片")

    embeddings = []
    metas = []

    for img_path in tqdm(image_files, desc="提取图片特征"):
        try:
            # 提取图片特征和 OCR 文字
            img_emb, ocr_text = multimodal_service.extract_image_features(img_path)

            # 构建元数据
            meta = {
                "titles": [img_path.stem],
                "media_type": "image",
                "media_url": str(img_path.relative_to(Path(MEDIA_DIR).parent)),
                "text": ocr_text or "",
                "ocr_text": ocr_text,
                "source_url": None,
                "publish_date": None
            }

            embeddings.append(img_emb)
            metas.append(meta)

        except Exception as e:
            print(f"\n处理图片失败 {img_path}: {e}")
            continue

    if not embeddings:
        print("未成功提取任何图片特征")
        return

    # 构建 FAISS 索引
    X = np.array(embeddings, dtype="float32")
    dim = X.shape[1]

    print(f"\n构建 FAISS 索引 (维度: {dim}, 数量: {len(embeddings)})")
    index = faiss.IndexFlatIP(dim)
    index.add(X)

    # 保存索引
    index_path = f"{INDEX_DIR}/faiss_image.index"
    faiss.write_index(index, index_path)
    print(f"图片索引已保存: {index_path}")

    # 保存元数据
    meta_path = f"{INDEX_DIR}/meta_image.jsonl"
    with open(meta_path, "w", encoding="utf-8") as f:
        for m in metas:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    print(f"图片元数据已保存: {meta_path}")

    print("="*60)
    print(f"图片索引构建完成！共 {len(metas)} 张图片")
    print("="*60)


def build_audio_index(
    whisper_model_name: str = "base"
):
    """
    构建音频向量索引

    Args:
        whisper_model_name: Whisper 模型大小
    """
    print("="*60)
    print("开始构建音频向量索引")
    print("="*60)

    # 初始化多模态服务
    multimodal_service = MultimodalService(
        clip_model_name="openai/clip-vit-base-patch32",
        whisper_model_name=whisper_model_name,
        use_ocr=False,
        media_dir=MEDIA_DIR
    )

    # 收集所有音频文件
    audio_dir = Path(MEDIA_DIR) / "audio"
    if not audio_dir.exists():
        print(f"音频目录不存在: {audio_dir}")
        print("请先将音频文件放置在 dataset/media/audio/ 目录下")
        return

    audio_files = list(audio_dir.glob("*.wav")) + list(audio_dir.glob("*.mp3")) + \
                  list(audio_dir.glob("*.m4a")) + list(audio_dir.glob("*.flac"))

    if not audio_files:
        print(f"未找到音频文件")
        return

    print(f"找到 {len(audio_files)} 个音频文件")

    embeddings = []
    metas = []

    for audio_path in tqdm(audio_files, desc="提取音频特征"):
        try:
            # 提取音频特征和转录文本
            transcription, audio_emb = multimodal_service.extract_audio_features(audio_path)

            if audio_emb is None:
                print(f"\n跳过（无法提取特征）: {audio_path}")
                continue

            # 构建元数据
            meta = {
                "titles": [audio_path.stem],
                "media_type": "audio",
                "media_url": str(audio_path.relative_to(Path(MEDIA_DIR).parent)),
                "text": transcription or "",
                "transcription": transcription,
                "source_url": None,
                "publish_date": None
            }

            embeddings.append(audio_emb)
            metas.append(meta)

        except Exception as e:
            print(f"\n处理音频失败 {audio_path}: {e}")
            continue

    if not embeddings:
        print("未成功提取任何音频特征")
        return

    # 构建 FAISS 索引
    X = np.array(embeddings, dtype="float32")
    dim = X.shape[1]

    print(f"\n构建 FAISS 索引 (维度: {dim}, 数量: {len(embeddings)})")
    index = faiss.IndexFlatIP(dim)
    index.add(X)

    # 保存索引
    index_path = f"{INDEX_DIR}/faiss_audio.index"
    faiss.write_index(index, index_path)
    print(f"音频索引已保存: {index_path}")

    # 保存元数据
    meta_path = f"{INDEX_DIR}/meta_audio.jsonl"
    with open(meta_path, "w", encoding="utf-8") as f:
        for m in metas:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    print(f"音频元数据已保存: {meta_path}")

    print("="*60)
    print(f"音频索引构建完成！共 {len(metas)} 个音频")
    print("="*60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="构建多模态索引")
    parser.add_argument("--mode", type=str, choices=["image", "audio", "all"],
                       default="all", help="构建模式: image/audio/all")
    parser.add_argument("--clip-model", type=str,
                       default="openai/clip-vit-base-patch32",
                       help="CLIP 模型名称")
    parser.add_argument("--whisper-model", type=str,
                       default="base",
                       help="Whisper 模型大小 (tiny/base/small/medium/large)")
    parser.add_argument("--no-ocr", action="store_true",
                       help="禁用 OCR")

    args = parser.parse_args()

    if args.mode in ["image", "all"]:
        build_image_index(
            clip_model_name=args.clip_model,
            use_ocr=not args.no_ocr
        )

    if args.mode in ["audio", "all"]:
        build_audio_index(
            whisper_model_name=args.whisper_model
        )

    print("\n✅ 所有索引构建完成！")

