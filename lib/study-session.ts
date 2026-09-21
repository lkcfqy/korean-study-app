import type { LessonMeta, LessonProgress } from "./course";

export type StudySession = {
  ids: string[];
  reviewIds: string[];
  resumeIds: string[];
  newIds: string[];
  dueCount: number;
  remainingReviews: number;
};

// One small session, not a claim about daily mastery or a fixed 180-day deadline.
export function planSession(
  lessons: Pick<LessonMeta, "id">[],
  rows: LessonProgress[],
  now: number,
  size = 4,
): StudySession {
  const limit = Math.max(1, Math.min(12, Math.floor(size) || 4));
  const known = new Set(lessons.map((l) => l.id));
  const due = rows
    .filter(
      (r) =>
        known.has(r.lesson_id) &&
        (r.review_step < 0 ||
          (r.next_review_at !== null && r.next_review_at <= now)),
    )
    .sort(
      (a, b) =>
        a.review_step - b.review_step ||
        (a.next_review_at ?? 0) - (b.next_review_at ?? 0) ||
        a.lesson_id.localeCompare(b.lesson_id),
    );
  const reviewIds = [...new Set(due.map((r) => r.lesson_id))].slice(0, limit);
  const completed = new Set(
    rows.filter((r) => r.completed_at !== null).map((r) => r.lesson_id),
  );
  const selected = new Set(reviewIds);
  const resumeIds = rows
    .filter((r) =>
      known.has(r.lesson_id) &&
      r.completed_at === null &&
      !selected.has(r.lesson_id) &&
      (r.cursor > 0 || r.read_mask !== 0 || r.draft.trim().length > 0),
    )
    .sort((a, b) => b.updated_at - a.updated_at || a.lesson_id.localeCompare(b.lesson_id))
    .map((r) => r.lesson_id)
    .filter((id, index, ids) => ids.indexOf(id) === index)
    .slice(0, limit - reviewIds.length);
  resumeIds.forEach((id) => selected.add(id));
  const newIds = lessons
    .filter((l) => !completed.has(l.id) && !selected.has(l.id))
    .slice(0, Math.min(4, limit - reviewIds.length - resumeIds.length))
    .map((l) => l.id);
  return {
    ids: [...reviewIds, ...resumeIds, ...newIds],
    reviewIds,
    resumeIds,
    newIds,
    dueCount: due.length,
    remainingReviews: Math.max(0, due.length - reviewIds.length),
  };
}

export function searchLessons<
  T extends Pick<LessonMeta, "id" | "title" | "day">,
>(lessons: T[], query: string) {
  const terms = query
    .normalize("NFKC")
    .trim()
    .toLocaleLowerCase()
    .split(/\s+/)
    .filter(Boolean);
  if (!terms.length) return [];
  return lessons.filter((l) =>
    terms.every((term) =>
      `${l.id} ${l.title}`.normalize("NFKC").toLocaleLowerCase().includes(term),
    ),
  );
}
