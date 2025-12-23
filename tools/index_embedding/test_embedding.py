# -*- coding: utf-8 -*-
"""
Embedding 模型对比测试

测试不同模型的：
1. 向量维度
2. 加载时间
3. 编码速度
4. 语义相似度质量
"""
import time
import numpy as np
from sentence_transformers import SentenceTransformer


def test_embedding_model(model_name: str):
    """测试embedding模型性能"""
    print(f"\n{'='*70}")
    print(f"测试模型: {model_name}")
    print(f"{'='*70}")

    # 1. 加载模型
    print("\n1. 加载模型...")
    start = time.time()
    try:
        model = SentenceTransformer(model_name)
        load_time = time.time() - start
        print(f"   ✅ 加载成功")
        print(f"   ⏱️  加载时间: {load_time:.2f}秒")
    except Exception as e:
        print(f"   ❌ 加载失败: {e}")
        return None

    # 2. 模型信息
    print(f"\n2. 模型信息:")
    print(f"   向量维度: {model.get_sentence_embedding_dimension()}")
    print(f"   最大序列长度: {model.max_seq_length}")

    # 3. 编码速度测试
    print(f"\n3. 编码速度测试:")
    test_texts = [
        "关于开展2026届毕业生毕业图像信息采集的通知",
        "河南师范大学关于2023级本科生报名参加普通话水平测试的通知",
        "关于举办教师教学创新大赛备赛指导培训的通知"
    ]

    start = time.time()
    embeddings = model.encode(test_texts, normalize_embeddings=True)
    encode_time = time.time() - start

    print(f"   编码3个文本用时: {encode_time*1000:.1f}ms")
    print(f"   平均每个: {encode_time*1000/len(test_texts):.1f}ms")

    # 4. 语义相似度测试
    print(f"\n4. 语义相似度测试:")
    query = "毕业图像采集"
    docs = [
        "关于开展2026届毕业生毕业图像信息采集的通知",  # 高相关
        "关于举办教师教学创新大赛的通知",  # 低相关
        "2026届毕业生照片拍摄安排通知"  # 中相关
    ]

    q_emb = model.encode([query], normalize_embeddings=True)[0]
    d_embs = model.encode(docs, normalize_embeddings=True)

    similarities = [np.dot(q_emb, d_emb) for d_emb in d_embs]

    print(f"   查询: '{query}'")
    for i, (doc, sim) in enumerate(zip(docs, similarities), 1):
        print(f"   [{i}] 相似度={sim:.4f}: {doc[:40]}...")

    # 5. 区分度测试
    print(f"\n5. 区分度分析:")
    print(f"   最高相似度: {max(similarities):.4f}")
    print(f"   最低相似度: {min(similarities):.4f}")
    print(f"   区分度: {max(similarities) - min(similarities):.4f}")

    return {
        "model_name": model_name,
        "load_time": load_time,
        "dimension": model.get_sentence_embedding_dimension(),
        "encode_time_per_doc": encode_time / len(test_texts),
        "best_similarity": max(similarities),
        "worst_similarity": min(similarities),
        "discrimination": max(similarities) - min(similarities)
    }


def compare_models():
    """对比多个模型"""
    models = [
        "BAAI/bge-small-zh-v1.5",  # 当前使用
        "BAAI/bge-base-zh-v1.5",   # 推荐升级
        # "BAAI/bge-large-zh-v1.5",  # 高质量（如需要请取消注释）
    ]

    results = []
    for model_name in models:
        result = test_embedding_model(model_name)
        if result:
            results.append(result)

    # 对比总结
    if len(results) > 1:
        print(f"\n{'='*70}")
        print("📊 模型对比总结")
        print(f"{'='*70}")
        print(f"\n{'指标':<20} {'small':<15} {'base':<15} {'提升':<15}")
        print(f"{'-'*70}")

        small = results[0]
        base = results[1] if len(results) > 1 else None

        if base:
            print(f"{'向量维度':<20} {small['dimension']:<15} {base['dimension']:<15} {'+' + str(base['dimension']-small['dimension']):<15}")
            print(f"{'加载时间(秒)':<20} {small['load_time']:<15.2f} {base['load_time']:<15.2f} {'+' + f\"{base['load_time']-small['load_time']:.2f}\":<15}")
            print(f"{'编码速度(ms/doc)':<20} {small['encode_time_per_doc']*1000:<15.1f} {base['encode_time_per_doc']*1000:<15.1f} {'+' + f\"{(base['encode_time_per_doc']-small['encode_time_per_doc'])*1000:.1f}\":<15}")
            print(f"{'最佳相似度':<20} {small['best_similarity']:<15.4f} {base['best_similarity']:<15.4f} {'+' + f\"{base['best_similarity']-small['best_similarity']:.4f}\":<15}")
            print(f"{'区分度':<20} {small['discrimination']:<15.4f} {base['discrimination']:<15.4f} {'+' + f\"{base['discrimination']-small['discrimination']:.4f}\":<15}")
            
            print(f"\n💡 结论:")
            if base['discrimination'] > small['discrimination']:
                improvement = (base['discrimination'] / small['discrimination'] - 1) * 100
                print(f"   ✅ base模型区分度提升 {improvement:.1f}%")
                print(f"   ✅ 推荐升级到 bge-base-zh-v1.5")
            print(f"   ⚠️  加载时间增加 {base['load_time']-small['load_time']:.2f}秒（首次加载）")
            print(f"   ⚠️  编码时间增加 {(base['encode_time_per_doc']-small['encode_time_per_doc'])*1000:.1f}ms/doc")


if __name__ == "__main__":
    print("🔬 Embedding模型性能测试")
    print("="*70)
    print("说明: 首次运行会下载模型到 ~/.cache/huggingface/")
    print("      small模型 ~100MB, base模型 ~400MB")
    print("="*70)

    compare_models()

    print(f"\n{'='*70}")
    print("✅ 测试完成")
    print(f"{'='*70}")

