# -*- coding: utf-8 -*-
"""
智能文档分块工具（优化版）
- 基于语义边界的智能切分
- 支持Markdown结构感知（标题、列表、表格）
- 自适应块大小优化
- 保留文档结构信息
"""
import os, re, json, pathlib
from tqdm import tqdm
from typing import List, Tuple, Dict
import argparse

# 目录配置
DATABASE_DIR = "../../dataset/database"
CHUNK_DIR = "../../dataset/chunks"
os.makedirs(CHUNK_DIR, exist_ok=True)


class SmartChunker:
    """智能文档分块器"""

    def __init__(self, target_size: int = 600, min_size: int = 50,
                 max_size: int = 1200, overlap: int = 120):
        """
        初始化分块器（优化版：增大块大小以保留更多上下文）

        Args:
            target_size: 目标块大小（字符数）- 增加到600以保留更完整的信息
            min_size: 最小块大小
            max_size: 最大块大小 - 增加到1200以避免截断重要内容
            overlap: 块之间的重叠字符数 - 增加到120以保持连贯性
        """
        self.target_size = target_size
        self.min_size = min_size
        self.max_size = max_size
        self.overlap = overlap

        # 句子边界正则（包含更多分隔符）
        self.sent_pattern = re.compile(r'(?<=[。！？!?；;\n])\s*')

    def extract_structure(self, text: str) -> List[Dict]:
        """
        提取Markdown文档结构

        Returns:
            结构化的文本段落列表，包含段落类型和内容
        """
        lines = text.split('\n')
        sections = []
        current_section = {'type': 'text', 'content': [], 'level': 0}
        in_table = False
        in_list = False

        for line in lines:
            stripped = line.strip()

            # 跳过元信息分隔符和元信息行
            if stripped == '---':
                continue
            if stripped.startswith('**') and ('来源' in stripped or '发布日期' in stripped):
                continue

            # 标题检测
            if stripped.startswith('#'):
                if current_section['content']:
                    sections.append(current_section)
                level = len(re.match(r'^#+', stripped).group())
                heading_text = stripped.lstrip('#').strip()  # 移除#号，只保留标题文本
                current_section = {
                    'type': 'heading',
                    'level': level,
                    'content': [heading_text]
                }
                sections.append(current_section)
                current_section = {'type': 'text', 'content': [], 'level': level}
                continue

            # 表格检测
            if '|' in stripped and stripped.count('|') >= 2:
                if not in_table:
                    if current_section['content']:
                        sections.append(current_section)
                    current_section = {'type': 'table', 'content': [], 'level': current_section['level']}
                    in_table = True
                current_section['content'].append(line)
                continue
            elif in_table:
                sections.append(current_section)
                current_section = {'type': 'text', 'content': [], 'level': current_section['level']}
                in_table = False

            # 列表检测
            if re.match(r'^[\d\-*•]+[.)]\s+', stripped) or re.match(r'^[一二三四五六七八九十]+[、.]\s+', stripped):
                if not in_list:
                    if current_section['content'] and current_section['type'] != 'list':
                        sections.append(current_section)
                        current_section = {'type': 'list', 'content': [], 'level': current_section['level']}
                    elif not current_section['content']:
                        current_section['type'] = 'list'
                    in_list = True
                current_section['content'].append(line)
                continue
            elif in_list and stripped:
                # 列表项延续
                current_section['content'].append(line)
                continue
            elif in_list and not stripped:
                sections.append(current_section)
                current_section = {'type': 'text', 'content': [], 'level': current_section['level']}
                in_list = False
                continue

            # 普通文本
            if stripped:
                if current_section['type'] not in ['text']:
                    if current_section['content']:
                        sections.append(current_section)
                    current_section = {'type': 'text', 'content': [], 'level': current_section['level']}
                current_section['content'].append(line)
            else:
                # 空行作为段落分隔
                if current_section['content']:
                    sections.append(current_section)
                    current_section = {'type': 'text', 'content': [], 'level': current_section['level']}

        # 添加最后一个section
        if current_section['content']:
            sections.append(current_section)

        return sections

    def chunk_section(self, section: Dict) -> List[str]:
        """
        对单个section进行分块

        Args:
            section: 包含type、content、level的字典

        Returns:
            分块后的文本列表
        """
        content = '\n'.join(section['content']).strip()
        if not content:
            return []

        # 表格和列表尽量保持完整
        if section['type'] in ['table', 'list']:
            if len(content) <= self.max_size:
                return [content]
            # 如果过长，按行拆分
            lines = section['content']
            chunks = []
            current = []
            current_len = 0
            for line in lines:
                line_len = len(line)
                if current_len + line_len > self.target_size and current:
                    chunks.append('\n'.join(current))
                    current = [line]
                    current_len = line_len
                else:
                    current.append(line)
                    current_len += line_len
            if current:
                chunks.append('\n'.join(current))
            return chunks

        # 标题单独成块（与后续文本合并）
        if section['type'] == 'heading':
            return [content]

        # 普通文本：基于句子边界分块
        return self._chunk_text_by_sentences(content)

    def _chunk_text_by_sentences(self, text: str) -> List[str]:
        """
        基于句子边界对文本进行分块
        """
        # 分句
        sentences = self.sent_pattern.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return []

        chunks = []
        current_chunk = []
        current_len = 0

        for sent in sentences:
            sent_len = len(sent)

            # 单句过长，强制截断
            if sent_len > self.max_size:
                if current_chunk:
                    chunks.append(''.join(current_chunk))
                    current_chunk = []
                    current_len = 0
                # 按最大长度截断
                for i in range(0, sent_len, self.target_size):
                    chunks.append(sent[i:i+self.target_size])
                continue

            # 判断是否需要新建块
            if current_len + sent_len > self.target_size and current_chunk:
                chunk_text = ''.join(current_chunk)
                chunks.append(chunk_text)

                # 添加重叠部分
                overlap_text = chunk_text[-self.overlap:] if len(chunk_text) > self.overlap else chunk_text
                current_chunk = [overlap_text, sent]
                current_len = len(overlap_text) + sent_len
            else:
                current_chunk.append(sent)
                current_len += sent_len

        # 添加最后一个块
        if current_chunk:
            chunks.append(''.join(current_chunk))

        # 过滤过短的块
        return [c for c in chunks if len(c) >= self.min_size]

    def chunk_document(self, text: str, title: str = "") -> List[Tuple[str, Dict]]:
        """
        对整个文档进行智能分块

        Args:
            text: 文档内容（Markdown格式）
            title: 文档标题

        Returns:
            (块文本, 块元数据) 的列表
        """
        sections = self.extract_structure(text)
        chunks_with_meta = []
        current_heading = title
        heading_stack = [title]  # 标题层级栈

        # 合并连续的文本sections以避免过度碎片化
        merged_sections = []
        i = 0
        while i < len(sections):
            section = sections[i]

            if section['type'] == 'text':
                # 合并连续的文本sections
                merged_content = []
                current_level = section['level']

                while i < len(sections) and sections[i]['type'] == 'text' and sections[i]['level'] == current_level:
                    merged_content.extend(sections[i]['content'])
                    i += 1

                merged_sections.append({
                    'type': 'text',
                    'content': merged_content,
                    'level': current_level
                })
            else:
                merged_sections.append(section)
                i += 1

        # 现在处理合并后的sections
        for section in merged_sections:
            # 更新标题上下文
            if section['type'] == 'heading':
                heading_text = section['content'][0] if section['content'] else ""
                level = section['level']

                # 维护标题栈
                while len(heading_stack) > level:
                    heading_stack.pop()
                if len(heading_stack) == level:
                    heading_stack[-1] = heading_text
                else:
                    heading_stack.append(heading_text)

                current_heading = ' > '.join(heading_stack)

                # 标题也作为独立chunk（便于检索）
                chunks_with_meta.append((
                    heading_text,
                    {'type': 'heading', 'heading': current_heading, 'level': level}
                ))
                continue

            # 对section内容分块
            section_chunks = self.chunk_section(section)
            for chunk_text in section_chunks:
                chunks_with_meta.append((
                    chunk_text,
                    {'type': section['type'], 'heading': current_heading}
                ))

        return chunks_with_meta


def process_documents(database_dir: str = DATABASE_DIR,
                     chunk_dir: str = CHUNK_DIR,
                     target_size: int = 600,
                     overlap: int = 120):
    """
    批量处理文档目录（优化版：更大的块大小）

    Args:
        database_dir: 数据库目录（包含各个文档文件夹）
        chunk_dir: 输出分块目录
        target_size: 目标块大小（增加到600）
        overlap: 重叠大小（增加到120）
    """
    chunker = SmartChunker(target_size=target_size, overlap=overlap)
    database_path = pathlib.Path(database_dir)

    if not database_path.exists():
        print(f"❌ 数据库目录不存在: {database_dir}")
        return

    doc_dirs = [d for d in database_path.iterdir() if d.is_dir()]
    print(f"📂 发现 {len(doc_dirs)} 个文档目录")

    total_chunks = 0
    processed_docs = 0

    for doc_dir in tqdm(doc_dirs, desc="🔄 Processing documents"):
        meta_path = doc_dir / "meta.json"
        content_path = doc_dir / "content.md"

        if not meta_path.exists() or not content_path.exists():
            continue

        # 读取元数据和内容
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            text = content_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"⚠️  读取失败 {doc_dir.name}: {e}")
            continue

        title = meta.get("title", "无标题通知")
        doc_id = meta["doc_id"]

        # 智能分块
        chunks_with_meta = chunker.chunk_document(text, title)

        if not chunks_with_meta:
            continue

        # 保存分块结果
        out_path = pathlib.Path(chunk_dir) / f"{doc_id}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            for i, (chunk_text, chunk_meta) in enumerate(chunks_with_meta, 1):
                item = {
                    "id": f"{doc_id}#p{i}",
                    "doc_id": doc_id,
                    "titles": [title, chunk_meta.get('heading', title)],
                    "text": chunk_text,
                    "chunk_type": chunk_meta.get('type', 'text'),
                    "heading_path": chunk_meta.get('heading', title),
                    "doc_type": meta.get("doc_type", "通知公告"),
                    "dept": meta.get("dept", "教务处"),
                    "publish_date": meta.get("publish_date"),
                    "source_url": meta.get("source_url"),
                    "has_attachments": meta.get("has_attachments", False),
                    "attachment_count": meta.get("attachment_count", 0),
                    "lang": "zh"
                }
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

        total_chunks += len(chunks_with_meta)
        processed_docs += 1

    print(f"\n✅ 分块完成!")
    print(f"   - 处理文档: {processed_docs} 个")
    print(f"   - 生成块: {total_chunks} 个")
    print(f"   - 平均每文档: {total_chunks/processed_docs:.1f} 个块" if processed_docs > 0 else "")
    print(f"   - 输出目录: {chunk_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="智能文档分块工具")
    parser.add_argument("--database-dir", default=DATABASE_DIR, help="数据库目录")
    parser.add_argument("--chunk-dir", default=CHUNK_DIR, help="分块输出目录")
    parser.add_argument("--target-size", type=int, default=600, help="目标块大小（优化为600）")
    parser.add_argument("--overlap", type=int, default=120, help="块重叠大小（优化为120）")

    args = parser.parse_args()

    process_documents(
        database_dir=args.database_dir,
        chunk_dir=args.chunk_dir,
        target_size=args.target_size,
        overlap=args.overlap
    )

