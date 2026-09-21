"use client";

import { useState } from "react";
import { ArrowRight, Headphones, Volume2 } from "lucide-react";
import { questionsFor, type Lesson } from "../lib/course";
import type { RecallCheck as Attempt } from "../lib/listening-check";

type Pair = [boolean, boolean];
type Props = {
  lesson: Lesson;
  busy: boolean;
  usedStudyHelp: boolean;
  onListen: (
    path: string,
    onFinished: (completed: boolean) => void,
  ) => Promise<void>;
  onStop: () => void;
  onBack: () => void;
  onComplete: (answers: number[], attempt: Attempt) => Promise<void>;
};

export default function RecallCheck({
  lesson,
  busy,
  usedStudyHelp,
  onListen,
  onStop,
  onBack,
  onComplete,
}: Props) {
  const questions = questionsFor(lesson);
  const [step, setStep] = useState(0);
  const [heard, setHeard] = useState<Pair>([false, false]);
  const [hints, setHints] = useState<Pair>([usedStudyHelp, usedStudyHelp]);
  const [recalled, setRecalled] = useState<Pair>([false, false]);
  const [revealed, setRevealed] = useState(false);
  const [showText, setShowText] = useState(false);
  const [listening, setListening] = useState(false);
  const [rating, setRating] = useState<boolean | null>(null);
  const question = questions[step];
  function updatePair(pair: Pair, value: boolean): Pair {
    return step === 0 ? [value, pair[1]] : [pair[0], value];
  }
  async function listen() {
    setListening(true);
    await onListen(question.line.audio, (completed) => {
      if (completed) setHeard((previous) => updatePair(previous, true));
      setListening(false);
    });
  }
  function reveal() {
    onStop();
    setListening(false);
    setRevealed(true);
  }
  async function next() {
    if (rating === null || busy) return;
    onStop();
    const ratings = updatePair(recalled, rating);
    setRecalled(ratings);
    if (step === 0) {
      setStep(1);
      setRevealed(false);
      setShowText(false);
      setRating(null);
      return;
    }
    await onComplete(
      questions.map((q) => q.answer),
      { mode: "recall", recalled: ratings, heard, hints },
    );
  }
  return (
    <>
      <div className="dialogue-body quiz-body">
        <div className="speaker">
          <Headphones size={19} />
          回忆练习 · 第 {step + 1} / 2 句
        </div>
        <h2 className="listening-title">先听，再用自己的话说意思。</h2>
        <p className="line-note">
          先在心里或开口说出谁在做什么、时间和否定。想好后核对中文，再诚实自评；这里不会自动判定听力水平。
        </p>
        <div className="listening-actions">
          <button
            className="button primary"
            disabled={busy || listening}
            onClick={() => void listen()}
          >
            <Volume2 size={18} />
            {listening ? "正在播放…" : heard[step] ? "再听一遍" : "播放这一句"}
          </button>
          {!revealed && (
            <button
              className="button subtle"
              disabled={busy || showText}
              onClick={() => {
                setHints((previous) => updatePair(previous, true));
                setShowText(true);
              }}
            >
              查看韩文提示
            </button>
          )}
        </div>
        {(showText || revealed) && (
          <p className="korean quiz-transcript" lang="ko">
            {question.line.ko}
          </p>
        )}
        {!revealed ? (
          <>
            <p className="line-note" role="status">
              {heard[step] || showText
                ? "回忆好意思后，再展开核对。"
                : "完整听完后可以核对；音频不可用时可使用韩文提示。"}
            </p>
            <button
              className="button"
              disabled={busy || (!heard[step] && !showText)}
              onClick={reveal}
            >
              我已尝试回忆，展开核对
            </button>
          </>
        ) : (
          <>
            <p className="translation recall-translation">{question.line.zh}</p>
            <p className="line-note">
              核对前，你回忆得怎么样？同义表达也可以，注意不要漏掉否定和时间。
            </p>
            <div
              className="listening-actions"
              role="group"
              aria-label="回忆自评"
            >
              <button
                className={"button " + (rating === true ? "primary" : "")}
                disabled={busy}
                aria-pressed={rating === true}
                onClick={() => setRating(true)}
              >
                主要意思一致
              </button>
              <button
                className={"button " + (rating === false ? "primary" : "")}
                disabled={busy}
                aria-pressed={rating === false}
                onClick={() => setRating(false)}
              >
                没想起或有遗漏
              </button>
            </div>
            <p className="line-note" role="status">
              自评只用于安排复习。使用提示或有遗漏时，会安排短间隔巩固。
            </p>
          </>
        )}
      </div>
      <div className="card-controls">
        <button
          className="button subtle"
          disabled={busy}
          onClick={() => {
            onStop();
            onBack();
          }}
        >
          回到对话学习
        </button>
        <button
          className="button primary"
          disabled={busy || rating === null}
          onClick={() => void next()}
        >
          {busy ? "保存中…" : step === 0 ? "下一句" : "完成本关"}
          <ArrowRight size={17} />
        </button>
      </div>
    </>
  );
}
