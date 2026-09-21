"use client";

import { useState } from "react";
import { ArrowRight, Check } from "lucide-react";
import { lessons, lessonById, type LessonProgress } from "../lib/course";
import { planSession } from "../lib/study-session";

export default function SessionPicker({
  rows,
  now,
  completionSerials,
  disabled,
  onChoose,
}: {
  rows: LessonProgress[];
  now: number;
  completionSerials: Record<string, number>;
  disabled: boolean;
  onChoose: (id: string, restart: boolean) => void;
}) {
  const [size, setSize] = useState(4);
  const [session, setSession] = useState<ReturnType<typeof planSession> | null>(
    null,
  );
  const [initialSerials, setInitialSerials] = useState<Record<string, number>>(
    {},
  );
  const preview = planSession(lessons, rows, now, size);
  const finished = (id: string) =>
    (completionSerials[id] ?? 0) > (initialSerials[id] ?? 0);
  const remaining = session?.ids.filter((id) => !finished(id)) ?? [];
  const next = remaining[0];
  function start() {
    const selected = preview;
    setSession(selected);
    setInitialSerials({ ...completionSerials });
    if (selected.ids[0])
      onChoose(selected.ids[0], selected.reviewIds.includes(selected.ids[0]));
  }
  return (
    <details className="session-picker">
      <summary>按自己的节奏 · 一次一小组</summary>
      <p className="muted">
        先安排待巩固和到期复习，空余位置最多加入 4
        关新课。复习多时，这组先不加新课。
      </p>
      <div className="listening-actions" role="group" aria-label="每组关数">
        {[4, 8, 12].map((n) => (
          <button
            className={"button " + (size === n ? "primary" : "")}
            key={n}
            aria-pressed={size === n}
            disabled={!!session && remaining.length > 0}
            onClick={() => setSize(n)}
          >
            {n} 关一组
          </button>
        ))}
      </div>
      {session ? (
        <>
          <p className="line-note" role="status">
            <Check size={15} />
            本组已完成 {session.ids.length - remaining.length} /{" "}
            {session.ids.length} 关。
            {!remaining.length
              ? "可以休息了；有余力再开始下一组。"
              : "中途可以休息，学习记录已按关保存。"}
          </p>
          {next ? (
            <button
              className="button primary"
              disabled={disabled}
              onClick={() => onChoose(next, session.reviewIds.includes(next))}
            >
              继续本组：{lessonById.get(next)?.title}
              <ArrowRight size={16} />
            </button>
          ) : (
            <button
              className="button"
              disabled={disabled || !preview.ids.length}
              onClick={start}
            >
              开始下一组
            </button>
          )}
          <button
            className="button subtle"
            disabled={disabled}
            onClick={() => setSession(null)}
          >
            结束本组
          </button>
        </>
      ) : (
        <>
          <p className="line-note">
            本组：{preview.reviewIds.length} 关复习 + {preview.newIds.length}{" "}
            关新课。
            {preview.remainingReviews > 0
              ? `另有 ${preview.remainingReviews} 关待复习，可以分组完成。`
              : ""}
          </p>
          <button
            className="button"
            disabled={disabled || !preview.ids.length}
            onClick={start}
          >
            {preview.ids.length ? "开始这一组" : "目前没有待学或到期的内容"}
          </button>
        </>
      )}
      <p className="coverage-note">
        分组用于控制本次练习量，刷新后可重新分组；各关云端进度不受影响。
      </p>
    </details>
  );
}
