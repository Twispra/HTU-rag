# -*- coding: utf-8 -*-
"""
增强已有的 markdown 文件：添加标题、来源和发布日期等元信息头部
"""
import pathlib
import json

def enhance_markdown_files():
    """为 database 中的所有文档添加 markdown 头部"""
    dataset_path = pathlib.Path("./dataset")
    database_path = dataset_path / "database"

    if not database_path.exists():
        print("database 目录不存在")
        return

    enhanced = 0
    skipped = 0

    for doc_dir in database_path.iterdir():
        if not doc_dir.is_dir():
            continue

        content_md = doc_dir / "content.md"
        meta_json = doc_dir / "meta.json"

        if not content_md.exists() or not meta_json.exists():
            continue

        # 读取元数据
        meta = json.loads(meta_json.read_text(encoding="utf-8"))
        content = content_md.read_text(encoding="utf-8")

        # 检查是否已经有头部（避免重复添加）
        if content.startswith("# ") or "**来源**:" in content[:200]:
            skipped += 1
            continue

        # 构建头部
        title = meta.get("title", "未命名通知")
        source_url = meta.get("source_url", "")
        publish_date = meta.get("publish_date", "")

        header = f"# {title}\n\n"
        header += f"**来源**: {source_url}\n\n"
        if publish_date:
            header += f"**发布日期**: {publish_date}\n\n"
        header += "---\n\n"

        # 添加头部并保存
        enhanced_content = header + content
        content_md.write_text(enhanced_content, encoding="utf-8")

        print(f"✓ 增强: {doc_dir.name}")
        enhanced += 1

    print("\n" + "=" * 80)
    print(f"增强统计:")
    print(f"  - 已增强: {enhanced} 篇")
    print(f"  - 跳过（已有头部）: {skipped} 篇")
    print("=" * 80)

if __name__ == "__main__":
    enhance_markdown_files()

