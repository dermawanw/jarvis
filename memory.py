import os, datetime
import chromadb, ollama
from chromadb.api.types import Metadata

VAULT = r"C:\Users\Mr.R\Documents\JARVIS MEMORY"   # sesuaikan
EMBED = "nomic-embed-text"

db = chromadb.PersistentClient(path="./memory_db")
col = db.get_or_create_collection("notes")

def _embed(texts):
    return ollama.embed(model=EMBED, input=texts)["embeddings"]

def _chunks(text, size=800):
    parts, buf = [], ""
    for para in text.split("\n\n"):
        if len(buf) + len(para) > size and buf:
            parts.append(buf.strip()); buf = ""
        buf += para + "\n\n"
    if buf.strip():
        parts.append(buf.strip())
    return parts

def index_vault():
    n = 0
    for root, _, files in os.walk(VAULT):
        if ".obsidian" in root:
            continue
        for f in files:
            if not f.endswith(".md"):
                continue
            path = os.path.join(root, f)
            rel = os.path.relpath(path, VAULT)
            with open(path, encoding="utf-8") as fh:
                chunks = _chunks(fh.read())
            if not chunks:
                continue
            col.delete(where={"source": rel})          # buang versi lama
            col.add(
                ids=[f"{rel}#{i}" for i in range(len(chunks))],
                documents=chunks,
                embeddings=_embed(chunks),
                metadatas=[{"source": rel}] * len(chunks),
            )
            n += len(chunks)
    return n

def search(query, k=4):
    if col.count() == 0:
        return []
    r = col.query(query_embeddings=_embed([query]), n_results=min(k, col.count()))
    return list(zip(r["documents"][0], [m["source"] for m in r["metadatas"][0]]))

def save_note(text):
    folder = os.path.join(VAULT, "Daily Notes")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{datetime.date.today()}.md")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"- {datetime.datetime.now():%H:%M} {text}\n")
    index_vault()
    return path