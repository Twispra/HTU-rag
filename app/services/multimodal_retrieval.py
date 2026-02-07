# -*- coding: utf-8 -*-
"""Multimodal Retrieval Service (支持图片和音频检索)"""
import faiss
import numpy as np
from typing import List, Dict, Optional, Tuple
import json
from pathlib import Path
from app.services.retrieval import RetrievalService
from app.services.multimodal import MultimodalService


class MultimodalRetrievalService:
    """多模态检索服务（文本 + 图片 + 音频）"""

    def __init__(self,
                 text_retrieval: RetrievalService,
                 multimodal_service: MultimodalService,
                 index_dir: str,
                 topk_per_modality: int = 20,
                 topk_final: int = 12,
                 fusion_weights: Optional[Dict[str, float]] = None):
        """
        初始化多模态检索服务

        Args:
            text_retrieval: 文本检索服务实例
            multimodal_service: 多模态处理服务实例
            index_dir: 索引文件目录
            topk_per_modality: 每种模态检索的 Top-K
            topk_final: 最终返回 Top-K
            fusion_weights: 模态融合权重 {"text": 0.5, "image": 0.3, "audio": 0.2}
        """
        self.text_retrieval = text_retrieval
        self.multimodal = multimodal_service
        self.index_dir = Path(index_dir)
        self.topk_per_modality = topk_per_modality
        self.topk_final = topk_final
        self.fusion_weights = fusion_weights or {"text": 0.5, "image": 0.3, "audio": 0.2}

        # 延迟加载的私有属性
        self._image_index: Optional[faiss.Index] = None
        self._image_metas: Optional[List[Dict]] = None
        self._audio_index: Optional[faiss.Index] = None
        self._audio_metas: Optional[List[Dict]] = None

    @property
    def image_index(self) -> Optional[faiss.Index]:
        """延迟加载图片 FAISS 索引"""
        if self._image_index is None:
            index_path = self.index_dir / "faiss_image.index"
            if index_path.exists():
                print(f"正在加载图片索引: {index_path}")
                self._image_index = faiss.read_index(str(index_path))
                print(f"图片索引加载完成 (共 {self._image_index.ntotal} 条向量)")
            else:
                print(f"图片索引不存在: {index_path}")
        return self._image_index

    @property
    def image_metas(self) -> Optional[List[Dict]]:
        """延迟加载图片元数据"""
        if self._image_metas is None:
            meta_path = self.index_dir / "meta_image.jsonl"
            if meta_path.exists():
                print(f"正在加载图片元数据: {meta_path}")
                with open(meta_path, encoding="utf-8") as f:
                    self._image_metas = [json.loads(line) for line in f]
                print(f"图片元数据加载完成 (共 {len(self._image_metas)} 条)")
            else:
                print(f"图片元数据不存在: {meta_path}")
        return self._image_metas

    @property
    def audio_index(self) -> Optional[faiss.Index]:
        """延迟加载音频 FAISS 索引"""
        if self._audio_index is None:
            index_path = self.index_dir / "faiss_audio.index"
            if index_path.exists():
                print(f"正在加载音频索引: {index_path}")
                self._audio_index = faiss.read_index(str(index_path))
                print(f"音频索引加载完成 (共 {self._audio_index.ntotal} 条向量)")
            else:
                print(f"音频索引不存在: {index_path}")
        return self._audio_index

    @property
    def audio_metas(self) -> Optional[List[Dict]]:
        """延迟加载音频元数据"""
        if self._audio_metas is None:
            meta_path = self.index_dir / "meta_audio.jsonl"
            if meta_path.exists():
                print(f"正在加载音频元数据: {meta_path}")
                with open(meta_path, encoding="utf-8") as f:
                    self._audio_metas = [json.loads(line) for line in f]
                print(f"音频元数据加载完成 (共 {len(self._audio_metas)} 条)")
            else:
                print(f"音频元数据不存在: {meta_path}")
        return self._audio_metas

    def retrieve_multimodal(self,
                           text: Optional[str] = None,
                           image: Optional[bytes] = None,
                           audio: Optional[bytes] = None) -> List[Dict]:
        """
        多模态检索（文本 + 图片 + 音频融合）

        Args:
            text: 文本查询
            image: 图片字节数据
            audio: 音频字节数据

        Returns:
            融合后的检索结果列表
        """
        results_by_modality = {}

        # 1. 处理多模态输入，提取特征
        multimodal_result = self.multimodal.process_multimodal_query(text, image, audio)

        # 构建完整的文本查询（包含 OCR 和音频转录）
        combined_text = multimodal_result["combined_text"]

        # 2. 文本检索
        if combined_text:
            try:
                text_docs = self.text_retrieval.retrieve(combined_text)
                results_by_modality["text"] = [
                    {"doc": doc, "score": 1.0 / (i + 1), "modality": "text"}
                    for i, doc in enumerate(text_docs[:self.topk_per_modality])
                ]
            except Exception as e:
                print(f"文本检索失败: {e}")
                results_by_modality["text"] = []

        # 3. 图片检索（如果有图片输入且索引存在）
        if image and self.image_index and self.image_metas:
            try:
                image_emb = multimodal_result["image_embedding"]
                if image_emb is not None:
                    # 搜索图片索引
                    image_emb = image_emb.reshape(1, -1).astype("float32")
                    D, I = self.image_index.search(image_emb, self.topk_per_modality)

                    results_by_modality["image"] = [
                        {"doc": self.image_metas[i], "score": float(D[0][idx]), "modality": "image"}
                        for idx, i in enumerate(I[0]) if i < len(self.image_metas)
                    ]
            except Exception as e:
                print(f"图片检索失败: {e}")
                results_by_modality["image"] = []

        # 4. 音频检索（如果有音频输入且索引存在）
        if audio and self.audio_index and self.audio_metas:
            try:
                audio_emb = multimodal_result["audio_embedding"]
                if audio_emb is not None:
                    # 搜索音频索引
                    audio_emb = audio_emb.reshape(1, -1).astype("float32")
                    D, I = self.audio_index.search(audio_emb, self.topk_per_modality)

                    results_by_modality["audio"] = [
                        {"doc": self.audio_metas[i], "score": float(D[0][idx]), "modality": "audio"}
                        for idx, i in enumerate(I[0]) if i < len(self.audio_metas)
                    ]
            except Exception as e:
                print(f"音频检索失败: {e}")
                results_by_modality["audio"] = []

        # 5. 融合多模态检索结果
        fused_results = self._fuse_results(results_by_modality)

        # 6. 返回 Top-K
        return [item["doc"] for item in fused_results[:self.topk_final]]

    def _fuse_results(self, results_by_modality: Dict[str, List[Dict]]) -> List[Dict]:
        """
        融合多模态检索结果（加权融合）

        Args:
            results_by_modality: {"text": [...], "image": [...], "audio": [...]}

        Returns:
            融合后的结果列表（按分数排序）
        """
        # 收集所有文档及其分数
        doc_scores = {}

        for modality, results in results_by_modality.items():
            weight = self.fusion_weights.get(modality, 0.0)

            for item in results:
                doc = item["doc"]
                score = item["score"]

                # 使用文档的唯一标识（URL 或标题）作为 key
                doc_key = doc.get("source_url") or doc.get("titles", [""])[0]

                if doc_key not in doc_scores:
                    doc_scores[doc_key] = {"doc": doc, "total_score": 0.0, "modalities": []}

                doc_scores[doc_key]["total_score"] += score * weight
                doc_scores[doc_key]["modalities"].append(modality)

        # 按分数排序
        sorted_docs = sorted(doc_scores.values(), key=lambda x: x["total_score"], reverse=True)

        return sorted_docs

    def retrieve_by_image_similarity(self, text_query: str, topk: int = 12) -> List[Dict]:
        """
        基于文本查询检索相似图片（使用 CLIP 跨模态检索）

        Args:
            text_query: 文本查询
            topk: 返回 Top-K

        Returns:
            图片文档列表
        """
        if not self.image_index or not self.image_metas:
            return []

        try:
            # 使用 CLIP 将文本编码到图片向量空间
            text_emb = self.multimodal.encode_text_for_image_search(text_query)
            text_emb = text_emb.reshape(1, -1).astype("float32")

            # 搜索
            D, I = self.image_index.search(text_emb, topk)

            results = [self.image_metas[i] for i in I[0] if i < len(self.image_metas)]
            return results
        except Exception as e:
            print(f"图片相似度检索失败: {e}")
            return []

