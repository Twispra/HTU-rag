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
                 fusion_weights: Optional[Dict[str, float]] = None,
                 enable_media_retrieval: bool = False):
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
        self.enable_media_retrieval = enable_media_retrieval

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
                           audio: Optional[bytes] = None,
                           preprocessed: Optional[Dict] = None) -> List[Dict]:
        """
        Multimodal retrieval (text + image + audio fusion).

        Args:
            text: Text query
            image: Image bytes
            audio: Audio bytes
            preprocessed: Optional preprocessed result to avoid duplicate work

        Returns:
            Fused retrieval results
        """
        results_by_modality: Dict[str, List[Dict]] = {}

        # 1) Preprocess multimodal inputs
        multimodal_result = preprocessed or self.multimodal.process_multimodal_query(text, image, audio)
        combined_text = multimodal_result.get("combined_text", "")

        # 2) Text retrieval (primary for campus QA)
        if combined_text:
            try:
                text_docs = self.text_retrieval.retrieve(combined_text)
                results_by_modality["text"] = [
                    {"doc": doc, "score": 1.0 / (i + 1), "modality": "text"}
                    for i, doc in enumerate(text_docs[:self.topk_per_modality])
                ]
            except Exception as e:
                print(f"Text retrieval failed: {e}")
                results_by_modality["text"] = []

        # 3) Optional media retrieval
        if self.enable_media_retrieval:
            if image and self.image_index and self.image_metas:
                try:
                    image_emb = multimodal_result.get("image_embedding")
                    if image_emb is not None:
                        image_emb = image_emb.reshape(1, -1).astype("float32")
                        D, I = self.image_index.search(image_emb, self.topk_per_modality)
                        results_by_modality["image"] = [
                            {"doc": self.image_metas[i], "score": float(D[0][idx]), "modality": "image"}
                            for idx, i in enumerate(I[0]) if i < len(self.image_metas)
                        ]
                except Exception as e:
                    print(f"Image retrieval failed: {e}")
                    results_by_modality["image"] = []

            if audio and self.audio_index and self.audio_metas:
                try:
                    audio_emb = multimodal_result.get("audio_embedding")
                    if audio_emb is not None:
                        audio_emb = audio_emb.reshape(1, -1).astype("float32")
                        D, I = self.audio_index.search(audio_emb, self.topk_per_modality)
                        results_by_modality["audio"] = [
                            {"doc": self.audio_metas[i], "score": float(D[0][idx]), "modality": "audio"}
                            for idx, i in enumerate(I[0]) if i < len(self.audio_metas)
                        ]
                except Exception as e:
                    print(f"Audio retrieval failed: {e}")
                    results_by_modality["audio"] = []

        # 4) Fuse results
        fused_results = self._fuse_results(results_by_modality)

        # 5) Return Top-K with scores
        packed_results: List[Dict] = []
        for item in fused_results[:self.topk_final]:
            doc = dict(item["doc"])
            doc["score"] = item["total_score"]
            doc["modalities"] = item["modalities"]
            packed_results.append(doc)

        return packed_results

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

            results: List[Dict] = []
            for idx, i in enumerate(I[0]):
                if i >= len(self.image_metas):
                    continue
                doc = dict(self.image_metas[i])
                doc["score"] = float(D[0][idx])
                results.append(doc)
            return results
        except Exception as e:
            print(f"图片相似度检索失败: {e}")
            return []

