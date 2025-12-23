#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
验证爬取结果
"""
import json
import pathlib

dataset_dir = pathlib.Path(__file__).parent.parent / "dataset"
db_dir = dataset_dir / "database"
state_file = dataset_dir / "crawl_state.json"

print("=" * 60)
print("爬取结果统计")
print("=" * 60)

# 统计文档
if db_dir.exists():
    docs = [d for d in db_dir.iterdir() if d.is_dir()]
    print(f"\n📁 总文档数: {len(docs)}")

    # 统计有附件的文档
    with_attach = [d for d in docs if (d / "attachments").exists()]
    print(f"📎 有附件文档: {len(with_attach)}")

    # 统计附件总数
    total_attach = sum(len(list((d / "attachments").iterdir()))
                      for d in with_attach if (d / "attachments").exists())
    print(f"📄 附件总数: {total_attach}")

    # 检查文件完整性
    complete = 0
    for doc in docs:
        if (doc / "content.md").exists() and (doc / "meta.json").exists():
            complete += 1
    print(f"✅ 完整文档: {complete}/{len(docs)}")
else:
    print("❌ database 目录不存在")

# 读取状态
if state_file.exists():
    print(f"\n📊 爬取状态:")
    state = json.loads(state_file.read_text(encoding="utf-8"))
    print(f"   已访问文章: {len(state.get('visited_articles', []))}")
    print(f"   已访问栏目页: {len(state.get('visited_lists', []))}")
else:
    print("\n⚠️  crawl_state.json 不存在")

print("\n" + "=" * 60)
print("验证完成！")
print("=" * 60)

