# -*- coding: utf-8 -*-
"""
系统诊断脚本 - 检查所有配置和服务状态
"""
import os
import sys
from pathlib import Path

print("="*70)
print("🔍 RAG系统诊断")
print("="*70)

# 1. 检查环境变量（API Keys）
print("\n1️⃣  检查API密钥配置...")
env_file = Path("../.env")
if env_file.exists():
    print(f"   ✅ .env 文件存在")
    with open(env_file, encoding='utf-8') as f:
        content = f.read()
        keys_to_check = [
            "DEEPSEEK_API_KEY",
            "OPENAI_API_KEY",
            "DASHSCOPE_API_KEY",
            "ZHIPU_API_KEY"
        ]
        found_keys = []
        for key in keys_to_check:
            if key in content and not content.split(key)[1].split('\n')[0].strip('= ').startswith('#'):
                found_keys.append(key)
                # 检查是否为空
                value = os.getenv(key)
                if value and value.strip():
                    print(f"   ✅ {key}: 已配置")
                else:
                    print(f"   ⚠️  {key}: 存在但为空")
            else:
                env_value = os.getenv(key)
                if env_value:
                    print(f"   ✅ {key}: 通过环境变量配置")
                else:
                    print(f"   ⚪ {key}: 未配置")

        if not found_keys and not any(os.getenv(k) for k in keys_to_check):
            print(f"   ⚠️  未找到任何API密钥配置")
else:
    print(f"   ⚠️  .env 文件不存在")
    print(f"   💡 请创建.env文件并配置API密钥")

# 2. 检查配置
print("\n2️⃣  检查应用配置...")
try:
    sys.path.insert(0, '..')
    from app.core.config import Settings
    settings = Settings()
    print(f"   ✅ 配置加载成功")
    print(f"   📦 LLM提供商: {settings.llm_provider}")
    print(f"   🤖 LLM模型: {settings.llm_model}")
    print(f"   📊 Embedding模型: {settings.embed_model}")
    print(f"   🔄 Rerank模型: {settings.rerank_model or '未启用'}")

    # 检查对应的API key是否配置
    key_map = {
        "deepseek": "DEEPSEEK_API_KEY",
        "openai": "OPENAI_API_KEY",
        "qwen": "DASHSCOPE_API_KEY",
        "zhipu": "ZHIPU_API_KEY"
    }
    required_key = key_map.get(settings.llm_provider.lower())
    if required_key:
        key_value = os.getenv(required_key)
        if key_value and key_value.strip():
            print(f"   ✅ {required_key} 已配置")
        else:
            print(f"   ❌ {required_key} 未配置或为空！")
            print(f"   💡 请在.env文件中添加: {required_key}=your_api_key_here")

except Exception as e:
    print(f"   ❌ 配置加载失败: {e}")
    sys.exit(1)

# 3. 检查索引文件
print("\n3️⃣  检查向量索引...")
index_dir = Path(settings.index_dir)
index_file = index_dir / "faiss.index"
meta_file = index_dir / "meta.jsonl"

if index_file.exists() and meta_file.exists():
    print(f"   ✅ 索引文件存在")

    try:
        import faiss
        index = faiss.read_index(str(index_file))
        print(f"   📊 向量维度: {index.d}")
        print(f"   📝 向量数量: {index.ntotal}")

        # 检查维度是否匹配
        expected_dim = {
            "small": 512,
            "base": 768,
            "large": 1024
        }
        model_type = None
        for key in expected_dim:
            if key in settings.embed_model.lower():
                model_type = key
                break

        if model_type and expected_dim[model_type] == index.d:
            print(f"   ✅ 索引维度与模型匹配 ({model_type}-{index.d}维)")
        elif model_type:
            print(f"   ❌ 索引维度({index.d})与模型({model_type}-{expected_dim[model_type]}维)不匹配！")
            print(f"   💡 需要重建索引: python tools/rebuild_index.py")

    except Exception as e:
        print(f"   ⚠️  索引文件读取失败: {e}")
else:
    print(f"   ❌ 索引文件不存在")
    print(f"   💡 请运行: python tools/rebuild_index.py")

# 4. 检查文档数据
print("\n4️⃣  检查文档数据...")
chunk_dir = Path("../dataset/chunks")
if chunk_dir.exists():
    chunk_files = list(chunk_dir.glob("*.jsonl"))
    print(f"   ✅ 分块目录存在")
    print(f"   📦 分块文件数: {len(chunk_files)}")

    if len(chunk_files) == 0:
        print(f"   ⚠️  没有分块文件")
        print(f"   💡 请运行: cd tools; python chunking.py")
else:
    print(f"   ❌ 分块目录不存在")

# 5. 测试LLM连接
print("\n5️⃣  测试LLM连接...")
try:
    from app.models.llm import make_llm

    required_key = key_map.get(settings.llm_provider.lower())
    key_value = os.getenv(required_key)

    if not key_value or not key_value.strip():
        print(f"   ⚠️  跳过测试（API密钥未配置）")
    else:
        print(f"   🔄 正在测试{settings.llm_provider}连接...")
        llm = make_llm(
            settings.llm_provider,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=100
        )

        test_messages = [
            {"role": "user", "content": "你好，请回复'测试成功'"}
        ]

        response = llm.chat(test_messages)
        print(f"   ✅ LLM连接成功")
        print(f"   💬 测试回复: {response[:50]}...")

except Exception as e:
    print(f"   ❌ LLM连接失败: {e}")
    print(f"   💡 请检查API密钥是否正确")

# 6. 测试检索服务
print("\n6️⃣  测试检索服务...")
try:
    if index_file.exists():
        from app.services.retrieval import RetrievalService

        print(f"   🔄 正在初始化检索服务...")
        print(f"   📦 使用模型: {settings.embed_model}")
        retrieval = RetrievalService(
            index_dir=str(index_dir),
            embed_model_name=settings.embed_model,  # 使用配置中的模型
            rerank_model_name=settings.rerank_model,
            topk_faiss=settings.topk_faiss,
            topk_final=settings.topk_final
        )

        print(f"   🔄 正在测试检索...")
        results = retrieval.retrieve("测试查询")
        print(f"   ✅ 检索服务正常")
        print(f"   📊 返回结果数: {len(results)}")
    else:
        print(f"   ⚠️  跳过测试（索引不存在）")

except Exception as e:
    print(f"   ❌ 检索服务失败: {e}")
    import traceback
    traceback.print_exc()

# 总结
print("\n" + "="*70)
print("📋 诊断总结")
print("="*70)

issues = []
if not env_file.exists() or not any(os.getenv(k) for k in keys_to_check):
    issues.append("⚠️  API密钥未配置")

if not index_file.exists():
    issues.append("⚠️  向量索引未构建")

if len(chunk_files) == 0 if chunk_dir.exists() else True:
    issues.append("⚠️  文档分块未生成")

if issues:
    print("\n发现以下问题:")
    for issue in issues:
        print(f"  {issue}")

    print("\n💡 解决方案:")
    if "API密钥" in str(issues):
        print("  1. 创建或编辑 .env 文件")
        print("  2. 添加API密钥，例如: DEEPSEEK_API_KEY=sk-xxx")
    if "文档分块" in str(issues):
        print("  3. 运行: cd tools; python chunking.py")
    if "向量索引" in str(issues):
        print("  4. 运行: python tools/rebuild_index.py")
else:
    print("\n✅ 所有检查通过！系统可以正常运行。")
    print("\n🚀 启动命令:")
    print("   uvicorn app.main:app --reload --port 8000")

print("\n" + "="*70)

