#!/usr/bin/env python3
"""Count personally reviewed lessons whose current course bytes still match the ledger.

This checks bookkeeping only. It never judges Korean, Chinese, or pronunciation.
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "content/course-index.json"
LEDGER = ROOT / "docs/independent-review-20260923.jsonl"


def main() -> None:
    lessons = json.loads(INDEX.read_text())["lessons"]
    by_id = {lesson["id"]: lesson for lesson in lessons}
    rows = [json.loads(line) for line in LEDGER.read_text().splitlines() if line.strip()]
    seen: set[str] = set()
    current = []
    stale = []
    for row in rows:
        lesson_id = row["lessonId"]
        if lesson_id in seen:
            raise SystemExit(f"duplicate reviewed lesson: {lesson_id}")
        seen.add(lesson_id)
        if lesson_id not in by_id:
            raise SystemExit(f"unknown reviewed lesson: {lesson_id}")
        raw = (ROOT / "public/course" / f"{lesson_id}.json").read_bytes()
        lesson = json.loads(raw)
        counts = {
            "lines": len(lesson["lines"]),
            "parts": sum(len(line["parts"]) for line in lesson["lines"]),
            "words": sum(len(line.get("words", [])) for line in lesson["lines"]),
            "questions": len(lesson["questions"]),
        }
        if row["sha256"] != hashlib.sha256(raw).hexdigest() or row["counts"] != counts:
            stale.append(lesson_id)
        else:
            current.append(row)
    totals = {key: sum(row["counts"][key] for row in current) for key in ("lines", "parts", "words", "questions")}
    print(json.dumps({
        "currentReviewedLessons": len(current),
        "totalLessons": len(lessons),
        "remainingLessons": len(lessons) - len(current),
        "currentReviewedItemCounts": totals,
        "staleReviews": stale,
        "complete": len(current) == len(lessons) and not stale,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
