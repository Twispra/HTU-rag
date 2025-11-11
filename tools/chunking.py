# chunker_htuedu.py
import os, re, json, pathlib
from tqdm import tqdm

STAGING_DIR = "../dataset/staging"
CHUNK_DIR = "../dataset/chunks"
os.makedirs(CHUNK_DIR, exist_ok=True)

def chunk_text(text, size=350, overlap=60):
    """句子优先的滑动窗口切块"""
    sents = re.split(r'(?<=[。！？!?；;])\s*', text)
    chunks, cur, cur_len = [], [], 0
    for s in sents:
        slen = len(s)
        if cur_len + slen > size:
            chunks.append("".join(cur))
            # overlap：取末尾一部分进入下一块
            overlap_text = "".join(cur)[-overlap:]
            cur, cur_len = [overlap_text, s], len(overlap_text) + slen
        else:
            cur.append(s)
            cur_len += slen
    if cur:
        chunks.append("".join(cur))
    return [c.strip() for c in chunks if len(c.strip()) > 30]

all_chunks = []
for docdir in tqdm(list(pathlib.Path(STAGING_DIR).iterdir()), desc="Processing"):
    meta_path = docdir / "meta.json"
    content_path = docdir / "content.md"
    if not meta_path.exists() or not content_path.exists():
        continue
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    text = content_path.read_text(encoding="utf-8")
    title = meta.get("title") or "无标题通知"
    doc_id = meta["doc_id"]

    chunks = chunk_text(text, size=350, overlap=60)
    out_path = pathlib.Path(CHUNK_DIR) / f"{doc_id}.jsonl"

    with open(out_path, "w", encoding="utf-8") as f:
        for i, ck in enumerate(chunks, 1):
            item = {
                "id": f"{doc_id}#p{i}",
                "doc_id": doc_id,
                "titles": [title],
                "text": ck,
                "doc_type": meta.get("doc_type", "通知公告"),
                "dept": meta.get("dept", "教务处"),
                "publish_date": meta.get("publish_date"),
                "source_url": meta.get("source_url"),
                "lang": "zh"
            }
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

print("✅ Chunking 完成，输出目录:", CHUNK_DIR)
