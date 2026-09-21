import type { Progress, LessonProgress } from "./course";

export type ProgressDelta = {
  kind: "delta";
  row: LessonProgress;
  currentLesson: string;
  serverTime: number;
  counts: Progress["counts"];
};

export function mergeProgress(
  previous: Progress,
  delta: ProgressDelta,
): Progress {
  // Response sequence is guarded by the caller. Never replace other lessons with
  // a one-row delta; a full GET remains authoritative after a device switch.
  const rows = previous.rows.filter(
    (row) => row.lesson_id !== delta.row.lesson_id,
  );
  rows.push(delta.row);
  rows.sort(
    (a, b) =>
      b.updated_at - a.updated_at || b.lesson_id.localeCompare(a.lesson_id),
  );
  return {
    rows,
    currentLesson: delta.currentLesson,
    serverTime: delta.serverTime,
    counts: delta.counts,
  };
}
