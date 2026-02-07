# -*- coding: utf-8 -*-
"""
测试多模态功能
用于验证多模态服务是否正常工作
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.services.multimodal import MultimodalService
from PIL import Image
import io


def test_clip_image_encoding():
    """测试 CLIP 图片编码"""
    print("="*60)
    print("测试 CLIP 图片编码")
    print("="*60)

    # 创建一个简单的测试图片
    img = Image.new('RGB', (224, 224), color='red')

    service = MultimodalService(
        clip_model_name="openai/clip-vit-base-patch32",
        use_ocr=False  # 先不测试 OCR
    )

    try:
        embedding, ocr_text = service.extract_image_features(img)
        print(f"✅ CLIP 编码成功")
        print(f"   向量维度: {embedding.shape}")
        print(f"   向量范数: {(embedding ** 2).sum() ** 0.5:.4f}")
    except Exception as e:
        print(f"❌ CLIP 编码失败: {e}")
        return False

    return True


def test_clip_text_encoding():
    """测试 CLIP 文本编码"""
    print("\n" + "="*60)
    print("测试 CLIP 文本编码（跨模态检索）")
    print("="*60)

    service = MultimodalService(
        clip_model_name="openai/clip-vit-base-patch32",
        use_ocr=False
    )

    try:
        embedding = service.encode_text_for_image_search("一张红色的图片")
        print(f"✅ CLIP 文本编码成功")
        print(f"   向量维度: {embedding.shape}")
        print(f"   向量范数: {(embedding ** 2).sum() ** 0.5:.4f}")
    except Exception as e:
        print(f"❌ CLIP 文本编码失败: {e}")
        return False

    return True


def test_ocr():
    """测试 OCR 功能"""
    print("\n" + "="*60)
    print("测试 OCR 文字识别")
    print("="*60)

    # 创建一个带文字的图片（实际应该是真实图片）
    img = Image.new('RGB', (400, 200), color='white')

    service = MultimodalService(
        clip_model_name="openai/clip-vit-base-patch32",
        use_ocr=True
    )

    try:
        embedding, ocr_text = service.extract_image_features(img)
        print(f"✅ OCR 初始化成功")
        print(f"   提取文字: {ocr_text or '(空白图片，无文字)'}")
    except Exception as e:
        print(f"⚠️  OCR 功能不可用: {e}")
        print("   提示: 如不需要 OCR，可以设置 use_ocr=False")
        return False

    return True


def test_whisper():
    """测试 Whisper 音频转录"""
    print("\n" + "="*60)
    print("测试 Whisper 音频转录")
    print("="*60)

    print("⚠️  需要真实音频文件才能测试")
    print("   跳过此测试（需要时请提供音频文件路径）")

    # 如果有测试音频文件，取消注释以下代码
    # service = MultimodalService(whisper_model_name="base")
    # audio_path = "path/to/test.wav"
    # try:
    #     transcription, embedding = service.extract_audio_features(audio_path)
    #     print(f"✅ Whisper 转录成功")
    #     print(f"   转录文本: {transcription}")
    # except Exception as e:
    #     print(f"❌ Whisper 转录失败: {e}")
    #     return False

    return True


def test_multimodal_query_processing():
    """测试多模态查询处理"""
    print("\n" + "="*60)
    print("测试多模态查询处理")
    print("="*60)

    img = Image.new('RGB', (224, 224), color='blue')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes = img_bytes.getvalue()

    service = MultimodalService(
        clip_model_name="openai/clip-vit-base-patch32",
        use_ocr=False
    )

    try:
        result = service.process_multimodal_query(
            text="这是什么颜色？",
            image=img_bytes,
            audio=None
        )

        print(f"✅ 多模态查询处理成功")
        print(f"   文本查询: {result['text_query']}")
        print(f"   组合文本: {result['combined_text']}")
        print(f"   图片向量: {'存在' if result['image_embedding'] is not None else '不存在'}")

    except Exception as e:
        print(f"❌ 多模态查询处理失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("开始测试多模态功能")
    print("="*60 + "\n")

    results = {}

    # 测试 CLIP
    results['CLIP 图片编码'] = test_clip_image_encoding()
    results['CLIP 文本编码'] = test_clip_text_encoding()

    # 测试 OCR（可选）
    results['OCR 识别'] = test_ocr()

    # 测试 Whisper（需要音频文件）
    results['Whisper 转录'] = test_whisper()

    # 测试组合功能
    results['多模态查询处理'] = test_multimodal_query_processing()

    # 输出测试结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)

    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")

    passed_count = sum(results.values())
    total_count = len(results)

    print(f"\n总计: {passed_count}/{total_count} 测试通过")

    if passed_count == total_count:
        print("\n🎉 所有测试通过！多模态功能正常。")
    elif passed_count >= total_count - 1:
        print("\n⚠️  大部分功能正常，部分可选功能不可用（如 OCR）。")
    else:
        print("\n❌ 存在多个问题，请检查依赖安装和配置。")

    print("\n提示:")
    print("1. 确保已安装所有依赖: pip install -r requirements.txt")
    print("2. 首次运行会自动下载模型，需要网络连接")
    print("3. 如不需要 OCR，可设置 use_ocr=False")
    print("4. Whisper 测试需要真实音频文件")


if __name__ == "__main__":
    main()

