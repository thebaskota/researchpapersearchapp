#!/usr/bin/env python3
import json
from pathlib import Path
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

IN_DIR = Path("out_main/json")
PERSIST_DIR = Path("out_main/chroma")
COLLECTION_NAME = "projects"

def make_embedding_text(doc: dict) -> str:
    front = doc.get("front", {}) or {}
    title = front.get("title") or ""
    abstract = front.get("abstract") or ""
    keywords = front.get("keywords") or []
    categories = front.get("categories") or []

    # minimal, consistent text blob
    parts = []
    if title:
        parts.append(f"Title: {title}")
    if abstract:
        parts.append(f"Abstract: {abstract}")
    if keywords:
        parts.append("Keywords: " + ", ".join(map(str, keywords)))
    if categories:
        parts.append("Categories: " + ", ".join(map(str, categories)))

    return "\n".join(parts).strip()

def main():
    if not IN_DIR.exists():
        raise SystemExit(f"Missing input folder: {IN_DIR}")

    # Embedding model (small + fast, good for PoC)
    embed_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

    client = chromadb.PersistentClient(path=str(PERSIST_DIR))

    # cosine distance is better for text embeddings
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )

    ids, docs, metas = [], [], []

    for p in sorted(IN_DIR.glob("*.json")):
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)

        doc_id = data.get("id")
        if not doc_id:
            continue

        front = data.get("front", {}) or {}
        fileinfo = data.get("file", {}) or {}

        text = make_embedding_text(data)
        if not text:
            continue

        metadata = {
            "filename": fileinfo.get("filename") or "",
            "path": fileinfo.get("path") or "",
            "modified_time": fileinfo.get("modified_time") or "",
            "year": str(front.get("year")) if front.get("year") is not None else "",
            # store authors as a JSON string to keep it simple
            "authors_json": json.dumps(front.get("authors") or [], ensure_ascii=False),
            "title": front.get("title") or "",
        }

        ids.append(doc_id)
        docs.append(text)
        metas.append(metadata)

    if not ids:
        raise SystemExit("No documents to index (check your JSON files).")

    # Minimal approach: delete and rebuild each time (safe for PoC)
    # If you want incremental updates later, we’ll add upsert logic.
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )

    # Add in batches (kept minimal)
    BATCH = 256
    for i in range(0, len(ids), BATCH):
        collection.add(
            ids=ids[i:i+BATCH],
            documents=docs[i:i+BATCH],
            metadatas=metas[i:i+BATCH],
        )

    # Log metadata to JSON file
    log_data = [
        {"id": doc_id, "metadata": meta}
        for doc_id, meta in zip(ids, metas)
    ]
    log_file = Path(PERSIST_DIR).parent / "metadata_log.json"
    with log_file.open("w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)

    print(f"Indexed {len(ids)} projects into {PERSIST_DIR}/{COLLECTION_NAME}")
    print(f"Metadata logged to {log_file}")

if __name__ == "__main__":
    main()
