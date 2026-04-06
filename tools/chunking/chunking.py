# -*- coding: utf-8 -*-
"""
智能文档分块工具

- 基于语义边界切分文本
- 感知 Markdown 标题、列表、表格结构
- 输出当前系统使用的 dataset/chunks JSONL 格式
"""
import argparse
import json
import pathlib
import re
from typing import Dict, List, Tuple


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATABASE_DIR = PROJECT_ROOT / "dataset" / "database"
CHUNK_DIR = PROJECT_ROOT / "dataset" / "chunks"


class SmartChunker:
    """面向通知公告类文档的轻量级结构化分块器。"""

    def __init__(
        self,
        target_size: int = 600,
        min_size: int = 50,
        max_size: int = 1200,
        overlap: int = 120,
    ):
        self.target_size = target_size
        self.min_size = min_size
        self.max_size = max_size
        self.overlap = overlap
        self.sent_pattern = re.compile(r"(?<=[。！？?!\n])\s*")

    def extract_structure(self, text: str) -> List[Dict]:
        """抽取 Markdown 结构，尽量保留标题、列表和表格边界。"""
        lines = text.split("\n")
        sections: List[Dict] = []
        current_section = {"type": "text", "content": [], "level": 0}
        in_table = False
        in_list = False

        for line in lines:
            stripped = line.strip()

            if stripped == "---":
                continue
            if stripped.startswith("**") and ("来源" in stripped or "发布日期" in stripped):
                continue

            if stripped.startswith("#"):
                if current_section["content"]:
                    sections.append(current_section)
                level = len(re.match(r"^#+", stripped).group())
                heading_text = stripped.lstrip("#").strip()
                sections.append({"type": "heading", "level": level, "content": [heading_text]})
                current_section = {"type": "text", "content": [], "level": level}
                in_table = False
                in_list = False
                continue

            if "|" in stripped and stripped.count("|") >= 2:
                if not in_table:
                    if current_section["content"]:
                        sections.append(current_section)
                    current_section = {
                        "type": "table",
                        "content": [],
                        "level": current_section["level"],
                    }
                    in_table = True
                current_section["content"].append(line)
                continue
            elif in_table:
                sections.append(current_section)
                current_section = {"type": "text", "content": [], "level": current_section["level"]}
                in_table = False

            is_list_item = bool(
                re.match(r"^(?:[\d\-\*\u2022]+[.)]?\s+)", stripped)
                or re.match(r"^[一二三四五六七八九十]+[、.]\s+", stripped)
            )

            if is_list_item:
                if not in_list:
                    if current_section["content"] and current_section["type"] != "list":
                        sections.append(current_section)
                        current_section = {
                            "type": "list",
                            "content": [],
                            "level": current_section["level"],
                        }
                    elif not current_section["content"]:
                        current_section["type"] = "list"
                    in_list = True
                current_section["content"].append(line)
                continue
            elif in_list and stripped:
                current_section["content"].append(line)
                continue
            elif in_list and not stripped:
                sections.append(current_section)
                current_section = {"type": "text", "content": [], "level": current_section["level"]}
                in_list = False
                continue

            if stripped:
                if current_section["type"] != "text":
                    if current_section["content"]:
                        sections.append(current_section)
                    current_section = {"type": "text", "content": [], "level": current_section["level"]}
                current_section["content"].append(line)
            else:
                if current_section["content"]:
                    sections.append(current_section)
                    current_section = {"type": "text", "content": [], "level": current_section["level"]}

        if current_section["content"]:
            sections.append(current_section)

        return sections

    def chunk_section(self, section: Dict) -> List[str]:
        """对单个 section 进行切块。"""
        content = "\n".join(section["content"]).strip()
        if not content:
            return []

        if section["type"] in {"table", "list"}:
            if len(content) <= self.max_size:
                return [content]

            lines = section["content"]
            chunks: List[str] = []
            current_lines: List[str] = []
            current_len = 0
            for line in lines:
                line_len = len(line)
                if current_len + line_len > self.target_size and current_lines:
                    chunks.append("\n".join(current_lines))
                    current_lines = [line]
                    current_len = line_len
                else:
                    current_lines.append(line)
                    current_len += line_len
            if current_lines:
                chunks.append("\n".join(current_lines))
            return chunks

        if section["type"] == "heading":
            return [content]

        return self._chunk_text_by_sentences(content)

    def _chunk_text_by_sentences(self, text: str) -> List[str]:
        sentences = [sentence.strip() for sentence in self.sent_pattern.split(text) if sentence.strip()]
        if not sentences:
            return []

        chunks: List[str] = []
        current_chunk: List[str] = []
        current_len = 0

        for sentence in sentences:
            sent_len = len(sentence)

            if sent_len > self.max_size:
                if current_chunk:
                    chunks.append("".join(current_chunk))
                    current_chunk = []
                    current_len = 0

                for start in range(0, sent_len, self.target_size):
                    chunks.append(sentence[start : start + self.target_size])
                continue

            if current_len + sent_len > self.target_size and current_chunk:
                chunk_text = "".join(current_chunk)
                chunks.append(chunk_text)

                overlap_text = chunk_text[-self.overlap :] if len(chunk_text) > self.overlap else chunk_text
                current_chunk = [overlap_text, sentence]
                current_len = len(overlap_text) + sent_len
            else:
                current_chunk.append(sentence)
                current_len += sent_len

        if current_chunk:
            chunks.append("".join(current_chunk))

        return [chunk for chunk in chunks if len(chunk) >= self.min_size]

    def chunk_document(self, text: str, title: str = "") -> List[Tuple[str, Dict]]:
        """对整篇文档执行结构化切块。"""
        sections = self.extract_structure(text)
        chunks_with_meta: List[Tuple[str, Dict]] = []
        heading_stack = [title] if title else []
        current_heading = title

        merged_sections: List[Dict] = []
        index = 0
        while index < len(sections):
            section = sections[index]
            if section["type"] == "text":
                merged_content: List[str] = []
                current_level = section["level"]
                while (
                    index < len(sections)
                    and sections[index]["type"] == "text"
                    and sections[index]["level"] == current_level
                ):
                    merged_content.extend(sections[index]["content"])
                    index += 1
                merged_sections.append(
                    {"type": "text", "content": merged_content, "level": current_level}
                )
            else:
                merged_sections.append(section)
                index += 1

        for section in merged_sections:
            if section["type"] == "heading":
                heading_text = section["content"][0] if section["content"] else ""
                level = section.get("level", 1)

                while len(heading_stack) > level:
                    heading_stack.pop()

                if len(heading_stack) == level and heading_stack:
                    heading_stack[-1] = heading_text
                else:
                    heading_stack.append(heading_text)

                current_heading = " > ".join([part for part in heading_stack if part])
                chunks_with_meta.append(
                    (
                        heading_text,
                        {"type": "heading", "heading": current_heading, "level": level},
                    )
                )
                continue

            for chunk_text in self.chunk_section(section):
                chunks_with_meta.append(
                    (
                        chunk_text,
                        {"type": section["type"], "heading": current_heading or title},
                    )
                )

        return chunks_with_meta


def process_documents(
    database_dir=DATABASE_DIR,
    chunk_dir=CHUNK_DIR,
    target_size: int = 600,
    overlap: int = 120,
    prune_stale: bool = True,
):
    """
    批量处理 dataset/database，并输出系统当前使用的 chunk JSONL。
    """
    try:
        from tqdm import tqdm
    except ModuleNotFoundError:
        def tqdm(iterable, **_kwargs):
            return iterable

    chunker = SmartChunker(target_size=target_size, overlap=overlap)
    database_path = pathlib.Path(database_dir).expanduser().resolve()
    chunk_path = pathlib.Path(chunk_dir).expanduser().resolve()
    chunk_path.mkdir(parents=True, exist_ok=True)

    if not database_path.exists():
        print(f"ERROR: 数据库目录不存在: {database_path}")
        return

    doc_dirs = sorted([directory for directory in database_path.iterdir() if directory.is_dir()])
    print(f"发现 {len(doc_dirs)} 个文档目录")

    total_chunks = 0
    processed_docs = 0
    written_chunk_files = set()

    for doc_dir in tqdm(doc_dirs, desc="Processing documents"):
        meta_path = doc_dir / "meta.json"
        content_path = doc_dir / "content.md"

        if not meta_path.exists() or not content_path.exists():
            continue

        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            text = content_path.read_text(encoding="utf-8")
        except Exception as exc:
            print(f"WARNING: 读取失败 {doc_dir.name}: {exc}")
            continue

        title = meta.get("title", "无标题通知")
        doc_id = meta["doc_id"]
        out_path = chunk_path / f"{doc_id}.jsonl"
        written_chunk_files.add(out_path.name)

        chunks_with_meta = chunker.chunk_document(text, title)
        if not chunks_with_meta:
            if out_path.exists():
                out_path.unlink()
            continue

        with open(out_path, "w", encoding="utf-8") as file_handle:
            for index, (chunk_text, chunk_meta) in enumerate(chunks_with_meta, 1):
                item = {
                    "id": f"{doc_id}#p{index}",
                    "doc_id": doc_id,
                    "titles": [title, chunk_meta.get("heading", title)],
                    "text": chunk_text,
                    "chunk_type": chunk_meta.get("type", "text"),
                    "heading_path": chunk_meta.get("heading", title),
                    "doc_type": meta.get("doc_type", "通知公告"),
                    "dept": meta.get("dept", "教务处"),
                    "publish_date": meta.get("publish_date"),
                    "source_url": meta.get("source_url"),
                    "has_attachments": meta.get("has_attachments", False),
                    "attachment_count": meta.get("attachment_count", 0),
                    "lang": "zh",
                }
                file_handle.write(json.dumps(item, ensure_ascii=False) + "\n")

        total_chunks += len(chunks_with_meta)
        processed_docs += 1

    pruned_files = 0
    if prune_stale:
        for existing_file in chunk_path.glob("*.jsonl"):
            if existing_file.name not in written_chunk_files:
                existing_file.unlink()
                pruned_files += 1

    print("\n分块完成")
    print(f"   - 处理文档: {processed_docs} 个")
    print(f"   - 生成块: {total_chunks} 个")
    if processed_docs > 0:
        print(f"   - 平均每文档: {total_chunks / processed_docs:.1f} 个块")
    print(f"   - 清理旧块文件: {pruned_files} 个" if prune_stale else "   - 保留旧块文件")
    print(f"   - 输出目录: {chunk_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="智能文档分块工具")
    parser.add_argument("--database-dir", default=DATABASE_DIR, help="数据库目录")
    parser.add_argument("--chunk-dir", default=CHUNK_DIR, help="分块输出目录")
    parser.add_argument("--target-size", type=int, default=600, help="目标块大小")
    parser.add_argument("--overlap", type=int, default=120, help="块重叠大小")
    parser.add_argument("--no-prune", action="store_true", help="保留 chunk 目录中的旧文件")

    args = parser.parse_args()

    process_documents(
        database_dir=args.database_dir,
        chunk_dir=args.chunk_dir,
        target_size=args.target_size,
        overlap=args.overlap,
        prune_stale=not args.no_prune,
    )
