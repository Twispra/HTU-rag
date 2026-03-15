# -*- coding: utf-8 -*-
"""Multimodal Question Answering Service"""
import re
from typing import List, Optional
from app.services.multimodal_retrieval import MultimodalRetrievalService
from app.models.llm import ChatLLM
from app.models.schemas import (
    MultimodalChatResponse, DocumentReference,
    MultimodalSearchPreviewItem, MediaReference
)
from app.core.prompts import PromptTemplates


class MultimodalQAService:
    """多模态问答服务"""

    def __init__(self, multimodal_retrieval: MultimodalRetrievalService, llm: ChatLLM):
        """
        初始化多模态问答服务

        Args:
            multimodal_retrieval: 多模态检索服务实例
            llm: LLM 客户端实例
        """
        self.retrieval = multimodal_retrieval
        self.llm = llm

    def answer_question_multimodal(self,
                                   text: Optional[str] = None,
                                   image: Optional[bytes] = None,
                                   audio: Optional[bytes] = None) -> MultimodalChatResponse:
        """Multimodal QA (RAG generation)."""
        try:
            # Preprocess once to avoid duplicate work
            multimodal_result = self.retrieval.multimodal.process_multimodal_query(text, image, audio)
            combined_query = multimodal_result.get("combined_text", "")
            query_for_prompt = combined_query or text or "[multimodal query]"

            # Campus QA default: use OCR/ASR text only (unless media retrieval is enabled)
            if not combined_query and not self.retrieval.enable_media_retrieval:
                return MultimodalChatResponse(
                    query=query_for_prompt,
                    answer=(
                        "No readable text was detected from the image/audio. "
                        "Please provide a clearer image/audio or type the question in text."
                    ),
                    references=[],
                    image_ocr_text=multimodal_result.get("image_ocr_text"),
                    audio_transcription=multimodal_result.get("audio_text")
                )

            # Retrieval (use preprocessed result)
            docs = self.retrieval.retrieve_multimodal(text, image, audio, preprocessed=multimodal_result)

            if not docs:
                return MultimodalChatResponse(
                    query=query_for_prompt,
                    answer="No relevant content found. Please rephrase or add more specific details.",
                    references=[],
                    image_ocr_text=multimodal_result.get("image_ocr_text"),
                    audio_transcription=multimodal_result.get("audio_text")
                )

            # Build prompt
            messages = self._format_multimodal_prompt(query_for_prompt, docs, multimodal_result)

            # LLM generation
            try:
                answer = self.llm.chat(messages)
                if not answer or not answer.strip():
                    answer = "Sorry, there was a problem generating the response. Please try again."
            except Exception as e:
                print(f"LLM call failed: {e}")
                answer = "(LLM unavailable; here are relevant snippets.)\n\n"
                for i, d in enumerate(docs[:3], 1):
                    answer += f"{i}. {d['titles'][0]}\n{d['text'][:200]}...\n\n"

            # Deduplicate references
            unique_refs = {}
            media_refs = []

            for d in docs:
                key = d.get("source_url") or d["titles"][0]
                if key not in unique_refs:
                    unique_refs[key] = DocumentReference(
                        title=d["titles"][0],
                        source_url=d.get("source_url")
                    )

                if "media_url" in d and "media_type" in d:
                    media_refs.append(MediaReference(
                        media_type=d["media_type"],
                        media_url=d["media_url"],
                        ocr_text=d.get("ocr_text"),
                        transcription=d.get("transcription"),
                        title=d["titles"][0]
                    ))

            return MultimodalChatResponse(
                query=query_for_prompt,
                answer=answer,
                references=list(unique_refs.values()),
                media_references=media_refs,
                image_ocr_text=multimodal_result.get("image_ocr_text"),
                audio_transcription=multimodal_result.get("audio_text")
            )
        except Exception as e:
            print(f"Multimodal QA error: {e}")
            import traceback
            traceback.print_exc()
            return MultimodalChatResponse(
                query=text or "[multimodal query]",
                answer=f"Sorry, an error occurred while processing your request: {str(e)}",
                references=[]
            )

    def preview_search_multimodal(self,
                                  text: Optional[str] = None,
                                  image: Optional[bytes] = None,
                                  audio: Optional[bytes] = None) -> List[MultimodalSearchPreviewItem]:
        """Multimodal preview search (no LLM)."""
        multimodal_result = self.retrieval.multimodal.process_multimodal_query(text, image, audio)
        combined_query = multimodal_result.get("combined_text", "")

        if not combined_query and not self.retrieval.enable_media_retrieval:
            return []

        docs = self.retrieval.retrieve_multimodal(text, image, audio, preprocessed=multimodal_result)

        keywords = re.split(r"[，。；,.!?\s]+", combined_query) if combined_query else []

        results = []
        for d in docs:
            snippet = self._highlight(d.get("text", ""), keywords)[:200]

            results.append(MultimodalSearchPreviewItem(
                title=d["titles"][0] if isinstance(d.get("titles"), list) else d.get("titles", ""),
                publish_date=d.get("publish_date"),
                snippet=snippet,
                source_url=d.get("source_url"),
                media_type=d.get("media_type"),
                media_url=d.get("media_url"),
                similarity_score=d.get("score")
            ))

        return results

    def search_images_by_text(self, text_query: str, topk: int = 12) -> List[MultimodalSearchPreviewItem]:
        """
        基于文本搜索相似图片（CLIP 跨模态检索）

        Args:
            text_query: 文本描述
            topk: 返回结果数量

        Returns:
            图片检索结果列表
        """
        docs = self.retrieval.retrieve_by_image_similarity(text_query, topk)

        results = []
        for d in docs:
            results.append(MultimodalSearchPreviewItem(
                title=d.get("titles", ["未命名图片"])[0] if isinstance(d.get("titles"), list) else d.get("titles", "未命名图片"),
                publish_date=d.get("publish_date"),
                snippet=d.get("text", "")[:200],
                source_url=d.get("source_url"),
                media_type="image",
                media_url=d.get("media_url"),
                similarity_score=d.get("score")
            ))

        return results

    def _format_multimodal_prompt(self, query: str, docs: List[dict], multimodal_result: dict) -> List[dict]:
        """
        格式化多模态 Prompt

        Args:
            query: 组合查询文本
            docs: 检索到的文档列表
            multimodal_result: 多模态处理结果

        Returns:
            OpenAI 格式的 messages 列表
        """
        context = ""
        for i, d in enumerate(docs, 1):
            title = d["titles"][0] if isinstance(d["titles"], list) else d["titles"]
            date = d.get("publish_date", "未知日期")
            text = d["text"]
            url = d.get("source_url", "")

            context += f"\n【文档 {i}】\n"
            context += f"标题: {title}\n"
            context += f"发布日期: {date}\n"
            if url:
                context += f"链接: {url}\n"

            # 添加媒体信息
            if "media_type" in d:
                context += f"媒体类型: {d['media_type']}\n"
                if "ocr_text" in d and d["ocr_text"]:
                    context += f"图片文字: {d['ocr_text']}\n"
                if "transcription" in d and d["transcription"]:
                    context += f"音频转录: {d['transcription']}\n"

            context += f"内容: {text}\n"

        # 增强系统提示（多模态）
        system_prompt = PromptTemplates.RAG_SYSTEM + "\n\n注意：此查询可能包含图片或音频信息，请综合考虑所有模态的信息。"

        # 增强用户提示
        user_prompt = f"""请基于以下文档回答用户的问题。

问题: {query}

"""

        # 添加多模态信息提示
        if multimodal_result.get("image_ocr_text"):
            user_prompt += f"[用户上传图片中的文字]: {multimodal_result['image_ocr_text']}\n\n"

        if multimodal_result.get("audio_text"):
            user_prompt += f"[用户音频转录]: {multimodal_result['audio_text']}\n\n"

        user_prompt += f"""相关文档：
{context}

回答要求：
1. 综合文本、图片和音频信息回答
2. 特别关注日期、时间、地点等关键信息
3. 如果文档中包含图片或音频内容，请在回答中说明
4. 提供清晰、准确的答案

回答:"""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    def _highlight(self, text: str, keywords: List[str]) -> str:
        """高亮关键词"""
        for kw in keywords:
            if kw and len(kw) > 1:
                text = text.replace(kw, f"**{kw}**")
        return text

