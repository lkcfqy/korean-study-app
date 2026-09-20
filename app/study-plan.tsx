'use client';

import {useState} from 'react';
import plan from '../content/study-plan.json';
import {lessons,lessonById,totalWords,totalSentences} from '../lib/course';

export default function StudyPlan({initialMonth,disabled,onChooseLesson}:{initialMonth:number;disabled:boolean;onChooseLesson:(id:string)=>void}){
 const [month,setMonth]=useState(initialMonth);
 const spec=plan.months[month];
 const days=plan.days.filter(d=>d.month===month+1);
 return <>
  <p>180 天，每天 4 小时，共 720 小时。按从入门到进阶的顺序安排，也可以直接选择任意一天、任意关卡。</p>
  <div className="plan-note"><strong>站内精读：{lessons.length} 关 · {totalSentences} 个独立句 · {totalWords} 个核心词条</strong><p>{plan.inventoryNote}</p></div>
  <div className="month-tabs" role="group" aria-label="选择学习月份">{plan.months.map((m,i)=><button key={m.month} className={'button '+(month===i?'primary':'')} aria-pressed={month===i} onClick={()=>setMonth(i)}>第 {m.month} 月</button>)}</div>
  <section className="month-overview"><p className="eyebrow">DAY {spec.startDay}–{spec.endDay}</p><h3>{spec.title}</h3><p>{spec.skills}</p><p className="month-target">截至本月的站内词句：<strong>{spec.words.toLocaleString()}</strong> 词条 · <strong>{spec.sentences.toLocaleString()}</strong> 个不同句子</p></section>
  <p className="muted">展开某一天查看四小时安排。每天列出的都是站内实际课程；复习日不增加新词、新句。</p>
  <div className="day-list">{days.map(day=>{
   return <details key={day.day} className="plan-day"><summary><span className="day-number">{day.day}</span><span className="day-title"><strong>{day.topic}</strong><small>{day.title} · {day.newWords?`新词 ${day.newWords} / 新句 ${day.newSentences}`:'不增加新词句'}</small></span><span aria-hidden="true" className="day-expand">＋</span></summary><div className="day-detail"><div className="day-dialogues">{(day.lessonIds.length?day.lessonIds:day.reviewLessonIds).map(id=>{const item=lessonById.get(id)!;return <button key={id} className="button" disabled={disabled} onClick={()=>onChooseLesson(id)}>{item.title}<span className="muted">{item.lineCount} 句</span></button>;})}</div><ol className="daily-tasks">{day.tasks.map((task,i)=><li key={i}><div><strong>{task.title}</strong><span>{task.minutes} 分钟</span></div><p>{task.instruction}</p></li>)}</ol><p className="muted">截至今天，课程累计收录：{day.cumulativeWords.toLocaleString()} 词条 / {day.cumulativeSentences.toLocaleString()} 句。同一词条、同一句子只计算一次。</p></div></details>;
  })}</div>
  <h3 className="section-title">本月怎么检验</h3><p>{spec.checkpoint}</p>
  <h3 className="section-title">记住了再加量</h3><p>{plan.retentionRule}</p>
  <h3 className="section-title">来源与阶段测评</h3><p>课程词句已经收录在站内。官方测评用于检查能力，测评题量不计入站内词句数量。</p><ul className="plan-sources">{plan.sources.map(s=><li key={s.url}><a href={s.url} target="_blank" rel="noreferrer">{s.label}</a></li>)}</ul>
  <div className="plan-note"><strong>目标需要用测评验证</strong><p>半年从零冲刺 TOPIK 6 是高强度目标，学习时长和词句数量不能保证结果。TOPIK II 纸笔考试 6 级线为 230/300；机考为 431/600，训练时请使用相应尺度。本日程的模考按纸笔格式安排。</p><p>每句配有中文、词语拆解和固定 SunHi 音频。具体审校方式与覆盖见来源说明；自动复核不等于独立教师逐条认证。</p></div>
 </>;
}
