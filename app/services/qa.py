# -*- coding: utf-8 -*-
"""Question Answering Service"""
import re
from typing import List
from app.services.retrieval import RetrievalService
from app.models.llm import ChatLLM
from app.models.schemas import ChatResponse, DocumentReference, SearchPreviewItem
from app.core.prompts import PromptTemplates


class QAService:
    """问答服务"""

    def __init__(self, retrieval_service: RetrievalService, llm: ChatLLM):
        """
        初始化问答服务

        Args:
            retrieval_service: 检索服务实例
            llm: LLM 客户端实例
        """
        self.retrieval = retrieval_service
        self.llm = llm

    def answer_question(self, question: str) -> ChatResponse:
        """
        回答问题（RAG 生成）

        Args:
            question: 用户问题

        Returns:
            ChatResponse 包含答案和参考文档
        """
        try:
            # 检索相关文档
            docs = self.retrieval.retrieve(question)

            if not docs:
                return ChatResponse(
                    query=question,
                    answer="抱歉，未找到相关内容。请尝试换个方式提问。",
                    references=[]
                )

            # 构建 Prompt
            messages = PromptTemplates.format_rag_prompt(question, docs)

            # 调用 LLM 生成答案
            try:
                answer = self.llm.chat(messages)
                if not answer or not answer.strip():
                    answer = "抱歉，生成回答时出现问题。请稍后再试。"
            except Exception as e:
                print(f"LLM调用失败: {e}")
                # LLM调用失败时，返回检索到的文档摘要
                answer = "（由于LLM服务暂时不可用，以下是相关文档摘要）\n\n"
                for i, d in enumerate(docs[:3], 1):
                    answer += f"{i}. {d['titles'][0]}\n{d['text'][:200]}...\n\n"

            # 去重参考文档
            unique_refs = {}
            for d in docs:
                key = d.get("source_url") or d["titles"][0]
                if key not in unique_refs:
                    unique_refs[key] = DocumentReference(
                        title=d["titles"][0],
                        source_url=d.get("source_url")
                    )

            return ChatResponse(
                query=question,
                answer=answer,
                references=list(unique_refs.values())
            )
        except Exception as e:
            print(f"问答服务错误: {e}")
            import traceback
            traceback.print_exc()
            return ChatResponse(
                query=question,
                answer=f"抱歉，处理您的问题时出现错误：{str(e)}\n\n请检查：\n1. 向量索引是否已构建\n2. API密钥是否配置正确\n3. 网络连接是否正常",
                references=[]
            )

    def preview_search(self, query: str) -> List[SearchPreviewItem]:
        """
        纯检索预览（不调用 LLM）

        Args:
            query: 查询文本

        Returns:
            检索结果列表
        """
        docs = self.retrieval.retrieve(query)
        keywords = re.split(r"[，。；,.!?、\s]+", query)

        results = []
        for d in docs:
            snippet = self._highlight(d["text"], keywords)[:200]
            results.append(SearchPreviewItem(
                title=d["titles"][0],
                publish_date=d.get("publish_date"),
                snippet=snippet,
                source_url=d.get("source_url")
            ))

        return results

    @staticmethod
    def _highlight(text: str, keywords: List[str]) -> str:
        """
        高亮关键词

        Args:
            text: 原始文本
            keywords: 关键词列表

        Returns:
            高亮后的文本（使用 **keyword** 标记）
        """
        for kw in keywords:
            if not kw.strip():
                continue
            text = re.sub(
                re.escape(kw),
                lambda m: f"**{m.group(0)}**",
                text,
                flags=re.I
            )
        return text

