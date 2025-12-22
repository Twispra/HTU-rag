# build_index.py
import os
from sentence_transformers import SentenceTransformer
import numpy as np, faiss, json, pathlib, tqdm


CHUNK_DIR = "../dataset/chunks"
INDEX_DIR = "../dataset/index"
os.makedirs(INDEX_DIR, exist_ok=True)

model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
embeddings, metas = [], []

for file in tqdm.tqdm(list(pathlib.Path(CHUNK_DIR).glob("*.jsonl")), desc="Embedding"):
    with open(file, encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            txt = " ".join(d["titles"]) + " " + d["text"]
            emb = model.encode(txt, normalize_embeddings=True)
            embeddings.append(emb)
            metas.append(d)

X = np.array(embeddings, dtype="float32")
index = faiss.IndexFlatIP(X.shape[1])
index.add(X)
faiss.write_index(index, f"{INDEX_DIR}/faiss.index")

with open(f"{INDEX_DIR}/meta.jsonl", "w", encoding="utf-8") as f:
    for m in metas:
        f.write(json.dumps(m, ensure_ascii=False) + "\n")

print("✅ 向量索引已创建，共", len(metas), "条 chunk")
