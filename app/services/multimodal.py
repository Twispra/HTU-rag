# -*- coding: utf-8 -*-
"""Multimodal Processing Service (Image & Audio)"""
import os
import tempfile
from pathlib import Path
from typing import Any, Optional, Union, Tuple, Dict
import numpy as np
from PIL import Image
import io

# Lazy imports to avoid loading heavy models at startup
_clip_model = None
_clip_processor = None
_whisper_model = None
_ocr_reader = None

_AUDIO_SUFFIX_BY_MIME = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/opus": ".opus",
    "audio/mp4": ".mp4",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "audio/wav": ".wav",
    "audio/wave": ".wav",
    "audio/x-wav": ".wav",
}
_ALLOWED_AUDIO_SUFFIXES = {".webm", ".ogg", ".opus", ".mp4", ".m4a", ".mp3", ".wav", ".flac", ".aac"}


class MultimodalService:
    """多模态处理服务（图片、音频）"""

    def __init__(self,
                 clip_model_name: str = "openai/clip-vit-base-patch32",
                 whisper_model_name: str = "base",
                 use_ocr: bool = True,
                 media_dir: str = "dataset/media"):
        """
        初始化多模态服务

        Args:
            clip_model_name: CLIP 模型名称（用于图片特征提取）
            whisper_model_name: Whisper 模型大小 (tiny/base/small/medium/large)
            use_ocr: 是否启用 OCR（提取图片中的文字）
            media_dir: 媒体文件存储目录
        """
        self.clip_model_name = clip_model_name
        self.whisper_model_name = whisper_model_name
        self.use_ocr = use_ocr
        self.media_dir = Path(media_dir)
        self.media_dir.mkdir(parents=True, exist_ok=True)

    @property
    def clip_model(self):
        """延迟加载 CLIP 模型"""
        global _clip_model, _clip_processor
        if _clip_model is None:
            print(f"正在加载 CLIP 模型: {self.clip_model_name}")
            from transformers import CLIPModel, CLIPProcessor
            _clip_model = CLIPModel.from_pretrained(self.clip_model_name)
            _clip_processor = CLIPProcessor.from_pretrained(self.clip_model_name)
            print("CLIP 模型加载完成")
        return _clip_model, _clip_processor

    @property
    def whisper_model(self):
        """延迟加载 Whisper 模型"""
        global _whisper_model
        if _whisper_model is None:
            print(f"正在加载 Whisper 模型: {self.whisper_model_name}")
            try:
                import whisper
                _whisper_model = whisper.load_model(self.whisper_model_name)
                print("Whisper 模型加载完成")
            except ImportError:
                print("警告: whisper 未安装，音频功能不可用")
                print("安装方法: pip install openai-whisper")
                _whisper_model = None
        return _whisper_model

    @property
    def ocr_reader(self):
        """延迟加载 OCR 模型"""
        global _ocr_reader
        if _ocr_reader is None and self.use_ocr:
            print("正在加载 PaddleOCR 模型")
            try:
                # ???? Paddle ???????/???
                # ?????????? paddleocr/paddle ????
                os.environ.setdefault("FLAGS_use_pir_api", "0")
                os.environ.setdefault("FLAGS_enable_pir_api", "0")
                os.environ.setdefault("FLAGS_use_mkldnn", "0")

                # 若 paddle 已可用，尝试显式关闭 PIR/MKLDNN
                try:
                    import paddle
                    try:
                        paddle.set_flags({
                            "FLAGS_use_pir_api": 0,
                            "FLAGS_enable_pir_api": 0,
                            "FLAGS_use_mkldnn": 0
                        })
                    except Exception:
                        pass
                except Exception:
                    pass

                from paddleocr import PaddleOCR
                import inspect

                ocr_kwargs = {
                    "use_angle_cls": True,
                    "lang": "ch"
                }
                try:
                    params = inspect.signature(PaddleOCR.__init__).parameters
                    if "show_log" in params:
                        ocr_kwargs["show_log"] = False
                except Exception:
                    # signature introspection may fail; keep default behavior
                    ocr_kwargs["show_log"] = False

                try:
                    _ocr_reader = PaddleOCR(**ocr_kwargs)
                except TypeError:
                    # fallback for older versions without show_log
                    ocr_kwargs.pop("show_log", None)
                    _ocr_reader = PaddleOCR(**ocr_kwargs)

                print("OCR 模型加载完成")
            except ImportError:
                print("警告: paddleocr 未安装，OCR 功能不可用")
                print("安装方法: pip install paddleocr paddlepaddle")
                _ocr_reader = None
        return _ocr_reader

    def extract_image_features(self, image_input: Union[str, Path, Image.Image, bytes]) -> Tuple[np.ndarray, Optional[str]]:
        """
        提取图片特征向量和文字内容

        Args:
            image_input: 图片路径、PIL Image 对象或字节数据

        Returns:
            (image_embedding, ocr_text)
        """
        # 加载图片
        if isinstance(image_input, (str, Path)):
            image = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, bytes):
            image = Image.open(io.BytesIO(image_input)).convert("RGB")
        elif isinstance(image_input, Image.Image):
            image = image.convert("RGB")
        else:
            raise ValueError(f"不支持的图片输入类型: {type(image_input)}")

        # 提取 CLIP 特征
        model, processor = self.clip_model
        inputs = processor(images=image, return_tensors="pt")

        with __import__('torch').no_grad():
            image_features = model.get_image_features(**inputs)
            # 归一化
            image_embedding = image_features / image_features.norm(dim=-1, keepdim=True)
            image_embedding = image_embedding.cpu().numpy().flatten()

        # OCR 提取文字（可选）
        ocr_text = None
        if self.use_ocr and self.ocr_reader:
            try:
                # PaddleOCR 需要 numpy array
                img_array = np.array(image)
                try:
                    result = self.ocr_reader.ocr(img_array, cls=True)
                except TypeError:
                    # 兼容不支持 cls 参数的版本
                    result = self.ocr_reader.ocr(img_array)
                if result and result[0]:
                    ocr_text = "\n".join([line[1][0] for line in result[0]])
            except Exception as e:
                print(f"OCR 处理失败: {e}")

        return image_embedding, ocr_text

    def extract_audio_features(self, audio_path: Union[str, Path]) -> Tuple[str, Optional[np.ndarray]]:
        """
        提取音频特征（转文字 + 可选的音频 embedding）

        Args:
            audio_path: 音频文件路径

        Returns:
            (transcribed_text, audio_embedding)
        """
        audio_path = str(audio_path)

        # Whisper 转录
        model = self.whisper_model
        if model is None:
            raise RuntimeError("Whisper 模型未安装或加载失败")

        import whisper
        audio = whisper.load_audio(audio_path)
        duration = len(audio) / 16000 if len(audio) else 0
        peak = float(np.max(np.abs(audio))) if len(audio) else 0.0
        rms = float(np.sqrt(np.mean(np.square(audio)))) if len(audio) else 0.0
        print(f"[ASR] decoded audio: duration={duration:.2f}s, peak={peak:.6f}, rms={rms:.6f}")

        if len(audio):
            audio = audio - float(np.mean(audio))
            peak = float(np.max(np.abs(audio)))
            if peak > 1e-5:
                audio = np.clip(audio / peak * 0.8, -1.0, 1.0).astype(np.float32)
                rms = float(np.sqrt(np.mean(np.square(audio))))
                print(f"[ASR] normalized audio: peak=0.800000, rms={rms:.6f}")

        result = model.transcribe(
            audio,
            language="zh",
            task="transcribe",
            fp16=False,
            condition_on_previous_text=False,
            no_speech_threshold=1.0,
            initial_prompt="以下是普通话中文问句。",
        )
        transcribed_text = (result.get("text") or "").strip()
        if not transcribed_text:
            fallback_result = model.transcribe(
                audio,
                task="transcribe",
                fp16=False,
                condition_on_previous_text=False,
                no_speech_threshold=1.0,
            )
            transcribed_text = (fallback_result.get("text") or "").strip()
        print(f"[ASR] transcription length={len(transcribed_text)}, text={transcribed_text!r}")

        # 可选：提取音频特征向量（使用 Whisper encoder）
        # 注意：这里简化处理，实际可以用更专业的音频 embedding 模型
        audio_embedding = None
        try:
            import torch
            embedding_audio = whisper.pad_or_trim(audio)
            mel = whisper.log_mel_spectrogram(embedding_audio).to(model.device)

            with torch.no_grad():
                audio_features = model.embed_audio(mel.unsqueeze(0))
                audio_embedding = audio_features.cpu().numpy().flatten()
        except Exception as e:
            print(f"音频特征提取失败: {e}")

        return transcribed_text, audio_embedding

    def _audio_suffix_from_upload(self, audio_info: Dict[str, Any]) -> str:
        """Choose a temporary file suffix that matches the uploaded audio format."""
        content_type = (audio_info.get("content_type") or "").split(";", 1)[0].lower()
        if content_type in _AUDIO_SUFFIX_BY_MIME:
            return _AUDIO_SUFFIX_BY_MIME[content_type]

        filename = audio_info.get("filename") or ""
        suffix = Path(filename).suffix.lower()
        if suffix in _ALLOWED_AUDIO_SUFFIXES:
            return suffix

        return ".webm"

    def encode_text_for_image_search(self, text: str) -> np.ndarray:
        """
        将文本编码为可以与图片特征比较的向量（使用 CLIP 文本编码器）

        Args:
            text: 查询文本

        Returns:
            text_embedding (与图片在同一向量空间)
        """
        model, processor = self.clip_model
        inputs = processor(text=[text], return_tensors="pt", padding=True)

        with __import__('torch').no_grad():
            text_features = model.get_text_features(**inputs)
            # 归一化
            text_embedding = text_features / text_features.norm(dim=-1, keepdim=True)
            text_embedding = text_embedding.cpu().numpy().flatten()

        return text_embedding

    def save_media(self, file_bytes: bytes, filename: str, media_type: str = "image") -> Path:
        """
        保存媒体文件到本地

        Args:
            file_bytes: 文件字节数据
            filename: 文件名
            media_type: 媒体类型 (image/audio)

        Returns:
            保存的文件路径
        """
        type_dir = self.media_dir / media_type
        type_dir.mkdir(parents=True, exist_ok=True)

        file_path = type_dir / filename
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        return file_path

    def process_multimodal_query(self,
                                  text: Optional[str] = None,
                                  image: Optional[Union[str, bytes]] = None,
                                  audio: Optional[Union[str, bytes, Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        处理多模态查询（文本 + 图片 + 音频）

        Args:
            text: 文本查询
            image: 图片（路径或字节）
            audio: 音频（路径或字节）

        Returns:
            处理结果字典
        """
        result = {
            "text_query": text or "",
            "image_embedding": None,
            "image_ocr_text": None,
            "audio_text": None,
            "audio_embedding": None,
            "combined_text": ""
        }

        text_parts = []
        if text:
            text_parts.append(text)

        # 处理图片
        if image:
            try:
                if isinstance(image, bytes):
                    img_emb, ocr_text = self.extract_image_features(image)
                else:
                    img_emb, ocr_text = self.extract_image_features(image)

                result["image_embedding"] = img_emb
                result["image_ocr_text"] = ocr_text
                if ocr_text:
                    text_parts.append(f"[图片文字]: {ocr_text}")
            except Exception as e:
                print(f"图片处理失败: {e}")

        # 处理音频
        if audio:
            try:
                temp_path = None
                audio_payload = audio
                audio_suffix = ".wav"
                if isinstance(audio, dict):
                    audio_payload = audio.get("bytes")
                    audio_suffix = self._audio_suffix_from_upload(audio)
                if not audio_payload:
                    raise ValueError("Uploaded audio is empty")
                print(
                    "[ASR] processing audio: "
                    f"suffix={audio_suffix}, bytes={len(audio_payload) if isinstance(audio_payload, bytes) else 'path'}"
                )
                try:
                    if isinstance(audio_payload, bytes):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=audio_suffix) as tmp:
                            tmp.write(audio_payload)
                            temp_path = tmp.name
                        audio_text, audio_emb = self.extract_audio_features(temp_path)
                    else:
                        audio_text, audio_emb = self.extract_audio_features(audio_payload)
                finally:
                    if temp_path:
                        try:
                            os.remove(temp_path)
                        except OSError:
                            pass

                result["audio_text"] = audio_text
                result["audio_embedding"] = audio_emb
                if audio_text:
                    text_parts.append(f"[音频内容]: {audio_text}")
            except Exception as e:
                print(f"音频处理失败: {e}")

        result["combined_text"] = " ".join(text_parts)
        return result

