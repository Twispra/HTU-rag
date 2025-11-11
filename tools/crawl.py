# -*- coding: utf-8 -*-
"""
HTU 教务处栏目爬虫（结构化落盘）
- 起始栏目页：--start https://www.htu.edu.cn/teaching/3251/list.htm
- 递归“下一页”
- 抽取每篇文章，保存 HTML / Markdown / meta.json / 附件
- 目录：raw/<doc_id>/..., staging/<doc_id>/...
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

def normalize_date_from_url(url: str) -> str | None:
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
    """抓取文章并落盘"""
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
    # 某些页面正文区域 class 名经常叫 .Article,.article,.v_news_content 等，trafilatura 兜底
    md = trafilatura.extract(html, include_tables=True, include_links=False, output_format="markdown")
    md = md or ""

    # doc_id & 路径
    doc_id = make_doc_id(url, title)
    raw_dir = ensure_dir(pathlib.Path(out_dir)/"raw"/doc_id)
    stg_dir = ensure_dir(pathlib.Path(out_dir)/"staging"/doc_id)

    # 保存 HTML
    (raw_dir/"page.html").write_text(html, encoding="utf-8")

    # 下载附件
    attachments = []
    for a in soup.select("a[href]"):
        href = a.get("href")
        if not href:
            continue
        if not href.lower().endswith(ATTACH_EXTS):
            continue
        file_url = urljoin(url, href)
        try:
            r = http_get(file_url, session)
            fname = os.path.basename(urlparse(file_url).path) or "file"
            local = raw_dir/"assets"/fname
            ensure_dir(local.parent)
            with open(local, "wb") as f:
                f.write(r.content)
            attachments.append({
                "url": file_url,
                "local": str(local),
                "hash": md5_bytes(r.content)
            })
        except Exception as e:
            print(f"[附件失败] {file_url}: {e}", file=sys.stderr)

    # 保存 Markdown
    (stg_dir/"content.md").write_text(md, encoding="utf-8")

    # 元数据
    meta = {
        "doc_id": doc_id,
        "source_url": url,
        "title": title,
        "dept": "教务处",
        "doc_type": "通知公告",
        "publish_date": publish_date,
        "crawl_date": str(datetime.date.today()),
        "lang": "zh",
        "version": "v1",
        "hash_html": hash_html,
        "attachments": attachments
    }
    (stg_dir/"meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return doc_id, title

def parse_list_page(session, url):
    """解析栏目页：返回文章链接列表 + 下一页链接（若有）"""
    resp = http_get(url, session)
    html = resp.text
    soup = BeautifulSoup(html, "lxml")

    # 文章链接（常见在 .list 或 ul li a；尽量广一些，但限定域 /teaching/）
    links = []
    for a in soup.select("a[href]"):
        href = a.get("href")
        if not href:
            continue
        full = urljoin(url, href)
        # 典型文章 URL 形如 /teaching/2025/1105/c3251a360557/page.htm
        if re.search(r"/teaching/\d{4}/\d{4}/c\d+a\d+/", full):
            links.append(full)

    # 下一页：文本含“下一页”或 rel=next
    next_link = None
    a_next = soup.find("a", string=re.compile(r"下一页|下页|下一页»|next", re.I)) or soup.find("a", rel=lambda v: v and "next" in v.lower())
    if a_next and a_next.get("href"):
        next_link = urljoin(url, a_next.get("href"))

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

def crawl(start_url, out_dir, max_pages=50, delay=1.0):
    out_dir = pathlib.Path(out_dir)
    ensure_dir(out_dir)
    state_path = out_dir/"crawl_state.json"
    state = load_state(state_path)

    s = requests.Session()
    s.headers.update({"User-Agent": UA})

    list_url = start_url
    pages_done = 0

    while list_url and pages_done < max_pages:
        if list_url in state["visited_lists"]:
            print(f"[跳过栏目已抓] {list_url}")
        else:
            print(f"[栏目] {list_url}")
            try:
                article_links, next_link = parse_list_page(s, list_url)
            except Exception as e:
                print(f"[栏目失败] {list_url}: {e}", file=sys.stderr)
                break

            got = 0
            for aurl in article_links:
                if aurl in state["visited_articles"]:
                    # 也可以做变更检测：拉页面 md5 对比后重跑
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
            list_url = next_link
            pages_done += 1
            time.sleep(delay)
            continue

        # 如果这页已抓过，仍尝试找下一页
        try:
            _, next_link = parse_list_page(s, list_url)
        except Exception:
            next_link = None
        list_url = next_link
        pages_done += 1
        time.sleep(delay)

    print(f"完成：栏目页 {pages_done} 页；文章 {len(state['visited_articles'])} 篇。输出目录：{out_dir}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, help="栏目起始 URL，如 https://www.htu.edu.cn/teaching/3251/list.htm")
    ap.add_argument("--out", default="./dataset", help="输出根目录（包含 raw/ staging/）")
    ap.add_argument("--max-pages", type=int, default=50, help="最多遍历栏目页数")
    ap.add_argument("--delay", type=float, default=1.0, help="请求间隔秒")
    args = ap.parse_args()
    # 友情提示：尊重 robots.txt 和网站负载，必要时加大 --delay
    crawl(args.start, args.out, args.max_pages, args.delay)

if __name__ == "__main__":
    main()
