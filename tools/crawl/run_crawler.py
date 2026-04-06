# -*- coding: utf-8 -*-
"""
Crawler launcher.

Examples:
    python tools/crawl/run_crawler.py
    python tools/crawl/run_crawler.py --force
    python tools/crawl/run_crawler.py --max-pages 5 --delay 0.5
"""
import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
CRAWL_SCRIPT = SCRIPT_DIR / "crawl.py"

DEFAULT_START_URL = "https://www.htu.edu.cn/teaching/3251/list.htm"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "dataset"
DEFAULT_MAX_PAGES = 100
DEFAULT_DELAY = 1.0
DEFAULT_STOP_AFTER_KNOWN_PAGES = 3


def build_command(args: argparse.Namespace):
    command = [
        sys.executable,
        str(CRAWL_SCRIPT),
        "--start",
        args.start,
        "--out",
        str(Path(args.out).expanduser().resolve()),
        "--max-pages",
        str(args.max_pages),
        "--delay",
        str(args.delay),
        "--stop-after-known-pages",
        str(args.stop_after_known_pages),
    ]

    if args.force:
        command.append("--force")
    if args.refresh_known:
        command.append("--refresh-known")

    return command


def main():
    parser = argparse.ArgumentParser(description="Run HTU crawler with stable paths.")
    parser.add_argument("--start", default=DEFAULT_START_URL, help="列表起始 URL")
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUTPUT_DIR),
        help="dataset 输出目录",
    )
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES, help="最多抓取列表页数")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="请求间隔秒数")
    parser.add_argument("--force", action="store_true", help="强制重新抓取")
    parser.add_argument(
        "--refresh-known",
        action="store_true",
        help="刷新已记录文章，适合同 URL 内容有更新时使用",
    )
    parser.add_argument(
        "--stop-after-known-pages",
        type=int,
        default=DEFAULT_STOP_AFTER_KNOWN_PAGES,
        help="增量模式下连续多少个列表页无新增后停止；0 表示不提前停止",
    )
    args = parser.parse_args()

    command = build_command(args)

    print(f"\n开始爬取：{args.start}")
    print(f"输出目录：{Path(args.out).expanduser().resolve()}")
    print(f"最多列表页：{args.max_pages}")
    print(f"请求间隔：{args.delay} 秒")
    print(f"强制模式：{'是' if args.force else '否'}")
    print(f"刷新已知文章：{'是' if args.refresh_known else '否'}")
    print(f"无新增提前停止页数：{args.stop_after_known_pages}")
    print(f"\n执行命令：{' '.join(command)}")
    print("=" * 60)

    try:
        subprocess.run(command, check=True, cwd=str(PROJECT_ROOT))
    except subprocess.CalledProcessError as exc:
        print(f"\n执行失败，退出码: {exc.returncode}")
        print("请确认当前 Python 环境已安装项目依赖，并使用项目对应的虚拟环境运行。")
        sys.exit(exc.returncode)


if __name__ == "__main__":
    main()
