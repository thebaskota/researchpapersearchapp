#!/usr/bin/env python3

import os
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import math

IN_DIR = Path("out_main/json")
OUT_DIR = Path("out_main/employee")

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # author -> { skill -> set(doc_ids) }
    author_skills = defaultdict(lambda: defaultdict(set))
    author_projects = defaultdict(set)

    for file_path in IN_DIR.glob("*.json"):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        doc_id = data.get("id")
        front = data.get("front", {})

        authors = front.get("authors", [])
        keywords = front.get("keywords", [])
        categories = front.get("categories", [])

        # combine skills
        skills = set(keywords + categories)

        for author in authors:
            author_projects[author].add(doc_id)

            for skill in skills:
                author_skills[author][skill].add(doc_id)

    # build profiles
    for author, skills_map in author_skills.items():
        employee_id = f"E{abs(hash(author)) % 100000}"  # simple stable-ish ID
        project_count = len(author_projects[author])

        top_skills = []

        for skill, doc_ids in skills_map.items():
            doc_count = len(doc_ids)
            score = round(math.log1p(doc_count), 2)

            top_skills.append({
                "skill": skill,
                "doc_count": doc_count,
                "recent_count": 0,     # not implemented yet
                "score": score
            })

        # sort by doc_count descending
        top_skills.sort(key=lambda x: x["doc_count"], reverse=True)

        profile = {
            "employee_id": employee_id,
            "name": author,
            "project_count": project_count,
            "top_skills": top_skills,
            "last_updated": datetime.now().date().isoformat()
        }

        out_file = OUT_DIR / f"{employee_id}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2, ensure_ascii=False)

    print("Profiles generated.")

if __name__ == "__main__":
    main()
