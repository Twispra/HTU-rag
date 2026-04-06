#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Verify crawler output under the project dataset directory."""
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = PROJECT_ROOT / "dataset"
DB_DIR = DATASET_DIR / "database"
STATE_FILE = DATASET_DIR / "crawl_state.json"


print("=" * 60)
print("爬取结果统计")
print("=" * 60)

if DB_DIR.exists():
    docs = [directory for directory in DB_DIR.iterdir() if directory.is_dir()]
    print(f"\n总文档数: {len(docs)}")

    with_attach = [directory for directory in docs if (directory / "attachments").exists()]
    print(f"有附件文档: {len(with_attach)}")

    total_attach = sum(
        len(list((directory / "attachments").iterdir()))
        for directory in with_attach
        if (directory / "attachments").exists()
    )
    print(f"附件总数: {total_attach}")

    complete = 0
    for doc in docs:
        if (doc / "content.md").exists() and (doc / "meta.json").exists():
            complete += 1
    print(f"完整文档: {complete}/{len(docs)}")
else:
    print("ERROR: dataset/database 不存在")

if STATE_FILE.exists():
    print("\n爬取状态:")
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    print(f"   已记录文章: {len(state.get('visited_articles', []))}")
    print(f"   已扫描列表页: {len(state.get('visited_lists', []))}")
    print(f"   最近运行时间: {state.get('last_run_at')}")
else:
    print("\nWARNING: crawl_state.json 不存在")

print("\n" + "=" * 60)
print("验证完成")
print("=" * 60)
