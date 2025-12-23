# -*- coding: utf-8 -*-
"""
HTU 教务处栏目爬虫（优化版）
- 起始栏目页：--start https://www.htu.edu.cn/teaching/3251/list.htm
- 递归"下一页"
- 抽取每篇文章，保存 Markdown 原数据 / meta.json / 附件（不解析）
- 统一目录结构：database/<doc_id>/
  - content.md (markdown格式原数据)
  - meta.json (元数据)
  - attachments/ (附件文件夹，如有)
"""
import argparse, os, re, time, json, hashlib, pathlib, datetime, sys
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import trafilatura

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

ATTACH_EXTS = (".pdf",".doc",".docx",".xls",".xlsx",".zip",".rar",".7z",".png",".jpg",".jpeg")

def md5_bytes(b: bytes) -> str:
    return "md5:"+hashlib.md5(b).hexdigest()

def ensure_dir(p: pathlib.Path):
    p.mkdir(parents=True, exist_ok=True)
    return p

def http_get(url, session, timeout=20):
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r

def normalize_date_from_url(url: str):
    """
    解析像 /2025/1105/c3251a360557/page.htm → 2025-11-05
    """
    m = re.search(r"/(\d{4})/(\d{4})/", url)
    if not m:
        return None
    y, md = m.group(1), m.group(2)
    mm, dd = md[:2], md[2:]
    try:
        return str(datetime.date(int(y), int(mm), int(dd)))
    except Exception:
        return None

def make_doc_id(article_url: str, title_text: str) -> str:
    """
    生成稳定 doc_id：HTU_教务处_通知_YYYY-MM-DD_<aid or hash>
    aid 优先取 c3251a360557 中的 360557；否则用 URL md5 后 10 位
    """
    date_str = normalize_date_from_url(article_url) or "unknown"
    m = re.search(r"a(\d+)", article_url)
    tail = m.group(1) if m else hashlib.md5(article_url.encode("utf-8")).hexdigest()[:10]
    # 简单规范化标题
    title_norm = re.sub(r"[\\/:*?\"<>| \t\n]+", "", title_text)[:18] or "文章"
    return f"HTU_教务处_通知_{date_str}_{tail}_{title_norm}"

def extract_article(session, url, out_dir):
    """抓取文章并落盘到统一的database结构"""
    resp = http_get(url, session)
    html = resp.text
    hash_html = md5_bytes(html.encode("utf-8"))
    soup = BeautifulSoup(html, "lxml")

    # 取标题：优先 h1，再次从 <title>
    h1 = soup.select_one("h1")
    title = (h1.get_text(strip=True) if h1 else soup.title.get_text(strip=True) if soup.title else "").strip()
    if not title:
        title = "未命名通知"

    publish_date = normalize_date_from_url(url)

    # 提取 Markdown 格式原数据（保留表格、链接等结构）
    md = trafilatura.extract(
        html,
        include_tables=True,
        include_links=True,
        include_images=True,
        include_formatting=True,
        output_format="markdown"
    )
    md = md or ""

    # 添加标题和元信息到 markdown 顶部
    md_header = f"# {title}\n\n"
    md_header += f"**来源**: {url}\n\n"
    if publish_date:
        md_header += f"**发布日期**: {publish_date}\n\n"
    md_header += "---\n\n"
    md = md_header + md

    # doc_id & 统一路径：database/<doc_id>/
    doc_id = make_doc_id(url, title)
    doc_dir = ensure_dir(pathlib.Path(out_dir)/"database"/doc_id)

    # 下载附件到同文件夹的 attachments/ 子目录
    attachments = []
    attach_found = False
    for a in soup.select("a[href]"):
        href = a.get("href")
        if not href:
            continue
        href_lower = href.lower()
        if not href_lower.endswith(ATTACH_EXTS):
            continue
        file_url = urljoin(url, href)
        try:
            r = http_get(file_url, session)
            # 保留原始文件名
            fname = os.path.basename(urlparse(file_url).path) or "attachment"
            # 确保文件名唯一
            attach_dir = doc_dir/"attachments"
            ensure_dir(attach_dir)
            local_path = attach_dir/fname

            # 处理重名文件
            counter = 1
            base_name, ext = os.path.splitext(fname)
            while local_path.exists():
                local_path = attach_dir/f"{base_name}_{counter}{ext}"
                counter += 1

            with open(local_path, "wb") as f:
                f.write(r.content)

            attach_found = True
            attachments.append({
                "filename": local_path.name,
                "path": f"attachments/{local_path.name}",
                "url": file_url,
                "size": len(r.content),
                "hash": md5_bytes(r.content)
            })
            print(f"    [附件] {local_path.name} ({len(r.content)} bytes)")
        except Exception as e:
            print(f"    [附件失败] {file_url}: {e}", file=sys.stderr)

    # 保存 Markdown 原数据
    (doc_dir/"content.md").write_text(md, encoding="utf-8")

    # 元数据
    meta = {
        "doc_id": doc_id,
        "title": title,
        "source_url": url,
        "dept": "教务处",
        "doc_type": "通知公告",
        "publish_date": publish_date,
        "crawl_date": str(datetime.date.today()),
        "lang": "zh",
        "version": "v2",
        "hash_html": hash_html,
        "has_attachments": attach_found,
        "attachment_count": len(attachments),
        "attachments": attachments
    }
    (doc_dir/"meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return doc_id, title

def parse_list_page(session, url):
    """解析栏目页：返回文章链接列表 + 下一页链接（若有）"""
    resp = http_get(url, session)
    html = resp.text
    soup = BeautifulSoup(html, "lxml")

    # 文章链接：精确匹配文章详情页URL pattern
    # 典型文章 URL 形如 /teaching/2025/1105/c3251a360557/page.htm
    links = []
    for a in soup.select("a[href]"):
        href = a.get("href")
        if not href:
            continue
        # 只匹配相对路径，确保是文章详情页
        if re.match(r'/teaching/\d{4}/\d{4}/c\d+a\d+/page\.htm', href):
            full = urljoin(url, href)
            links.append(full)

    # 下一页：查找包含"下一页"的链接，或匹配list数字递增的链接
    next_link = None
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a.get("href")
        # 方法1: 文本包含"下一页"
        if "下一页" in text or "next" in text.lower():
            next_link = urljoin(url, href)
            break
        # 方法2: 匹配 list2.htm, list3.htm 等（但"下一页"优先）
        if re.search(r'list\d+\.htm$', href):
            if not next_link:  # 只在没找到"下一页"时使用
                next_link = urljoin(url, href)

    # 去重、保持顺序
    seen = set()
    uniq_links = []
    for l in links:
        if l not in seen:
            uniq_links.append(l); seen.add(l)

    return uniq_links, next_link

def load_state(state_path):
    if state_path.exists():
        return json.loads(state_path.read_text(encoding="utf-8"))
    return {"visited_articles": [], "visited_lists": []}

def save_state(state_path, state):
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def crawl(start_url, out_dir, max_pages=50, delay=1.0, force=False):
    out_dir = pathlib.Path(out_dir)
    ensure_dir(out_dir)
    state_path = out_dir/"crawl_state.json"

    if force:
        print("[强制模式] 清除状态，重新爬取所有内容")
        state = {"visited_articles": [], "visited_lists": []}
    else:
        state = load_state(state_path)
        print(f"[继续模式] 已抓取 {len(state['visited_articles'])} 篇文章, {len(state['visited_lists'])} 个栏目页")

    s = requests.Session()
    s.headers.update({"User-Agent": UA})

    list_url = start_url
    pages_done = 0

    while list_url and pages_done < max_pages:
        print(f"[栏目] {list_url}")

        try:
            article_links, next_link = parse_list_page(s, list_url)
            print(f"  找到 {len(article_links)} 篇文章")
        except Exception as e:
            print(f"[栏目失败] {list_url}: {e}", file=sys.stderr)
            break

        # 处理文章链接
        if list_url not in state["visited_lists"]:
            got = 0
            for aurl in article_links:
                if aurl in state["visited_articles"]:
                    print(f"  [跳过已抓] {aurl}")
                    continue
                try:
                    doc_id, title = extract_article(s, aurl, out_dir)
                    print(f"  [OK] {title} → {doc_id}")
                    state["visited_articles"].append(aurl)
                    got += 1
                    time.sleep(delay)
                except Exception as e:
                    print(f"  [文章失败] {aurl}: {e}", file=sys.stderr)

            state["visited_lists"].append(list_url)
            save_state(state_path, state)
            print(f"  本页新增 {got} 篇文章")
        else:
            print(f"  [栏目已抓过，跳过文章提取]")

        # 移动到下一页
        list_url = next_link
        pages_done += 1
        if list_url:
            print(f"  下一页: {list_url}")
            time.sleep(delay)
        else:
            print(f"  没有更多页面")

    print(f"完成：栏目页 {pages_done} 页；文章 {len(state['visited_articles'])} 篇。输出目录：{out_dir}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="栏目起始 URL，如 https://www.htu.edu.cn/teaching/3251/list.htm")
    ap.add_argument("--out", default="./dataset", help="输出根目录（包含 database/ crawl_state.json）")
    ap.add_argument("--max-pages", type=int, default=50, help="最多遍历栏目页数")
    ap.add_argument("--delay", type=float, default=1.0, help="请求间隔秒")
    ap.add_argument("--force", action="store_true", help="强制重新爬取，忽略已有状态")
    args = ap.parse_args()
    # 友情提示：尊重 robots.txt 和网站负载，必要时加大 --delay
    crawl(args.start, args.out, args.max_pages, args.delay, args.force)

if __name__ == "__main__":
    main()
