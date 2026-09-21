"use client";

import { useState } from "react";
import { ArrowRight, Check, Headphones, Volume2 } from "lucide-react";
import { questionsFor, type Lesson } from "../lib/course";
import {
  independentAnswers,
  type ChoiceCheck as Attempt,
} from "../lib/listening-check";

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
export default function ListeningCheck({
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
  const [answers, setAnswers] = useState<number[]>([]);
  const [firstAnswers, setFirstAnswers] = useState<number[]>([]);
  const [heard, setHeard] = useState<[boolean, boolean]>([false, false]);
  const [hints, setHints] = useState<[boolean, boolean]>([
    usedStudyHelp,
    usedStudyHelp,
  ]);
  const [showText, setShowText] = useState(false);
  const [listening, setListening] = useState(false);
  const question = questions[step];
  const selected = answers[step];
  const correct = selected === question.answer;
  const canAnswer = heard[step] || showText;

  async function listen() {
    setListening(true);
    await onListen(question.line.audio, (completed) => {
      if (completed)
        setHeard((previous) =>
          step === 0 ? [true, previous[1]] : [previous[0], true],
        );
      setListening(false);
    });
  }
  function reveal() {
    setShowText(true);
    setHints((previous) =>
      step === 0 ? [true, previous[1]] : [previous[0], true],
    );
  }
  function choose(answer: number) {
    if (busy || !canAnswer || correct) return;
    setFirstAnswers((previous) => {
      const next = [...previous];
      if (next[step] === undefined) next[step] = answer;
      return next;
    });
    setAnswers((previous) => {
      const next = [...previous];
      next[step] = answer;
      return next;
    });
  }
  async function next() {
    if (!correct || busy) return;
    onStop();
    setListening(false);
    if (step === 0) {
      setStep(1);
      setShowText(false);
      return;
    }
    const attempt: Attempt = {
      firstAnswers: [firstAnswers[0], firstAnswers[1]],
      heard,
      hints,
    };
    await onComplete(answers, attempt);
  }
  const result =
    step === 1 && correct
      ? independentAnswers(
          { firstAnswers: [firstAnswers[0], firstAnswers[1]], heard, hints },
          questions.map((q) => q.answer),
        )
      : null;
  return (
    <>
      <div className="dialogue-body quiz-body">
        <div className="speaker">
          <Headphones size={19} />
          听力检查 · 第 {step + 1} / 2 句
        </div>
        <h2 className="listening-title">先听一句，再选意思。</h2>
        <p className="line-note">
          韩文先收起来。回看对话或使用韩文提示后，这次按巩固练习记录。
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
          <button
            className="button subtle"
            disabled={busy || showText}
            onClick={reveal}
          >
            {showText ? "已使用韩文提示" : "查看韩文提示"}
          </button>
        </div>
        {showText && (
          <p className="korean quiz-transcript" lang="ko">
            {question.line.ko}
          </p>
        )}
        <p className="line-note" role="status">
          {canAnswer
            ? "这句在刚才的对话中是什么意思？"
            : "听完后显示选项；音频暂时不可用时，也可以用韩文提示继续练习。"}
        </p>
      </div>
      {canAnswer && (
        <div className="choices">
          {question.options.map((option, i) => (
            <button
              key={option}
              disabled={busy || correct}
              className={
                "choice " +
                (selected === i ? (correct ? "correct" : "wrong") : "")
              }
              onClick={() => choose(i)}
            >
              <span className="choice-letter">
                {String.fromCharCode(65 + i)}
              </span>
              {option}
              {selected === i && correct && <Check size={18} />}
            </button>
          ))}
        </div>
      )}
      {selected !== undefined && (
        <p className="answer-feedback" role="status">
          {correct
            ? "理解正确。"
            : `还不太对，回听后再试。${question.line.note}`}
          {question.explanation && (
            <span className="contrast-explanation">
              辨析：{question.explanation}
            </span>
          )}
        </p>
      )}
      {result !== null && (
        <p className="answer-feedback">
          本次 {result} / 2 句首次独立答对。
          {result === 2
            ? "下次隔一段时间再听，检查是否记住。"
            : "答错或看过提示的内容，建议明天再巩固。"}
        </p>
      )}
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
          disabled={!correct || busy}
          onClick={() => void next()}
        >
          {busy ? "保存中…" : step === 0 ? "下一句" : "完成本关"}
          <ArrowRight size={17} />
        </button>
      </div>
    </>
  );
}
