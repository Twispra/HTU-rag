# -*- coding: utf-8 -*-
"""Document Retrieval Service"""
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from FlagEmbedding import FlagReranker
from typing import List, Dict, Optional
import json
from pathlib import Path


class RetrievalService:
    """文档检索服务（支持延迟加载）"""

    def __init__(self,
                 index_dir: str,
                 embed_model_name: str,
                 rerank_model_name: Optional[str] = None,
                 topk_faiss: int = 40,
                 topk_final: int = 12):
        """
        初始化检索服务（优化版：增加检索数量）

        Args:
            index_dir: 索引文件目录
            embed_model_name: 嵌入模型名称
            rerank_model_name: 重排模型名称（可选）
            topk_faiss: FAISS 检索 Top-K（增加到40以获取更多候选）
            topk_final: 最终返回 Top-K（增加到12以提供更丰富的上下文）
        """
        self.index_dir = Path(index_dir)
        self.embed_model_name = embed_model_name
        self.rerank_model_name = rerank_model_name
        self.topk_faiss = topk_faiss
        self.topk_final = topk_final

        # 延迟加载的私有属性
        self._embed_model: Optional[SentenceTransformer] = None
        self._reranker: Optional[FlagReranker] = None
        self._index: Optional[faiss.Index] = None
        self._metas: Optional[List[Dict]] = None

    @property
    def embed_model(self) -> SentenceTransformer:
        """延迟加载嵌入模型"""
        if self._embed_model is None:
            print(f"正在加载嵌入模型: {self.embed_model_name}")
            self._embed_model = SentenceTransformer(self.embed_model_name)
            print("嵌入模型加载完成")
        return self._embed_model

    @property
    def reranker(self) -> Optional[FlagReranker]:
        """延迟加载重排模型"""
        if self._reranker is None and self.rerank_model_name:
            print(f"正在加载重排模型: {self.rerank_model_name}")
            self._reranker = FlagReranker(self.rerank_model_name, use_fp16=False)
            print("重排模型加载完成")
        return self._reranker

    @property
    def index(self) -> faiss.Index:
        """延迟加载 FAISS 索引"""
        if self._index is None:
            index_path = self.index_dir / "faiss.index"
            if not index_path.exists():
                raise FileNotFoundError(f"索引文件不存在: {index_path}")
            print(f"正在加载 FAISS 索引: {index_path}")
            self._index = faiss.read_index(str(index_path))
            print(f"FAISS 索引加载完成 (共 {self._index.ntotal} 条向量)")
        return self._index

    @property
    def metas(self) -> List[Dict]:
        """延迟加载元数据"""
        if self._metas is None:
            meta_path = self.index_dir / "meta.jsonl"
            if not meta_path.exists():
                raise FileNotFoundError(f"元数据文件不存在: {meta_path}")
            print(f"正在加载元数据: {meta_path}")
            with open(meta_path, encoding="utf-8") as f:
                self._metas = [json.loads(line) for line in f]
            print(f"元数据加载完成 (共 {len(self._metas)} 条)")
        return self._metas

    def retrieve(self, query: str) -> List[Dict]:
        """
        检索相关文档（优化版：添加查询扩展）

        Args:
            query: 查询文本

        Returns:
            相关文档列表（已排序）
        """
        # 查询扩展：将短查询扩展为更完整的表述
        expanded_query = self._expand_query(query)
        print(f"原始查询: {query}")
        if expanded_query != query:
            print(f"扩展查询: {expanded_query}")

        # 向量化查询（使用扩展后的查询）
        qv = self.embed_model.encode([expanded_query], normalize_embeddings=True).astype("float32")

        # FAISS 检索候选
        D, I = self.index.search(qv, self.topk_faiss)
        cands = [self.metas[i] for i in I[0] if i < len(self.metas)]

        if not cands:
            return []

        # 重排（如果启用）
        if self.reranker:
            pairs = [
                (query, " ".join(c["titles"]) + " " + c["text"])
                for c in cands
            ]
            scores = self.reranker.compute_score(pairs)
            # 处理单个分数的情况
            if not isinstance(scores, list):
                scores = [scores]
            top_idx = np.argsort(scores)[::-1][:self.topk_final]
        else:
            # 使用余弦相似度
            cand_vecs = np.array([
                self.embed_model.encode(
                    " ".join(c["titles"]) + " " + c["text"],
                    normalize_embeddings=True
                )
                for c in cands
            ])
            sims = cand_vecs @ qv.T
            top_idx = np.argsort(sims.ravel())[::-1][:self.topk_final]

        return [cands[i] for i in top_idx]

    def _expand_query(self, query: str) -> str:
        """
        扩展查询：将短查询扩展为更完整的表述

        Args:
            query: 原始查询

        Returns:
            扩展后的查询
        """
        # 关键词映射：将口语化问题转换为正式术语
        expansions = {
            "运动会": "运动会 体育活动 校运动会 停课安排",
            "选课": "选课 课程选择 网上选课 选课时间",
            "考试": "考试 期末考试 考试安排 考试时间",
            "放假": "放假 假期 假期安排 寒假 暑假",
            "开学": "开学 开学时间 返校 报到",
            "补考": "补考 重修 缓考",
            "成绩": "成绩 成绩查询 绩点 分数",
            "毕业": "毕业 学位 毕业设计 论文答辩",
            "转专业": "转专业 专业调整",
            "奖学金": "奖学金 评定 评选",
        }

        expanded = query
        for keyword, expansion in expansions.items():
            if keyword in query:
                # 只扩展，不替换原查询
                expanded = f"{query} {expansion}"
                break

        return expanded

    def preload(self):
        """预加载所有资源（可选，用于启动时初始化）"""
        _ = self.embed_model
        _ = self.reranker
        _ = self.index
        _ = self.metas
        print("所有资源预加载完成")

