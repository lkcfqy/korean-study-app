"use client";
import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  ArrowRight,
  Cloud,
  CloudOff,
  Volume2,
  BookOpen,
  ChevronLeft,
  Check,
  RotateCcw,
  X,
  LoaderCircle,
  Pause,
} from "lucide-react";
import {
  lessons,
  lessonById,
  lessonSchema,
  stages,
  totalWords,
  totalSentences,
  progressSchema,
  progressDeltaSchema,
  errorSchema,
  type Progress,
  type Word,
  type Lesson,
} from "../lib/course";
import hangul from "../content/hangul.json";
import firstLesson from "../content/first-lesson.json";
import SentenceReader from "./sentence-reader";
import ListeningCheck from "./listening-check";
import RecallCheck from "./recall-check";
import SessionPicker from "./session-picker";
import { searchLessons } from "../lib/study-session";
import { mergeProgress } from "../lib/merge-progress";
import {
  hasContrastQuestions,
  independentAnswers,
  type ListeningCheck as ListeningAttempt,
} from "../lib/listening-check";
import PlanBoundary from "./plan-boundary";
import { reviewSourceDays } from "../lib/review-plan";
import { learningError } from "../lib/learning-error";
import { AudioPlayback } from "../lib/audio-playback";
const StudyPlan = lazy(() => import("./study-plan"));

type Props = { signedIn: boolean; signInHref: string };
type Panel = "lessons" | "plan" | "hangul" | null;
type ToolContext = {
  registerTool: (
    tool: {
      name: string;
      description: string;
      inputSchema: object;
      annotations: { readOnlyHint: boolean };
      execute: (input: unknown) => unknown;
    },
    options: { signal: AbortSignal },
  ) => void | Promise<void>;
};
const empty: Progress = {
  rows: [],
  currentLesson: "c01",
  serverTime: 0,
  counts: { sentences: 0, words: 0, completed: 0 },
};
export default function LearningApp({ signedIn, signInHref }: Props) {
  const [progress, setProgress] = useState<Progress>(empty);
  const [loaded, setLoaded] = useState(!signedIn);
  const [ready, setReady] = useState(!signedIn);
  const [clockTime, setClockTime] = useState(0);
  const [lessonId, setLessonId] = useState("c01");
  const [cursor, setCursor] = useState(0);
  const [lesson, setLesson] = useState<Lesson>(firstLesson);
  const [contentBusy, setContentBusy] = useState(false);
  const contentRequest = useRef(0);
  const lessonCache = useRef(new Map<string, Lesson>([["c01", firstLesson]]));
  const [search, setSearch] = useState("");
  const [completionSerials, setCompletionSerials] = useState<
    Record<string, number>
  >({});
  const [courseMonth, setCourseMonth] = useState(0);
  const [courseDay, setCourseDay] = useState(1);
  const [meaning, setMeaning] = useState(true);
  const [word, setWord] = useState<Word | null>(null);
  const [panel, setPanel] = useState<Panel>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const [error, setError] = useState("");
  const [failedLesson, setFailedLesson] = useState<{
    id: string;
    restart: boolean;
  } | null>(null);
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);
  const progressRequest = useRef(0);
  const selecting = useRef(false);
  const focusLesson = useRef(false);
  const lessonHeading = useRef<HTMLHeadingElement>(null);
  const [sync, setSync] = useState(
    signedIn ? "正在读取进度" : "登录后同步进度",
  );
  const [audioError, setAudioError] = useState("");
  const [playing, setPlaying] = useState(false);
  const [audioLoading, setAudioLoading] = useState(false);
  const [rate, setRate] = useState(1);
  const audio = useRef<AudioPlayback | null>(null);
  const [done, setDone] = useState(false);
  const [usedStudyHelp, setUsedStudyHelp] = useState(false);
  const [checkResult, setCheckResult] = useState<number | null>(null);
  const [checkMode, setCheckMode] = useState<"choice" | "recall">("choice");
  const [draft, setDraft] = useState("");
  const [draftRevision, setDraftRevision] = useState(0);
  const [draftSaved, setDraftSaved] = useState(false);
  const initialised = useRef(false);
  const draftTouched = useRef(false);
  const index = Math.max(
    0,
    lessons.findIndex((l) => l.id === lessonId),
  );
  const line = lesson.lines[Math.min(cursor, lesson.lines.length - 1)];
  const record = progress.rows.find((r) => r.lesson_id === lessonId);
  const isQuiz = cursor >= lesson.lines.length && !done;
  const practice = progress.rows.filter((r) => r.review_step < 0);
  const reviewQueue = progress.rows
    .filter(
      (r) =>
        r.review_step < 0 ||
        (r.next_review_at !== null &&
          r.next_review_at <= Math.max(progress.serverTime, clockTime)),
    )
    .sort(
      (a, b) =>
        a.review_step - b.review_step ||
        (a.next_review_at ?? 0) - (b.next_review_at ?? 0),
    );
  const counts = progress.counts;
  const completedIds = useMemo(
    () =>
      new Set(
        progress.rows
          .filter((r) => r.completed_at !== null)
          .map((r) => r.lesson_id),
      ),
    [progress.rows],
  );
  const stopAudio = useCallback(() => {
    audio.current?.stop();
  }, []);
  const fetchLesson = useCallback(async (id: string) => {
    const meta = lessonById.get(id);
    if (!meta) throw new Error("这段对话不存在。");
    const cached = lessonCache.current.get(id);
    if (cached) return cached;
    const response = await fetch(
      `/course/${encodeURIComponent(id)}.json?v=${meta.revision}`,
      { signal: AbortSignal.timeout(20000) },
    );
    if (!response.ok) throw new Error("对话加载失败，请再试一次。");
    const value = lessonSchema.parse(await response.json());
    if (value.id !== id || value.lines.length !== meta.lineCount)
      throw new Error("课程版本不一致，请刷新页面。");
    if (lessonCache.current.size >= 12)
      lessonCache.current.delete(lessonCache.current.keys().next().value!);
    lessonCache.current.set(id, value);
    return value;
  }, []);
  const changeView = useCallback(
    async (p: Progress, id: string, restart = false) => {
      const request = ++contentRequest.current;
      setContentBusy(true);
      try {
        const next = await fetchLesson(id);
        if (request !== contentRequest.current) return;
        const row = p.rows.find((r) => r.lesson_id === id);
        setLesson(next);
        setLessonId(id);
        setCursor(restart ? 0 : Math.min(row?.cursor ?? 0, next.lines.length));
        setDone(
          !restart &&
            !!row?.completed_at &&
            (row?.cursor ?? 0) >= next.lines.length,
        );
        setUsedStudyHelp(false);
        setCheckResult(null);
        setWord(null);
        setDraft(row?.draft ?? "");
        setDraftRevision(row?.draft_revision ?? 0);
        draftTouched.current = false;
        setDraftSaved(false);
        setAudioError("");
        setError("");
        setFailedLesson(null);
        stopAudio();
      } finally {
        if (request === contentRequest.current) setContentBusy(false);
      }
    },
    [fetchLesson, stopAudio],
  );
  const load = useCallback(
    async (restore = false) => {
      if (!signedIn || inFlight.current || selecting.current) return;
      const request = ++progressRequest.current;
      try {
        const response = await fetch("/api/progress", {
          cache: "no-store",
          signal: AbortSignal.timeout(15000),
        });
        const raw = await response.json();
        if (request !== progressRequest.current || inFlight.current) return;
        if (!response.ok) throw new Error(errorSchema.parse(raw).error);
        const data = progressSchema.parse(raw);
        setProgress(data);
        setSync("进度已存云端");
        setError("");
        setLoaded(true);
        if (restore || !initialised.current) {
          await changeView(
            data,
            lessonById.has(data.currentLesson) ? data.currentLesson : "c01",
          );
          initialised.current = true;
          setReady(true);
        }
      } catch (e) {
        if (request !== progressRequest.current) return;
        setLoaded(true);
        setSync("暂未连接云端");
        setError(learningError(e, "读取失败，请重试。"));
      }
    },
    [signedIn, changeView],
  );
  useEffect(() => {
    const initialLoad = window.setTimeout(() => void load(), 0);
    const refresh = () => {
      if (document.visibilityState === "visible" && !inFlight.current)
        void load();
    };
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      window.clearTimeout(initialLoad);
      window.removeEventListener("focus", refresh);
      document.removeEventListener("visibilitychange", refresh);
      audio.current?.stop();
    };
  }, [load]);
  useEffect(() => {
    const tick = () => setClockTime(Date.now());
    const timer = window.setInterval(tick, 60000);
    window.addEventListener("focus", tick);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", tick);
    };
  }, []);
  useEffect(() => {
    const beforeLeave = (event: BeforeUnloadEvent) => {
      if (draftTouched.current) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", beforeLeave);
    return () => window.removeEventListener("beforeunload", beforeLeave);
  }, []);
  useEffect(() => {
    if (panel && !dialog.current?.open) dialog.current?.showModal();
    if (!panel && dialog.current?.open) dialog.current?.close();
  }, [panel]);
  useEffect(() => {
    if (!panel && focusLesson.current) {
      focusLesson.current = false;
      lessonHeading.current?.focus({ preventScroll: true });
      lessonHeading.current?.scrollIntoView({ block: "start" });
    }
  }, [panel, lessonId]);
  const mutate = async (
    body: Record<string, unknown>,
  ): Promise<Progress | null> => {
    if (inFlight.current) return null;
    inFlight.current = true;
    progressRequest.current++;
    setBusy(true);
    setError("");
    setSync("正在保存…");
    try {
      const response = await fetch("/api/progress?response=delta", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(15000),
      });
      const raw = await response.json();
      if (!response.ok) {
        const failure = errorSchema.parse(raw);
        if (failure.progress) setProgress(failure.progress);
        throw new Error(failure.error);
      }
      const data = mergeProgress(progress, progressDeltaSchema.parse(raw));
      setProgress(data);
      setSync("进度已存云端");
      return data;
    } catch (e) {
      setSync("这一步尚未保存");
      setError(learningError(e, "保存失败，请再次点击重试。"));
      return null;
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  };
  const play = async (
    path: string,
    onFinished?: (completed: boolean) => void,
  ) => {
    if (!audio.current)
      audio.current = new AudioPlayback((state) => {
        setPlaying(state.phase === "playing");
        setAudioLoading(state.phase === "loading");
        setAudioError(
          state.phase === "error"
            ? state.reason === "timeout"
              ? "音频加载时间较长，请重试，或使用韩文提示继续练习。"
              : state.reason === "load"
                ? "音频未能加载，请重试，或使用韩文提示继续练习。"
                : "播放未成功，请再次点击播放，或使用韩文提示。"
            : "",
        );
      });
    await audio.current.play(path, rate, onFinished);
  };
  const chooseLesson = async (id: string, restart = false) => {
    if (selecting.current || contentBusy || inFlight.current) return;
    selecting.current = true;
    progressRequest.current++;
    setFailedLesson(null);
    setError("");
    try {
      setContentBusy(true);
      await fetchLesson(id);
      if (!signedIn) {
        await changeView(empty, id, restart);
        focusLesson.current = true;
        setPanel(null);
        setMeaning(!restart);
        return;
      }
      if (draftTouched.current && lesson.stage === 5) {
        const saved = await mutate({
          action: "draft",
          lessonId,
          text: draft,
          revision: draftRevision,
        });
        if (!saved) return;
        setDraftRevision(
          saved.rows.find((r) => r.lesson_id === lessonId)?.draft_revision ??
            draftRevision,
        );
        draftTouched.current = false;
      }
      stopAudio();
      const p = await mutate({ action: "select", lessonId: id, restart });
      if (p) {
        await changeView(p, id, restart);
        focusLesson.current = true;
        setPanel(null);
        setMeaning(!restart);
      } else setFailedLesson({ id, restart });
    } catch (e) {
      setFailedLesson({ id, restart });
      setError(learningError(e, "对话加载失败，请重试。"));
    } finally {
      selecting.current = false;
      setContentBusy(false);
    }
  };
  const nextLine = async () => {
    if (!signedIn) {
      stopAudio();
      setCursor(cursor + 1);
      setWord(null);
      return;
    }
    const p = await mutate({ action: "read", lessonId, lineIndex: cursor });
    if (p) {
      stopAudio();
      setCursor(cursor + 1);
      setWord(null);
      setAudioError("");
    }
  };
  const complete = async (answers: number[], check: ListeningAttempt) => {
    const result = independentAnswers(
      check,
      lesson.questions.map((q) => q.answer),
    );
    setCheckMode(check.mode === "recall" ? "recall" : "choice");
    if (!signedIn) {
      stopAudio();
      setCheckResult(result);
      setDone(true);
      setCompletionSerials((previous) => ({
        ...previous,
        [lessonId]: (previous[lessonId] ?? 0) + 1,
      }));
      return;
    }
    const p = await mutate({ action: "complete", lessonId, answers, check });
    if (p) {
      stopAudio();
      setCheckResult(result);
      setDone(true);
      setCompletionSerials((previous) => ({
        ...previous,
        [lessonId]: (previous[lessonId] ?? 0) + 1,
      }));
    }
  };
  const saveDraft = async () => {
    const p = await mutate({
      action: "draft",
      lessonId,
      text: draft,
      revision: draftRevision,
    });
    if (p) {
      setDraftRevision(
        p.rows.find((r) => r.lesson_id === lessonId)?.draft_revision ??
          draftRevision,
      );
      draftTouched.current = false;
      setDraftSaved(true);
    }
  };
  const readCloudDraft = async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    ++progressRequest.current;
    setBusy(true);
    setSync("正在读取云端回复");
    try {
      const response = await fetch("/api/progress", {
        cache: "no-store",
        signal: AbortSignal.timeout(15000),
      });
      const raw = await response.json();
      if (!response.ok) throw new Error(errorSchema.parse(raw).error);
      const data = progressSchema.parse(raw);
      const cloud = data.rows.find((row) => row.lesson_id === lessonId);
      setProgress(data);
      setDraft(cloud?.draft ?? "");
      setDraftRevision(cloud?.draft_revision ?? 0);
      draftTouched.current = false;
      setDraftSaved(true);
      setError("");
      setSync("已读取云端回复");
    } catch (e) {
      setSync("暂未连接云端");
      setError(learningError(e, "读取失败，输入框中的文字仍保留，请重试。"));
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  };
  const stateRef = useRef({ lesson, progress, cursor });
  useEffect(() => {
    stateRef.current = { lesson, progress, cursor };
  }, [lesson, progress, cursor]);
  useEffect(() => {
    const context = (document as Document & { modelContext?: ToolContext })
      .modelContext;
    if (!context?.registerTool) return;
    const controller = new AbortController();
    const register = async () => {
      try {
        await context.registerTool(
          {
            name: "read_korean_learning_progress",
            description:
              "Read the visible course, current dialogue, cloud learning counts, and available lessons without changing study progress.",
            inputSchema: {
              type: "object",
              properties: {},
              additionalProperties: false,
            },
            annotations: { readOnlyHint: true },
            execute(input) {
              if (
                input === null ||
                typeof input !== "object" ||
                Array.isArray(input) ||
                Object.keys(input).length
              )
                throw new Error("Expected an empty object");
              const s = stateRef.current;
              return {
                lessonId: s.lesson.id,
                title: s.lesson.title,
                line: s.cursor + 1,
                counts: s.progress.counts,
                completed: s.progress.rows
                  .filter((r) => r.completed_at)
                  .map((r) => r.lesson_id),
              };
            },
          },
          { signal: controller.signal },
        );
      } catch (e) {
        console.warn("WebMCP unavailable", e);
      }
    };
    void register();
    return () => controller.abort();
  }, []);
  const disabled = busy || contentBusy || !loaded || !ready;
  const coursePlan = useMemo(() => {
    const lessonIds = lessons
      .filter((l) => l.day === courseDay)
      .map((l) => l.id);
    const reviewLessonIds = [
      ...new Set(
        reviewSourceDays(courseDay).flatMap((days) =>
          lessons.filter((l) => days.includes(l.day)).map((l) => l.id),
        ),
      ),
    ];
    return { lessonIds, reviewLessonIds };
  }, [courseDay]);
  const searchResults = useMemo(() => searchLessons(lessons, search), [search]);
  const visibleLessonIds = search.trim()
    ? searchResults.slice(0, 80).map((l) => l.id)
    : coursePlan.lessonIds.length
      ? coursePlan.lessonIds
      : coursePlan.reviewLessonIds;
  const PracticeCheck = hasContrastQuestions(lesson.id)
    ? ListeningCheck
    : RecallCheck;
  return (
    <>
      <a className="skip-link" href="#lesson-content">
        跳到当前对话
      </a>
      <header className="topbar">
        <div className="brand">
          <span className="mark" aria-hidden="true">
            한
          </span>
          <strong>
            한걸음 <small>一句一步</small>
          </strong>
        </div>
        {signedIn ? (
          <span className="sync" role="status">
            {busy ? (
              <LoaderCircle size={17} className="spin" />
            ) : error ? (
              <CloudOff size={17} />
            ) : (
              <Cloud size={17} />
            )}
            <span>{sync}</span>
          </span>
        ) : (
          <a className="button" href={signInHref} target="_top">
            <Cloud size={17} />
            登录同步
          </a>
        )}
      </header>
      <main className="workspace">
        <aside className="sidebar">
          <p className="eyebrow">YOUR KOREAN JOURNEY</p>
          <h2>从一句你好开始</h2>
          {stages.map((s, i) => (
            <button
              key={s}
              className={"stage " + (lesson.stage === i ? "active" : "")}
              onClick={() => {
                setCourseMonth(i);
                setCourseDay(i * 30 + 1);
                setSearch("");
                setPanel("lessons");
              }}
            >
              <span className="stage-index">{i + 1}</span>
              <span>{s}</span>
              {lessons
                .filter((l) => l.stage === i)
                .every((l) => completedIds.has(l.id)) && <Check size={14} />}
            </button>
          ))}
          <button className="button subtle" onClick={() => setPanel("hangul")}>
            <BookOpen size={17} />
            不会读？先认韩文
          </button>
          <div className="sidebar-foot">
            <p>按自己的节奏 · 先复习再加量</p>
            <button className="text-link" onClick={() => setPanel("plan")}>
              查看 180 天学习安排
            </button>
            <p className="small-note">
              {lessons.length.toLocaleString()} 关 · 自由选择
              <br />
              {totalWords} 去重词条 · {totalSentences} 条去重对话
            </p>
            {reviewQueue.length > 0 && (
              <button
                className="button"
                disabled={disabled}
                onClick={() =>
                  void chooseLesson(reviewQueue[0].lesson_id, true)
                }
              >
                <RotateCcw size={15} />
                复习与巩固 · {reviewQueue.length}
              </button>
            )}
          </div>
        </aside>
        <section
          id="lesson-content"
          className="learning"
          aria-labelledby="lesson-title"
        >
          <div className="lesson-heading">
            <div>
              <p className="eyebrow">
                CHAPTER {String(lesson.stage + 1).padStart(2, "0")} /{" "}
                {stages[lesson.stage]}
              </p>
              <h1 id="lesson-title" ref={lessonHeading} tabIndex={-1}>
                {lesson.title}
              </h1>
            </div>
            <button
              className="pill course-pill"
              onClick={() => {
                setCourseMonth(lesson.stage);
                setCourseDay(
                  lessonById.get(lessonId)?.day ?? lesson.stage * 30 + 1,
                );
                setSearch("");
                setPanel("lessons");
              }}
            >
              第 {index + 1} / {lessons.length} 关 <BookOpen size={14} />
            </button>
          </div>
          <div className="mobile-tools">
            <button className="text-link" onClick={() => setPanel("hangul")}>
              韩文拼读
            </button>
            <button className="text-link" onClick={() => setPanel("plan")}>
              180 天安排
            </button>
            {reviewQueue.length > 0 && (
              <button
                className="text-link"
                disabled={disabled}
                onClick={() =>
                  void chooseLesson(reviewQueue[0].lesson_id, true)
                }
              >
                复习 · {reviewQueue.length}
              </button>
            )}
          </div>
          {signedIn && (
            <SessionPicker
              rows={progress.rows}
              now={Math.max(progress.serverTime, clockTime)}
              completionSerials={completionSerials}
              disabled={disabled}
              onChoose={(id, restart) => void chooseLesson(id, restart)}
            />
          )}
          <div
            className="progress-track"
            role="progressbar"
            aria-label="本关对话进度"
            aria-valuenow={Math.min(cursor, lesson.lines.length)}
            aria-valuemin={0}
            aria-valuemax={lesson.lines.length}
          >
            <div
              className="progress-fill"
              style={{
                width:
                  Math.min(100, (cursor / lesson.lines.length) * 100) + "%",
              }}
            />
          </div>
          {!signedIn && (
            <div className="info-banner">
              所有对话均可自由试学。登录后自动保存进度，手机、电脑可接着学。
              <a href={signInHref} target="_top">
                登录并开始
              </a>
            </div>
          )}
          {signedIn && practice.length > 0 && !done && (
            <div className="info-banner">
              有 {practice.length} 关需要巩固。先复习，再按自己的节奏学新课。
              <button
                className="text-link"
                disabled={disabled}
                onClick={() =>
                  void chooseLesson(reviewQueue[0].lesson_id, true)
                }
              >
                复习一关
              </button>
            </div>
          )}
          {contentBusy && (
            <p role="status" className="muted">
              正在加载对话…
            </p>
          )}
          {error && (
            <div className="error-state" role="alert">
              {error}{" "}
              <button
                className="text-link"
                disabled={busy || contentBusy}
                onClick={() =>
                  failedLesson
                    ? void chooseLesson(failedLesson.id, failedLesson.restart)
                    : signedIn
                      ? void load()
                      : setError("")
                }
              >
                {failedLesson
                  ? "重新打开对话"
                  : signedIn
                    ? "重新连接"
                    : "关闭提示"}
              </button>
            </div>
          )}
          <div className="dialogue-card">
            <div className="scene-head">
              <strong>{lesson.scene}</strong>
              <span>
                {done
                  ? "本关完成"
                  : isQuiz
                    ? hasContrastQuestions(lesson.id)
                      ? "听懂了吗？"
                      : "试着回忆"
                    : `${cursor + 1} / ${lesson.lines.length}`}
              </span>
            </div>
            {done ? (
              <div className="dialogue-body">
                <div className="success-icon">
                  <Check size={27} />
                </div>
                <h2>
                  {checkResult === null
                    ? "这段对话已经练习过了。"
                    : checkMode === "recall"
                      ? "回忆练习完成。"
                      : checkResult === 2
                        ? "两句都首次独立答对。"
                        : "练习完成，再巩固一次。"}
                </h2>
                {checkResult !== null && (
                  <p className="line-note">
                    {checkMode === "recall"
                      ? "自评无提示回忆一致"
                      : "首次独立答对"}{" "}
                    {checkResult} / 2 句。
                    {checkMode === "recall"
                      ? "这是自评结果，用于安排复习，不是客观听力得分。"
                      : ""}
                    {checkResult < 2
                      ? checkMode === "recall"
                        ? "有遗漏或使用提示，建议先做短间隔复习。"
                        : "有答错或使用提示，建议先做短间隔复习。"
                      : "下次不看提示再试，检查是否记住。"}
                  </p>
                )}
                <p className="translation" style={{ marginTop: 12 }}>
                  {signedIn
                    ? "这段对话已经完成，学习进度已保存在云端。"
                    : "这段对话已完成试学。登录后可以把学习进度保存在云端。"}
                </p>
                {signedIn && (
                  <p className="line-note">
                    {record?.review_step === -1 ? "待巩固 · " : ""}下次复习：
                    {record?.next_review_at
                      ? new Date(record.next_review_at).toLocaleDateString(
                          "zh-CN",
                          { month: "long", day: "numeric" },
                        )
                      : "明天"}
                    。复习会沿用同一段对话。
                  </p>
                )}
                <div className="completion-actions">
                  {index < lessons.length - 1 ? (
                    <button
                      className="button primary"
                      disabled={disabled}
                      onClick={() => void chooseLesson(lessons[index + 1].id)}
                    >
                      进入下一关
                      <ArrowRight size={17} />
                    </button>
                  ) : (
                    <button
                      className="button primary"
                      onClick={() => setPanel("plan")}
                    >
                      查看 180 天学习安排
                    </button>
                  )}
                  <button
                    className="button"
                    disabled={disabled}
                    onClick={() => void chooseLesson(lessonId, true)}
                  >
                    <RotateCcw size={17} />
                    再练一遍
                  </button>
                </div>
                {checkResult !== null && checkResult < 2 && (
                  <p className="line-note">
                    今天可以先停在这里。把这一关重新听懂后，再继续新课。
                  </p>
                )}
                {index === lessons.length - 1 && (
                  <p className="line-note">
                    这是最后一关。你可以自由回到其他关卡，也可以结合 180
                    天安排扩展输入。
                  </p>
                )}
              </div>
            ) : isQuiz ? (
              <PracticeCheck
                key={lesson.id}
                lesson={lesson}
                busy={disabled}
                usedStudyHelp={usedStudyHelp}
                onListen={play}
                onStop={stopAudio}
                onBack={() => {
                  setUsedStudyHelp(true);
                  setCursor(0);
                  setMeaning(true);
                  setAudioError("");
                }}
                onComplete={complete}
              />
            ) : (
              <>
                <div className="dialogue-body">
                  <div className="speaker">
                    <span className="avatar" aria-hidden="true">
                      {line.speakerIndex === 0 ? "가" : "나"}
                    </span>
                    {lesson.roles[line.speakerIndex]}
                    <span className="speaker-voice">SunHi</span>
                  </div>
                  <SentenceReader
                    key={line.id}
                    line={line}
                    meaning={meaning}
                    onListen={() => void play(line.audio)}
                    onListenWord={(path) => void play(path)}
                  />
                </div>
                <div className="card-controls">
                  <div className="control-group">
                    <button
                      className="button"
                      onClick={() =>
                        playing || audioLoading
                          ? stopAudio()
                          : void play(line.audio)
                      }
                      aria-label={
                        audioLoading
                          ? "取消音频加载"
                          : playing
                            ? "暂停语音"
                            : "播放 SunHi 原音"
                      }
                    >
                      {audioLoading ? (
                        <LoaderCircle size={18} className="spin" />
                      ) : playing ? (
                        <Pause size={18} />
                      ) : (
                        <Volume2 size={18} />
                      )}
                      <span>
                        {audioLoading ? "加载中…" : playing ? "暂停" : "听原音"}
                      </span>
                    </button>
                    <button
                      className="button subtle speech-speed"
                      aria-label={`播放速度 ${rate === 1 ? "正常" : "0.8 倍"}，点击切换`}
                      onClick={() => {
                        const next = rate === 1 ? 0.8 : 1;
                        setRate(next);
                        audio.current?.setRate(next);
                      }}
                    >
                      {rate === 1 ? "1×" : "0.8×"}
                    </button>
                    <button
                      className="button subtle"
                      aria-pressed={meaning}
                      onClick={() => setMeaning(!meaning)}
                    >
                      {meaning ? "藏中文" : "看中文"}
                    </button>
                  </div>
                  <div className="control-group">
                    <button
                      className="button"
                      aria-label="上一句"
                      disabled={!cursor || busy}
                      onClick={() => {
                        setCursor(cursor - 1);
                        setWord(null);
                        stopAudio();
                      }}
                    >
                      <ChevronLeft size={18} />
                    </button>
                    <button
                      className="button primary"
                      disabled={disabled}
                      onClick={() => void nextLine()}
                    >
                      {busy
                        ? "保存中…"
                        : cursor === lesson.lines.length - 1
                          ? "开始练习"
                          : "懂了，下一句"}
                      <ArrowRight size={17} />
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
          {audioError && (
            <p className="error-state" role="alert">
              {audioError}
            </p>
          )}
          {!done && !isQuiz && (
            <>
              <div className="word-strip">
                <BookOpen size={17} />
                本句词语
                {line.words.map((w) => (
                  <button
                    key={w.id}
                    className={
                      "word-chip " + (word?.id === w.id ? "selected" : "")
                    }
                    lang="ko"
                    aria-pressed={word?.id === w.id}
                    onClick={() => setWord(word?.id === w.id ? null : w)}
                  >
                    {w.term}
                  </button>
                ))}
              </div>
              {word && (
                <div className="word-detail">
                  <div className="overview-row">
                    <div>
                      <strong lang="ko">{word.term}</strong>
                      <span>{word.zh}</span>
                    </div>
                    <button
                      className="button"
                      aria-label={"听原形 " + word.term}
                      onClick={() => void play(word.audio)}
                    >
                      <Volume2 size={18} />
                    </button>
                  </div>
                  <p>
                    这里显示词语原形及本句采用的词义。点击句子里的词，可听包含助词和词尾的完整词形，并查看语法说明。
                  </p>
                  {word.definition && <p>{word.definition}</p>}
                  {word.pronunciation?.length ? (
                    <p>
                      词典标音：
                      <span lang="ko">{word.pronunciation.join(" / ")}</span>
                    </p>
                  ) : null}
                  {word.entryId && (
                    <a
                      className="dictionary-link"
                      href={`https://krdict.korean.go.kr/chn/dicSearch/SearchView?ParaWordNo=${word.entryId}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      核对国立国语院中文词条
                    </a>
                  )}
                </div>
              )}
            </>
          )}
          {done && signedIn && lesson.stage === 5 && (
            <div className="writing">
              <div className="overview-row">
                <h3>轮到你来回应</h3>
                <span className="muted">书面表达 · 可选</span>
              </div>
              <p className="muted">
                围绕「{lesson.title}」，用韩语写一段 150–250
                字的回复：提出观点，给出理由，并说明限制。这是练习，不自动评定
                TOPIK 等级。
              </p>
              <textarea
                className="text-answer"
                aria-label="我的韩语回复"
                lang="ko"
                value={draft}
                readOnly={disabled}
                aria-busy={busy}
                maxLength={4000}
                onChange={(e) => {
                  setDraft(e.target.value);
                  draftTouched.current = true;
                  setDraftSaved(false);
                }}
                placeholder="제 생각에는…"
              />
              <div className="overview-row">
                <span className="muted">
                  {draft.length} 字 {draftSaved ? "· 已存云端" : ""}
                </span>
                <div className="control-group">
                  <button
                    className="button subtle"
                    disabled={busy}
                    onClick={() => void readCloudDraft()}
                  >
                    读取云端回复
                  </button>
                  <button
                    className="button"
                    disabled={disabled || (!draft.trim() && !record?.draft)}
                    onClick={() => void saveDraft()}
                  >
                    {draft.length === 0 && record?.draft ? "清空云端回复" : "保存回复"}
                  </button>
                </div>
              </div>
              <details className="beginner-help">
                <summary>写完后自查</summary>
                <p>
                  观点是否明确？每个理由是否有例子？有无过度概括？主语、助词、时态和书面语尾是否一致？本功能只保存回复，尚未提供教师批改。
                </p>
              </details>
            </div>
          )}
          <p className="hint">听一句，懂一句，再接下一句。</p>
          {lesson.source && (
            <p className="coverage-note">
              韩语例句与词典中文义：
              <a href={lesson.source.url} target="_blank" rel="noreferrer">
                {lesson.source.label}
              </a>{" "}
              ·{" "}
              <a href={lesson.source.license} target="_blank" rel="noreferrer">
                CC BY-SA 2.0 KR
              </a>
              。整句中文及点词注释为本课程编译。
              <a href="/content-sources.html" target="_blank">
                来源与审校说明
              </a>
            </p>
          )}
          <div className="bottom-stats">
            <span>
              <strong>{counts.completed}</strong>/{lessons.length} 关完成
            </span>
            <span>
              <strong>{counts.words}</strong>/{totalWords} 词条接触
            </span>
            <span>
              <strong>{counts.sentences}</strong>/{totalSentences} 条对话接触
            </span>
          </div>
          <p className="coverage-note">
            {signedIn
              ? "学习进度按账号保存在云端。学过不等于掌握。"
              : "访客试学不会保存进度。登录后可记录学过的词句。"}
          </p>
        </section>
      </main>
      <dialog
        ref={dialog}
        className="sheet"
        aria-labelledby="learning-tools-title"
        onClose={() => setPanel(null)}
        onClick={(e) => {
          if (e.target === dialog.current) {
            const r = dialog.current.getBoundingClientRect();
            if (
              e.clientX < r.left ||
              e.clientX > r.right ||
              e.clientY < r.top ||
              e.clientY > r.bottom
            )
              setPanel(null);
          }
        }}
      >
        <div className="sheet-head">
          <h2 id="learning-tools-title">
            {panel === "lessons"
              ? "你的对话旅程"
              : panel === "plan"
                ? "半年冲刺，逐步验证"
                : "韩文，从拼成一个音节开始"}
          </h2>
          <button
            className="button subtle"
            aria-label="关闭"
            onClick={() => setPanel(null)}
          >
            <X size={21} />
          </button>
        </div>
        {panel && error && (
          <p className="error-state" role="alert">
            {error}
            {failedLesson && (
              <button
                className="text-link"
                disabled={busy || contentBusy}
                onClick={() =>
                  void chooseLesson(failedLesson.id, failedLesson.restart)
                }
              >
                重新打开对话
              </button>
            )}
          </p>
        )}
        {panel && contentBusy && (
          <p className="muted" role="status">
            正在打开对话…
          </p>
        )}
        {panel === "lessons" && (
          <>
            <p className="muted">
              所有关卡自由选择。按月份、日期查看当天对话，勾号表示已经完成。
            </p>
            <label className="course-search">
              搜索课程标题（韩语 / 中文）
              <input
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="例如：咖啡、커피、c01"
                autoComplete="off"
              />
            </label>
            {search.trim() && (
              <p className="muted" role="status">
                找到 {searchResults.length} 关
                {searchResults.length > 80
                  ? "，显示前 80 关，请缩小搜索范围"
                  : ""}
                。搜索匹配标题和关卡编号。
              </p>
            )}
            {!search.trim() && (
              <>
                <div
                  className="month-tabs"
                  role="group"
                  aria-label="选择课程月份"
                >
                  {stages.map((name, i) => (
                    <button
                      key={name}
                      className={
                        "button " + (courseMonth === i ? "primary" : "")
                      }
                      aria-pressed={courseMonth === i}
                      onClick={() => {
                        setCourseMonth(i);
                        setCourseDay(i * 30 + 1);
                      }}
                    >
                      第 {i + 1} 月
                    </button>
                  ))}
                </div>
                <div
                  className="course-day-grid"
                  role="group"
                  aria-label="选择课程日期"
                >
                  {Array.from(
                    { length: 30 },
                    (_, i) => courseMonth * 30 + i + 1,
                  ).map((day) => (
                    <button
                      key={day}
                      className={
                        "button " + (courseDay === day ? "primary" : "")
                      }
                      aria-pressed={courseDay === day}
                      onClick={() => setCourseDay(day)}
                    >
                      {day}
                    </button>
                  ))}
                </div>
              </>
            )}
            <section className="course-section">
              <h3>
                {search.trim()
                  ? "搜索结果"
                  : `第 ${courseDay} 天 · ${coursePlan.lessonIds.length ? stages[courseMonth] : "复习对话"}`}
              </h3>
              <div className="lesson-list">
                {visibleLessonIds
                  .map((id) => lessonById.get(id)!)
                  .map((l) => (
                    <button
                      className={
                        "lesson-item " + (lesson.id === l.id ? "active" : "")
                      }
                      key={l.id}
                      disabled={disabled}
                      onClick={() => void chooseLesson(l.id)}
                    >
                      <span>
                        <strong>{l.title}</strong>
                        <span className="muted block">
                          第 {l.day} 天 · {l.lineCount} 句对话
                        </span>
                      </span>
                      {completedIds.has(l.id) ? (
                        <Check size={19} />
                      ) : (
                        <ArrowRight size={17} />
                      )}
                    </button>
                  ))}
              </div>
              {!search.trim() && !coursePlan.lessonIds.length && (
                <p className="muted">
                  今天不增加新词句。上方是近期及间隔复习对话，可直接选择。
                </p>
              )}
            </section>
          </>
        )}

        {panel === "plan" && (
          <PlanBoundary>
            <Suspense fallback={<p role="status">正在打开学习安排…</p>}>
              <StudyPlan
                initialMonth={lesson.stage}
                disabled={disabled}
                onChooseLesson={(id) => void chooseLesson(id)}
              />
            </Suspense>
          </PlanBoundary>
        )}
        {panel === "hangul" && (
          <>
            {audioError && (
              <p className="error-state" role="alert">
                {audioError}
              </p>
            )}
            {audioLoading && (
              <p role="status" className="muted">
                正在加载读音…
              </p>
            )}
            <p>
              韩文按音节组合。<strong lang="ko">한 = ㅎ + ㅏ + ㄴ</strong>
              ：开头辅音、元音、结尾收音。<strong lang="ko">아</strong> 的开头
              ㅇ 不发音；收音位置的 ㅇ 发鼻音。
            </p>
            <div className="plan-note">
              点下面的字母，听它组成的示例音节。辅音用「辅音 + ㅏ」演示，例如 ㄱ
              的按钮播放 가，不是字母名称 기역。
            </div>
            {[
              ["基本元音", 0, 10],
              ["基本辅音", 10, 24],
              ["紧音", 24, 29],
              ["复合元音", 29, 40],
            ].map(([title, start, end]) => (
              <section className="course-section" key={title}>
                <h3>{title}</h3>
                <div className="hangul-table">
                  {hangul.slice(Number(start), Number(end)).map((h) => (
                    <button
                      key={h.letter}
                      className="button"
                      onClick={() => void play(h.audio)}
                      aria-label={`${h.letter} 的示例音节 ${h.syllable}`}
                    >
                      <strong lang="ko">{h.letter}</strong>
                      <small lang="ko">{h.syllable}</small>
                    </button>
                  ))}
                </div>
              </section>
            ))}
            <p className="muted">
              收音主要归为七类音，且会发生连音、鼻音化、紧音化等变化。先听完整单词和句子，不用中文谐音代替韩文发音。这里是拼读速查，完整发音训练仍需扩充。
            </p>
          </>
        )}
      </dialog>
    </>
  );
}
