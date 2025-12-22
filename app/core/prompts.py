# -*- coding: utf-8 -*-
"""Prompt Templates Management"""
from typing import List, Dict


class PromptTemplates:
    """统一管理所有 Prompt 模板"""

    RAG_SYSTEM = "你是河南师范大学教务处智能助手。"

    RAG_USER = """你是一位熟悉河南师范大学教务与校园事务的助手。使用以上下文来回答用户的问题。如果你不知道答案，就说你"未在学校文件中找到明确规定"。总是使用中文回答。

问题: {question}

可参考的上下文：
···
{context}
···

如果给定的上下文无法让你做出回答，请回答数据库中没有这个内容，你不知道。
有用的回答:"""

    @staticmethod
    def format_rag_prompt(question: str, docs: List[Dict]) -> List[Dict[str, str]]:
        """
        格式化 RAG Prompt

        Args:
            question: 用户问题
            docs: 检索到的文档列表

        Returns:
            OpenAI 格式的 messages 列表
        """
        context = ""
        for i, d in enumerate(docs, 1):
            title = d["titles"][0] if isinstance(d["titles"], list) else d["titles"]
            date = d.get("publish_date", "未知日期")
            text = d["text"]
            context += f"[文档{i}] {title}（{date}）\n{text}\n\n"

        return [
            {"role": "system", "content": PromptTemplates.RAG_SYSTEM},
            {"role": "user", "content": PromptTemplates.RAG_USER.format(
                question=question,
                context=context
            )}
        ]

