# -*- coding: utf-8 -*-
"""Prompt Templates Management"""
from typing import List, Dict


class PromptTemplates:
    """统一管理所有 Prompt 模板"""

    RAG_SYSTEM = """你是河南师范大学教务处智能助手。
你的任务是根据提供的学校官方文档准确回答问题。
注意：
1. 特别关注文档中的日期、时间、地点等关键信息
2. 如果多个文档有相关信息，优先使用最新的文档
3. 直接给出明确答案，不要过度推测
4. 如果文档中没有明确信息，诚实告知"""

    RAG_USER = """请基于以下文档回答用户的问题。

问题: {question}

相关文档：
{context}

回答要求：
1. 仔细阅读每个文档的日期和内容
2. 提取所有与问题相关的关键信息（特别是日期、时间、地点）
3. 如果有具体的日期和安排，请清晰列出
4. 如果文档信息不完整或矛盾，请指出
5. 使用中文回答，语气友好专业

回答:"""

    @staticmethod
    def format_rag_prompt(question: str, docs: List[Dict]) -> List[Dict[str, str]]:
        """
        格式化 RAG Prompt（优化版：强调关键信息）

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
            url = d.get("source_url", "")

            # 突出显示日期和标题
            context += f"【文档{i}】\n"
            context += f"标题：{title}\n"
            context += f"发布日期：{date}\n"
            if url:
                context += f"链接：{url}\n"
            context += f"内容：\n{text}\n"
            context += "-" * 50 + "\n\n"

        return [
            {"role": "system", "content": PromptTemplates.RAG_SYSTEM},
            {"role": "user", "content": PromptTemplates.RAG_USER.format(
                question=question,
                context=context
            )}
        ]

