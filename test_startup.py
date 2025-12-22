# -*- coding: utf-8 -*-
"""测试服务启动"""
import sys
sys.path.insert(0, '.')

print("="*60)
print("测试服务启动...")
print("="*60)

try:
    print("\n1. 导入配置...")
    from app.core.config import Settings
    settings = Settings()
    print(f"   ✅ 配置加载成功")
    print(f"   - LLM Provider: {settings.llm_provider}")
    print(f"   - LLM Model: {settings.llm_model}")

    print("\n2. 导入应用...")
    from app.main import app
    print("   ✅ 应用导入成功")

    print("\n3. 检查路由...")
    routes = [r for r in app.routes if hasattr(r, 'path')]
    print(f"   ✅ 共 {len(routes)} 个路由")
    for route in routes[:5]:  # 只显示前5个
        if hasattr(route, 'methods') and route.methods:
            method = list(route.methods)[0]
        else:
            method = "GET"
        print(f"      {method:6} {route.path}")

    print("\n" + "="*60)
    print("✅ 所有测试通过！服务可以正常启动。")
    print("="*60)
    print("\n启动命令:")
    print("  uvicorn app.main:app --reload --port 8000")


except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

