#!/usr/bin/env python3
import json
import sys
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from collections import defaultdict
from pathlib import Path

PERSIST_DIR = Path("out_main/chroma")
COLLECTION_NAME = "projects"

def main():
    if len(sys.argv) < 2:
        print('Usage: python query.py "your project description" [top_k]')
        raise SystemExit(1)

    query_text = sys.argv[1]
    top_k = int(sys.argv[2]) if len(sys.argv) >= 3 else 10

    embed_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path=str(PERSIST_DIR))

    collection = client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=embed_fn,
    )

    res = collection.query(
        query_texts=[query_text],
        n_results=top_k,
        include=["metadatas", "documents", "distances"],
    )

    ids = res["ids"][0]
    metas = res["metadatas"][0]
    dists = res["distances"][0]  # with cosine space: dist ≈ (1 - cosine_similarity)

    print("\nTop similar projects:\n")
    employee_scores = defaultdict(float)
    employee_evidence = defaultdict(list)

    for rank, (doc_id, md, dist) in enumerate(zip(ids, metas, dists), start=1):
        # Convert distance -> similarity score in [~0..1]
        sim = 1.0 - float(dist)

        title = md.get("title", "")
        filename = md.get("filename", "")
        authors = json.loads(md.get("authors_json", "[]"))

        print(f"{rank:>2}. sim={sim:.3f}  doc_id={doc_id}  file={filename}")
        if title:
            print(f"    title: {title}")
        if authors:
            print(f"    authors: {', '.join(authors)}")

        # Rank employees by summed similarity from matched projects
        for a in authors:
            employee_scores[a] += sim
            employee_evidence[a].append({"doc_id": doc_id, "sim": round(sim, 3)})

    ranked = sorted(employee_scores.items(), key=lambda x: x[1], reverse=True)

    print("\nTop employees (by summed similarity):\n")
    for i, (name, score) in enumerate(ranked[:10], start=1):
        evidence = employee_evidence[name][:3]  # show first 3
        print(f"{i:>2}. score={score:.3f}  {name}  evidence={evidence}")

if __name__ == "__main__":
    main()
