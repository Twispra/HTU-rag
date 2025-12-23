# -*- coding: utf-8 -*-
"""
重建索引脚本（升级embedding模型后使用）

⚠️ 重要: 更换embedding模型后必须重建索引！
"""
import os
import sys
import time
from pathlib import Path

print("="*70)
print("🔄 重建向量索引")
print("="*70)

# 确认操作
print("\n⚠️  注意事项:")
print("  1. 重建索引会覆盖现有索引文件")
print("  2. 确保已更新 config.py 中的 embed_model 配置")
print("  3. 首次使用新模型会下载到本地（需要网络）")
print("  4. 重建时间取决于文档数量和模型大小")

response = input("\n是否继续重建索引？[y/N]: ").strip().lower()
if response != 'y':
    print("❌ 已取消")
    sys.exit(0)

print("\n" + "="*70)
print("开始重建...")
print("="*70)

start_time = time.time()

# 导入并执行 build_index
try:
    # 切换到 tools 目录
    tools_dir = Path(__file__).parent
    os.chdir(tools_dir)

    print("\n📦 1/3 - 加载配置和模型...")
    from sentence_transformers import SentenceTransformer
    import numpy as np
    import faiss
    import json
    import pathlib
    from tqdm import tqdm

    CHUNK_DIR = "../../dataset/chunks"
    INDEX_DIR = "../../dataset/index"
    os.makedirs(INDEX_DIR, exist_ok=True)

    # 从配置读取模型名
    sys.path.insert(0, str(tools_dir.parent))
    from app.core.config import Settings
    settings = Settings()
    model_name = settings.embed_model

    print(f"   使用模型: {model_name}")
    model = SentenceTransformer(model_name)
    dim = model.get_sentence_embedding_dimension()
    print(f"   向量维度: {dim}")

    print("\n📝 2/3 - 编码文档分块...")
    embeddings, metas = [], []
    chunk_files = list(pathlib.Path(CHUNK_DIR).glob("*.jsonl"))
    print(f"   发现 {len(chunk_files)} 个分块文件")

    total_chunks = 0
    for file in tqdm(chunk_files, desc="   编码进度"):
        with open(file, encoding="utf-8") as f:
            for line in f:
                d = json.loads(line)
                # 组合标题和正文
                txt = " ".join(d["titles"]) + " " + d["text"]
                emb = model.encode(txt, normalize_embeddings=True)
                embeddings.append(emb)
                metas.append(d)
                total_chunks += 1

    print(f"   ✅ 已编码 {total_chunks} 个文档块")

    print("\n🔍 3/3 - 构建FAISS索引...")
    X = np.array(embeddings, dtype="float32")
    print(f"   向量矩阵形状: {X.shape}")

    # 使用内积索引（余弦相似度）
    index = faiss.IndexFlatIP(X.shape[1])
    index.add(X)

    index_path = f"{INDEX_DIR}/faiss.index"
    faiss.write_index(index, index_path)
    print(f"   ✅ FAISS索引已保存: {index_path}")

    meta_path = f"{INDEX_DIR}/meta.jsonl"
    with open(meta_path, "w", encoding="utf-8") as f:
        for m in metas:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    print(f"   ✅ 元数据已保存: {meta_path}")

    elapsed = time.time() - start_time
    print("\n" + "="*70)
    print("✅ 索引重建完成!")
    print("="*70)
    print(f"\n📊 统计信息:")
    print(f"   文档分块数: {total_chunks}")
    print(f"   向量维度: {dim}")
    print(f"   索引大小: {os.path.getsize(index_path) / 1024 / 1024:.1f} MB")
    print(f"   耗时: {elapsed:.2f} 秒")
    print(f"   平均速度: {total_chunks/elapsed:.1f} 块/秒")

    print(f"\n💡 下一步:")
    print(f"   1. 运行 python ../test_startup.py 测试服务")
    print(f"   2. 运行 uvicorn app.main:app --reload 启动服务")

except Exception as e:
    print(f"\n❌ 重建失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

