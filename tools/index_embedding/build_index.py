# -*- coding: utf-8 -*-
"""Build FAISS index from dataset/chunks."""
import argparse
import json
import sys
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHUNK_DIR = PROJECT_ROOT / "dataset" / "chunks"
DEFAULT_INDEX_DIR = PROJECT_ROOT / "dataset" / "index"
DEFAULT_MODEL_NAME = "BAAI/bge-base-zh-v1.5"


def load_settings():
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        from app.core.config import Settings  # noqa: E402
    except ModuleNotFoundError:
        return None
    return Settings()


def normalize_chunk_record(record: dict, source_file: Path, line_number: int) -> dict:
    """Normalize chunk records into the current dataset/index meta format."""
    normalized = dict(record)

    titles = normalized.get("titles")
    if isinstance(titles, str):
        titles = [titles]
    elif not isinstance(titles, list):
        fallback_title = (
            normalized.get("title")
            or normalized.get("heading_path")
            or normalized.get("doc_id")
            or source_file.stem
        )
        titles = [str(fallback_title)]

    titles = [str(item).strip() for item in titles if str(item).strip()]
    if not titles:
        titles = [normalized.get("doc_id", source_file.stem)]

    text = normalized.get("text")
    if not isinstance(text, str) or not text.strip():
        fallback_text = normalized.get("content") or normalized.get("chunk") or ""
        text = str(fallback_text).strip()
    if not text:
        raise ValueError(f"{source_file}:{line_number} 缺少可索引文本")

    normalized["titles"] = titles
    normalized["text"] = text
    normalized.setdefault("doc_id", source_file.stem)
    normalized.setdefault("id", f"{normalized['doc_id']}#p{line_number}")
    normalized.setdefault("lang", "zh")

    return normalized


def compose_embedding_text(record: dict) -> str:
    return " ".join(record["titles"]) + " " + record["text"]


def load_chunk_records(chunk_dir: Path):
    try:
        from tqdm import tqdm
    except ModuleNotFoundError:
        def tqdm(iterable, **_kwargs):
            return iterable

    chunk_files = sorted(chunk_dir.glob("*.jsonl"))
    if not chunk_files:
        raise FileNotFoundError(f"未找到 chunk 文件: {chunk_dir}")

    records = []
    texts = []

    for chunk_file in tqdm(chunk_files, desc="Loading chunks"):
        with open(chunk_file, encoding="utf-8") as file_handle:
            for line_number, line in enumerate(file_handle, 1):
                if not line.strip():
                    continue
                normalized = normalize_chunk_record(json.loads(line), chunk_file, line_number)
                records.append(normalized)
                texts.append(compose_embedding_text(normalized))

    if not texts:
        raise ValueError(f"{chunk_dir} 中没有可编码的 chunk 数据")

    return records, texts


def build_index(
    chunk_dir=DEFAULT_CHUNK_DIR,
    index_dir=DEFAULT_INDEX_DIR,
    model_name: Optional[str] = None,
    batch_size: int = 32,
):
    try:
        import faiss
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ModuleNotFoundError as exc:
        raise SystemExit(
            f"缺少依赖: {exc.name}。请先在当前 Python 环境安装项目依赖，例如 `pip install -r requirements.txt`。"
        )

    chunk_path = Path(chunk_dir).expanduser().resolve()
    index_path = Path(index_dir).expanduser().resolve()
    index_path.mkdir(parents=True, exist_ok=True)

    settings = load_settings()
    resolved_model_name = model_name or (
        settings.embed_model if settings is not None else DEFAULT_MODEL_NAME
    )
    print(f"使用模型: {resolved_model_name}")

    records, texts = load_chunk_records(chunk_path)
    print(f"发现 {len(records)} 个 chunk，开始编码...")

    model = SentenceTransformer(resolved_model_name)
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True,
    )

    matrix = np.asarray(embeddings, dtype="float32")
    faiss_index = faiss.IndexFlatIP(matrix.shape[1])
    faiss_index.add(matrix)

    faiss.write_index(faiss_index, str(index_path / "faiss.index"))
    with open(index_path / "meta.jsonl", "w", encoding="utf-8") as file_handle:
        for record in records:
            file_handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    print("向量索引构建完成")
    print(f"   - chunk 数量: {len(records)}")
    print(f"   - 向量维度: {matrix.shape[1]}")
    print(f"   - 索引目录: {index_path}")


def main():
    parser = argparse.ArgumentParser(description="构建文本向量索引")
    parser.add_argument("--chunk-dir", default=DEFAULT_CHUNK_DIR, help="chunk 输入目录")
    parser.add_argument("--index-dir", default=DEFAULT_INDEX_DIR, help="索引输出目录")
    parser.add_argument(
        "--model",
        default=None,
        help="embedding 模型名称；不传时优先读取 app/core/config.py，失败则回退到默认模型",
    )
    parser.add_argument("--batch-size", type=int, default=32, help="编码 batch size")
    args = parser.parse_args()

    build_index(
        chunk_dir=args.chunk_dir,
        index_dir=args.index_dir,
        model_name=args.model,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
