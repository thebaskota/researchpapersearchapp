#!/usr/bin/env python3
"""
PDF → single-stage LLM extraction (front matter only) using Ollama (Llama 3.2 3B).

Input:
  data/*.pdf

Output:
  out/json/<paper_id>.json          (merged result)
  out/logs/<paper_id>_raw.json      (raw LLM response + prompt for debugging)
  out/index.jsonl                   (one-line summary per PDF)

Requires:
  pip install pymupdf requests
  Ollama running:  ollama serve
  Model pulled:    ollama pull llama3.2:3b
"""

import os
import re
import json
import time
import glob
import hashlib
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple, List

import fitz  # PyMuPDF
import requests


# ----------------------------
# Config
# ----------------------------

DATA_GLOB = "data/*.pdf"

OUT_DIR = "out"
OUT_JSON_DIR = os.path.join(OUT_DIR, "json")
OUT_LOG_DIR = os.path.join(OUT_DIR, "logs")
OUT_INDEX = os.path.join(OUT_DIR, "index.jsonl")

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2:3b"

# Page strategy
FRONT_PAGES_DEFAULT = 2        # first 2 pages
FRONT_PAGES_FALLBACK = 4       # if no abstract/keywords signal

# Text limits per call (keep CPU runtime tolerable)
MAX_CHARS_FRONT = 2000

# Ollama call behavior
TIMEOUT_SECS = 600
MAX_RETRIES = 2
RETRY_SLEEP_SECS = 2.0

# Prompt
PROMPT_FRONT = """You extract structured metadata from the FIRST pages of an academic/technical paper.
Return ONLY valid JSON. No markdown. No explanations.

Schema:
{{
  "title": string|null,
  "authors": string[],
  "year": integer|null,
  "abstract": string|null,
  "keywords": string[],
  "categories": string[]
}}

Rules:
- If a field is missing, use null (or [] for arrays).
- "keywords" should be 3-12 short phrases.
- "categories" should be 2-8 broad areas (e.g., "NLP", "Information Retrieval", "Databases").
- "authors" should be best-effort names only (no affiliations).

TEXT:
{TEXT}
"""


# ----------------------------
# Helpers
# ----------------------------

def ensure_dirs() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(OUT_JSON_DIR, exist_ok=True)
    os.makedirs(OUT_LOG_DIR, exist_ok=True)


def sha1_file(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_pages_text(doc: fitz.Document, page_indices: List[int], max_chars: int) -> str:
    parts: List[str] = []
    for i in page_indices:
        if 0 <= i < doc.page_count:
            t = (doc.load_page(i).get_text("text") or "").strip()
            if t:
                parts.append(t)
    text = "\n\n".join(parts).strip()
    return text[:max_chars]


def has_front_signal(text: str) -> bool:
    t = (text or "").lower()
    # word-boundary checks reduce random matches
    return (
        re.search(r"\babstract\b", t) is not None
        or re.search(r"\bkeywords?\b", t) is not None
        or re.search(r"\bindex terms\b", t) is not None
    )


@dataclass
class PaperSlices:
    front_text: str
    page_count: int


def slice_front(pdf_path: str) -> PaperSlices:
    doc = fitz.open(pdf_path)
    n = doc.page_count

    front_n = min(FRONT_PAGES_DEFAULT, n)
    front_text = extract_pages_text(doc, list(range(0, front_n)), MAX_CHARS_FRONT)

    if not has_front_signal(front_text) and n > front_n:
        front_n2 = min(FRONT_PAGES_FALLBACK, n)
        front_text = extract_pages_text(doc, list(range(0, front_n2)), MAX_CHARS_FRONT)

    doc.close()
    return PaperSlices(front_text=front_text, page_count=n)


def ollama_generate(prompt: str) -> str:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0}
    }
    r = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT_SECS)
    r.raise_for_status()
    return (r.json().get("response") or "").strip()


def parse_json_strictish(text: str) -> Dict[str, Any]:
    """
    Try strict JSON first; if it fails, extract the first {...} block.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("Empty model response.")

    # 1) strict
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2) fallback: first object block
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"No JSON object found in model response. Response was: {text[:250]}")
    json_str = m.group(0)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"JSON parsing failed: {e}\nFirst 500 chars of extracted JSON:\n{json_str[:500]}"
        )


def call_llm_json(prompt_template: str, text_block: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    prompt = prompt_template.replace("{TEXT}", text_block or "")
    last_err: Optional[str] = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            raw = ollama_generate(prompt)
            parsed = parse_json_strictish(raw)
            return parsed, {"prompt": prompt, "raw_response": raw, "attempt": attempt}
        except Exception as e:
            last_err = str(e)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_SLEEP_SECS * (attempt + 1))
            else:
                return {"error": last_err}, {
                    "prompt": prompt,
                    "raw_response": None,
                    "attempt": attempt,
                    "error": last_err
                }


def normalize_list(x) -> List[str]:
    if not isinstance(x, list):
        return []
    out: List[str] = []
    for v in x:
        if isinstance(v, str):
            s = v.strip()
            if s:
                out.append(s)
    return out


def safe_int(x) -> Optional[int]:
    if isinstance(x, int):
        return x
    if isinstance(x, str):
        m = re.search(r"\b(19|20)\d{2}\b", x)
        if m:
            try:
                return int(m.group(0))
            except Exception:
                return None
    return None


def postprocess_front(front: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": front.get("title") if isinstance(front.get("title"), str) else None,
        "authors": normalize_list(front.get("authors")),
        "year": safe_int(front.get("year")),
        "abstract": front.get("abstract") if isinstance(front.get("abstract"), str) else None,
        "keywords": normalize_list(front.get("keywords")),
        "categories": normalize_list(front.get("categories")),
        "error": front.get("error"),
    }


def process_pdf(pdf_path: str) -> Dict[str, Any]:
    paper_id = sha1_file(pdf_path)
    stat = os.stat(pdf_path)

    slices = slice_front(pdf_path)

    print("    Extracting front matter...")
    front_parsed, front_log = call_llm_json(PROMPT_FRONT, slices.front_text)

    merged = {
        "id": paper_id,
        "file": {
            "path": pdf_path,
            "filename": os.path.basename(pdf_path),
            "size_bytes": stat.st_size,
            "modified_time": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(stat.st_mtime)),
        },
        "pdf": {
            "page_count": slices.page_count
        },
        "slices_info": {
            "front_pages_default": FRONT_PAGES_DEFAULT,
            "front_pages_fallback": FRONT_PAGES_FALLBACK,
            "front_chars": len(slices.front_text or ""),
        },
        "front": postprocess_front(front_parsed),
    }

    raw_log = {
        "id": paper_id,
        "file": merged["file"],
        "slices_info": merged["slices_info"],
        "llm_calls": {"front": front_log},
    }

    out_json_path = os.path.join(OUT_JSON_DIR, f"{paper_id}.json")
    out_log_path = os.path.join(OUT_LOG_DIR, f"{paper_id}_raw.json")

    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    with open(out_log_path, "w", encoding="utf-8") as f:
        json.dump(raw_log, f, ensure_ascii=False, indent=2)

    index_row = {
        "id": paper_id,
        "filename": merged["file"]["filename"],
        "title": merged["front"]["title"],
        "year": merged["front"]["year"],
        "authors_n": len(merged["front"]["authors"] or []),
        "front_chars": merged["slices_info"]["front_chars"],
        "errors": {"front": merged["front"].get("error")},
    }
    with open(OUT_INDEX, "a", encoding="utf-8") as f:
        f.write(json.dumps(index_row, ensure_ascii=False) + "\n")

    return merged


def main() -> None:
    ensure_dirs()
    pdfs = sorted(glob.glob(DATA_GLOB))
    if not pdfs:
        print(f"No PDFs found at: {DATA_GLOB}")
        return

    # Fresh run
    if os.path.exists(OUT_INDEX):
        os.remove(OUT_INDEX)

    print(f"Found {len(pdfs)} PDFs.")
    for i, pdf_path in enumerate(pdfs, 1):
        print(f"[{i}/{len(pdfs)}] Processing: {os.path.basename(pdf_path)}")
        try:
            merged = process_pdf(pdf_path)
            title = merged["front"].get("title") or ""
            print(f"  -> OK | title: {title[:90]}")
        except Exception as e:
            import traceback
            print(f"  -> FAILED: {e}")
            if i == 1:
                print("Full error details for first failure:")
                traceback.print_exc()

    print("Done. Outputs:")
    print(f"  - {OUT_JSON_DIR}/<id>.json")
    print(f"  - {OUT_LOG_DIR}/<id>_raw.json")
    print(f"  - {OUT_INDEX}")


if __name__ == "__main__":
    main()
