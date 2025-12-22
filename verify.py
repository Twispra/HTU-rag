# -*- coding: utf-8 -*-
"""
项目验证脚本
运行此脚本检查重构是否成功
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

def check_imports():
    """检查所有模块是否能正常导入"""
    print("="*60)
    print("🔍 验证模块导入...")
    print("="*60)

    checks = [
        ("配置管理", "from app.core.config import Settings"),
        ("Prompt 模板", "from app.core.prompts import PromptTemplates"),
        ("LLM 客户端", "from app.models.llm import make_llm, ChatLLM"),
        ("数据模型", "from app.models.schemas import ChatResponse, DocumentReference"),
        ("检索服务", "from app.services.retrieval import RetrievalService"),
        ("问答服务", "from app.services.qa import QAService"),
        ("API 路由", "from app.api.routes import router"),
        ("主应用", "from app.main import app"),
    ]

    failed = []
    for name, import_stmt in checks:
        try:
            exec(import_stmt)
            print(f"  ✅ {name:15} - 导入成功")
        except Exception as e:
            print(f"  ❌ {name:15} - 导入失败: {e}")
            failed.append(name)

    return len(failed) == 0

def check_structure():
    """检查目录结构"""
    print("\n" + "="*60)
    print("🔍 验证目录结构...")
    print("="*60)

    required_dirs = [
        "app",
        "app/api",
        "app/services",
        "app/models",
        "app/core",
        "tests",
        "tools",
    ]

    required_files = [
        "app/main.py",
        "app/api/routes.py",
        "app/services/retrieval.py",
        "app/services/qa.py",
        "app/models/llm.py",
        "app/models/schemas.py",
        "app/core/config.py",
        "app/core/prompts.py",
        "README.md",
    ]

    missing = []

    for dir_path in required_dirs:
        full_path = ROOT / dir_path
        if full_path.exists():
            print(f"  ✅ {dir_path:30} - 存在")
        else:
            print(f"  ❌ {dir_path:30} - 缺失")
            missing.append(dir_path)

    for file_path in required_files:
        full_path = ROOT / file_path
        if full_path.exists():
            print(f"  ✅ {file_path:30} - 存在")
        else:
            print(f"  ❌ {file_path:30} - 缺失")
            missing.append(file_path)

    return len(missing) == 0

def check_old_files():
    """检查旧文件是否已备份"""
    print("\n" + "="*60)
    print("🔍 验证文件备份...")
    print("="*60)

    old_files = ["use_old.py", "llm_old.py", "settings_old.py", "mLLM_old.py"]

    for file_name in old_files:
        file_path = ROOT / file_name
        if file_path.exists():
            print(f"  ✅ {file_name:20} - 已备份")
        else:
            print(f"  ⚠️  {file_name:20} - 未找到（可能未创建）")

    return True

def check_routes():
    """检查 API 路由"""
    print("\n" + "="*60)
    print("🔍 验证 API 路由...")
    print("="*60)

    try:
        from app.main import app

        routes_found = []
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                path = route.path
                methods = list(route.methods) if route.methods else ['GET']
                routes_found.append((methods[0], path))

        expected = [
            ('GET', '/'),
            ('GET', '/health'),
            ('GET', '/ask'),
            ('GET', '/chat'),
        ]

        for method, path in expected:
            if any(p == path for m, p in routes_found):
                print(f"  ✅ {method:6} {path:20} - 已注册")
            else:
                print(f"  ❌ {method:6} {path:20} - 未找到")

        return True
    except Exception as e:
        print(f"  ❌ 路由检查失败: {e}")
        return False

def main():
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*15 + "RAG 项目重构验证脚本" + " "*22 + "║")
    print("╚" + "="*58 + "╝")
    print()

    results = []

    # 执行检查
    results.append(("模块导入", check_imports()))
    results.append(("目录结构", check_structure()))
    results.append(("文件备份", check_old_files()))
    results.append(("API 路由", check_routes()))

    # 总结
    print("\n" + "="*60)
    print("📊 验证总结")
    print("="*60)

    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name:15} {status}")
        if not passed:
            all_passed = False

    print("="*60)

    if all_passed:
        print("\n🎉 恭喜！所有检查通过，重构成功！")
        print("\n📚 下一步:")
        print("  1. 配置 .env 文件（复制 .env.example）")
        print("  2. 运行: unicorn app.main:app --reload --host")
        print("  3. 访问: http://localhost:8000")
        print("  4. 查看文档: README.md 和 QUICKSTART.md")
    else:
        print("\n⚠️ 部分检查未通过，请检查上述错误信息")

    print()

if __name__ == "__main__":
    main()

