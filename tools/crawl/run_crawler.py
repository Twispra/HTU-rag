# -*- coding: utf-8 -*-
"""
快速启动爬虫脚本
用法：
    python run_crawler.py          # 继续爬取（断点续传）
    python run_crawler.py --force  # 强制重新爬取
"""
import sys
import subprocess

# 配置参数
START_URL = "https://www.htu.edu.cn/teaching/3251/list.htm"
OUTPUT_DIR = "../../dataset"
MAX_PAGES = 100  # 最多爬取100页
DELAY = 1.0      # 请求间隔1秒

# 构建命令
cmd = [
    "python", "crawl.py",
    "--start", START_URL,
    "--out", OUTPUT_DIR,
    "--max-pages", str(MAX_PAGES),
    "--delay", str(DELAY)
]

# 检查是否有--force参数
if "--force" in sys.argv or "-f" in sys.argv:
    cmd.append("--force")
    print("🔄 强制模式：将清除已有状态，重新爬取所有内容")
else:
    print("⏩ 继续模式：将从上次中断处继续爬取")

print(f"\n📡 开始爬取：{START_URL}")
print(f"📁 输出目录：{OUTPUT_DIR}")
print(f"📄 最多爬取：{MAX_PAGES} 页")
print(f"⏱️  请求间隔：{DELAY} 秒")
print(f"\n执行命令：{' '.join(cmd)}\n")
print("="*60)

# 运行爬虫
subprocess.run(cmd)

