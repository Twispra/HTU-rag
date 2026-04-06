# -*- coding: utf-8 -*-
from __future__ import annotations
"""
HTU 教务通知爬虫

- 抓取列表页中的通知文章
- 将文章落盘到 dataset/database/<doc_id>/
- 支持断点续跑与增量更新
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import shutil
import sys
import time
from urllib.parse import urljoin, urlparse

try:
    import requests
    import trafilatura
    from bs4 import BeautifulSoup
except ModuleNotFoundError as exc:
    requests = None
    trafilatura = None
    BeautifulSoup = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)

ATTACH_EXTS = (
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".zip",
    ".rar",
    ".7z",
    ".png",
    ".jpg",
    ".jpeg",
)

ARTICLE_PATH_RE = re.compile(r"^/teaching/\d{4}/\d{4}/c\d+a\d+/page\.htm$")
LIST_PATH_RE = re.compile(r"^/teaching/\d+/list(?:\d+)?\.htm$")

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_START_URL = "https://www.htu.edu.cn/teaching/3251/list.htm"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "dataset"
DEFAULT_STOP_AFTER_KNOWN_PAGES = 3


def ensure_runtime_dependencies():
    if IMPORT_ERROR is not None:
        raise SystemExit(
            f"缺少依赖: {IMPORT_ERROR.name}。请先在当前 Python 环境安装项目依赖，例如 `pip install -r requirements.txt`。"
        )


def md5_bytes(data: bytes) -> str:
    return "md5:" + hashlib.md5(data).hexdigest()


def ensure_dir(path: pathlib.Path) -> pathlib.Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def http_get(url: str, session: requests.Session, timeout: int = 20) -> requests.Response:
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or "utf-8"
    return response


def normalize_date_from_url(url: str):
    """
    解析类似 /2025/1105/c3251a360557/page.htm -> 2025-11-05
    """
    match = re.search(r"/(\d{4})/(\d{4})/", url)
    if not match:
        return None

    year, month_day = match.group(1), match.group(2)
    month, day = month_day[:2], month_day[2:]
    try:
        return str(datetime.date(int(year), int(month), int(day)))
    except ValueError:
        return None


def make_doc_id(article_url: str, title_text: str) -> str:
    """
    生成稳定 doc_id:
    HTU_教务处_通知_YYYY-MM-DD_<article_id_or_hash>_<title_prefix>
    """
    date_str = normalize_date_from_url(article_url) or "unknown"
    article_match = re.search(r"a(\d+)", article_url)
    tail = (
        article_match.group(1)
        if article_match
        else hashlib.md5(article_url.encode("utf-8")).hexdigest()[:10]
    )
    title_norm = re.sub(r'[\\/:*?"<>| \t\r\n]+', "", title_text)[:18] or "文章"
    return f"HTU_教务处_通知_{date_str}_{tail}_{title_norm}"


def _reset_attachment_dir(doc_dir: pathlib.Path) -> pathlib.Path:
    attach_dir = doc_dir / "attachments"
    if attach_dir.exists():
        shutil.rmtree(attach_dir)
    return attach_dir


def extract_article(session: requests.Session, url: str, out_dir: pathlib.Path):
    """抓取文章并保存到统一的 database 目录结构。"""
    ensure_runtime_dependencies()
    response = http_get(url, session)
    html = response.text
    html_hash = md5_bytes(html.encode("utf-8"))
    soup = BeautifulSoup(html, "lxml")

    h1 = soup.select_one("h1")
    title = (
        h1.get_text(strip=True)
        if h1
        else soup.title.get_text(strip=True)
        if soup.title
        else ""
    ).strip()
    if not title:
        title = "未命名通知"

    publish_date = normalize_date_from_url(url)

    markdown = trafilatura.extract(
        html,
        include_tables=True,
        include_links=True,
        include_images=True,
        include_formatting=True,
        output_format="markdown",
    )
    markdown = markdown or ""

    markdown_header = f"# {title}\n\n"
    markdown_header += f"**来源**: {url}\n\n"
    if publish_date:
        markdown_header += f"**发布日期**: {publish_date}\n\n"
    markdown_header += "---\n\n"
    markdown = markdown_header + markdown

    doc_id = make_doc_id(url, title)
    doc_dir = ensure_dir(out_dir / "database" / doc_id)
    attach_dir = _reset_attachment_dir(doc_dir)

    attachments = []
    for anchor in soup.select("a[href]"):
        href = (anchor.get("href") or "").strip()
        if not href:
            continue

        file_url = urljoin(url, href)
        file_path = urlparse(file_url).path.lower()
        if not file_path.endswith(ATTACH_EXTS):
            continue

        try:
            file_response = http_get(file_url, session)
            ensure_dir(attach_dir)

            filename = os.path.basename(urlparse(file_url).path) or "attachment"
            local_path = attach_dir / filename

            counter = 1
            base_name, ext = os.path.splitext(filename)
            while local_path.exists():
                local_path = attach_dir / f"{base_name}_{counter}{ext}"
                counter += 1

            with open(local_path, "wb") as file_handle:
                file_handle.write(file_response.content)

            attachments.append(
                {
                    "filename": local_path.name,
                    "path": f"attachments/{local_path.name}",
                    "url": file_url,
                    "size": len(file_response.content),
                    "hash": md5_bytes(file_response.content),
                }
            )
            print(f"    [附件] {local_path.name} ({len(file_response.content)} bytes)")
        except Exception as exc:  # pragma: no cover - 网络波动时保留容错
            print(f"    [附件失败] {file_url}: {exc}", file=sys.stderr)

    (doc_dir / "content.md").write_text(markdown, encoding="utf-8")

    metadata = {
        "doc_id": doc_id,
        "title": title,
        "source_url": url,
        "dept": "教务处",
        "doc_type": "通知公告",
        "publish_date": publish_date,
        "crawl_date": str(datetime.date.today()),
        "lang": "zh",
        "version": "v2",
        "hash_html": html_hash,
        "has_attachments": bool(attachments),
        "attachment_count": len(attachments),
        "attachments": attachments,
    }
    (doc_dir / "meta.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return doc_id, title


def _list_page_number(url: str) -> int:
    path = urlparse(url).path
    match = re.search(r"/list(\d+)\.htm$", path)
    if match:
        return int(match.group(1))
    if path.endswith("/list.htm"):
        return 1
    return 0


def parse_list_page(session: requests.Session, url: str):
    """解析栏目页，返回文章链接列表和下一页链接。"""
    ensure_runtime_dependencies()
    response = http_get(url, session)
    soup = BeautifulSoup(response.text, "lxml")

    article_links = []
    next_link = None
    pagination_candidates = []

    for anchor in soup.select("a[href]"):
        href = (anchor.get("href") or "").strip()
        if not href or href.lower().startswith("javascript:"):
            continue

        full_url = urljoin(url, href)
        path = urlparse(full_url).path
        text = anchor.get_text(" ", strip=True)

        if ARTICLE_PATH_RE.match(path):
            article_links.append(full_url)
            continue

        if LIST_PATH_RE.match(path) and full_url != url:
            pagination_candidates.append(full_url)
            if "下一页" in text or "next" in text.lower():
                next_link = full_url

    seen = set()
    deduped_articles = []
    for article_url in article_links:
        if article_url not in seen:
            seen.add(article_url)
            deduped_articles.append(article_url)

    if not next_link and pagination_candidates:
        current_page = _list_page_number(url)
        future_pages = sorted(
            {candidate for candidate in pagination_candidates if _list_page_number(candidate) > current_page},
            key=_list_page_number,
        )
        if future_pages:
            next_link = future_pages[0]

    return deduped_articles, next_link


def build_default_state() -> dict:
    return {
        "state_version": 2,
        "visited_articles": [],
        "visited_lists": [],
        "last_run_at": None,
    }


def normalize_state(raw_state: dict) -> dict:
    state = build_default_state()
    state.update(raw_state or {})
    state["visited_articles"] = list(dict.fromkeys(state.get("visited_articles", [])))
    state["visited_lists"] = list(dict.fromkeys(state.get("visited_lists", [])))
    return state


def load_state(state_path: pathlib.Path) -> dict:
    if not state_path.exists():
        return build_default_state()
    return normalize_state(json.loads(state_path.read_text(encoding="utf-8")))


def save_state(state_path: pathlib.Path, state: dict):
    normalized_state = normalize_state(state)
    state_path.write_text(
        json.dumps(normalized_state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def crawl(
    start_url: str,
    out_dir,
    max_pages: int = 50,
    delay: float = 1.0,
    force: bool = False,
    refresh_known: bool = False,
    stop_after_known_pages: int = DEFAULT_STOP_AFTER_KNOWN_PAGES,
):
    ensure_runtime_dependencies()
    out_dir = ensure_dir(pathlib.Path(out_dir).expanduser().resolve())
    state_path = out_dir / "crawl_state.json"

    if force:
        print("[强制模式] 重置状态并重新抓取。")
        state = build_default_state()
    else:
        state = load_state(state_path)
        print(
            "[增量模式] 已记录文章 "
            f"{len(state['visited_articles'])} 篇，已扫描列表页 {len(state['visited_lists'])} 个。"
        )

    visited_articles = set(state["visited_articles"])
    seen_lists_this_run = set()

    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    list_url = start_url
    pages_done = 0
    total_new = 0
    total_refreshed = 0
    consecutive_pages_without_changes = 0

    while list_url and pages_done < max_pages:
        if list_url in seen_lists_this_run:
            print(f"[停止] 本轮已访问过列表页，疑似进入循环：{list_url}")
            break

        seen_lists_this_run.add(list_url)
        print(f"[列表] {list_url}")

        try:
            article_links, next_link = parse_list_page(session, list_url)
            print(f"  找到 {len(article_links)} 篇文章")
        except Exception as exc:
            print(f"[列表失败] {list_url}: {exc}", file=sys.stderr)
            break

        page_new = 0
        page_refreshed = 0

        for article_url in article_links:
            already_seen = article_url in visited_articles
            should_fetch = force or refresh_known or not already_seen

            if not should_fetch:
                print(f"  [跳过已抓取] {article_url}")
                continue

            try:
                doc_id, title = extract_article(session, article_url, out_dir)
                if already_seen:
                    page_refreshed += 1
                    print(f"  [刷新] {title} -> {doc_id}")
                else:
                    visited_articles.add(article_url)
                    state["visited_articles"].append(article_url)
                    page_new += 1
                    print(f"  [新增] {title} -> {doc_id}")
                time.sleep(delay)
            except Exception as exc:
                print(f"  [文章失败] {article_url}: {exc}", file=sys.stderr)

        if list_url not in state["visited_lists"]:
            state["visited_lists"].append(list_url)

        state["last_run_at"] = datetime.datetime.now().isoformat(timespec="seconds")
        save_state(state_path, state)

        total_new += page_new
        total_refreshed += page_refreshed

        if page_new == 0 and page_refreshed == 0:
            consecutive_pages_without_changes += 1
        else:
            consecutive_pages_without_changes = 0

        print(f"  本页新增 {page_new} 篇，刷新 {page_refreshed} 篇")

        pages_done += 1
        if (
            not force
            and not refresh_known
            and stop_after_known_pages > 0
            and consecutive_pages_without_changes >= stop_after_known_pages
        ):
            print(
                f"  连续 {stop_after_known_pages} 个列表页无新增文章，提前结束增量抓取。"
            )
            break

        list_url = next_link
        if list_url:
            print(f"  下一页 -> {list_url}")
            time.sleep(delay)
        else:
            print("  没有更多页面")

    print(
        "完成："
        f" 列表页 {pages_done} 个；新增文章 {total_new} 篇；"
        f" 刷新文章 {total_refreshed} 篇；输出目录：{out_dir}"
    )


def main():
    parser = argparse.ArgumentParser(description="HTU 教务通知爬虫")
    parser.add_argument("--start", default=DEFAULT_START_URL, help="列表起始 URL")
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUTPUT_DIR),
        help="输出根目录（包含 database/ 与 crawl_state.json）",
    )
    parser.add_argument("--max-pages", type=int, default=50, help="最多遍历多少个列表页")
    parser.add_argument("--delay", type=float, default=1.0, help="请求间隔秒数")
    parser.add_argument("--force", action="store_true", help="忽略已有状态，重新抓取")
    parser.add_argument(
        "--refresh-known",
        action="store_true",
        help="重新抓取已记录文章，用于刷新同 URL 的内容或附件",
    )
    parser.add_argument(
        "--stop-after-known-pages",
        type=int,
        default=DEFAULT_STOP_AFTER_KNOWN_PAGES,
        help="增量模式下连续多少个列表页无变化后停止；0 表示不提前停止",
    )
    args = parser.parse_args()

    crawl(
        start_url=args.start,
        out_dir=args.out,
        max_pages=args.max_pages,
        delay=args.delay,
        force=args.force,
        refresh_known=args.refresh_known,
        stop_after_known_pages=args.stop_after_known_pages,
    )


if __name__ == "__main__":
    main()
