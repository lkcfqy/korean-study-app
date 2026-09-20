'use client';

import {Fragment,useState} from 'react';
import {Volume2} from 'lucide-react';
import type {Line} from '../lib/course';

export default function SentenceReader({line,meaning,onListen,onListenWord}:{line:Line;meaning:boolean;onListen:()=>void;onListenWord:(path:string)=>void}){
 const [selected,setSelected]=useState<number|null>(null);
 const part=selected===null?null:line.parts[selected];
 const explanations=part?.explanation.split(/[；;＋+]/).map(value=>value.trim())??[];
 const readings=part?line.words.filter(word=>explanations.some(value=>value.startsWith(word.term+'：')||value.startsWith(word.term+'（'))||part.text.replace(/[.!?。？！]/g,'')===word.term):[];
 return <>
  <p className="korean interactive-sentence" lang="ko">{line.parts.map((p,i)=><Fragment key={i}>{i>0?' ':null}<button className={'sentence-token '+(selected===i?'selected':'')} aria-pressed={selected===i} aria-label={`拆解 ${p.text}`} onClick={()=>setSelected(selected===i?null:i)}>{p.text}</button></Fragment>)}</p>
  <p className={'translation '+(!meaning?'hidden-translation':'')}>{meaning?line.zh:'先听一遍，再试着理解。'}</p>
  <p className="line-note">{meaning?line.note:'需要提示时，可以显示中文或点句子里的词语。'}</p>
  <div className="breakdown-tools"><span>点句中词语，看注释、听读音</span></div>
  {part&&<div className="selected-part" role="region" aria-label="选中词语的注释"><div className="overview-row"><strong lang="ko">{part.text}</strong><span>{part.meaning}</span></div><p>{part.explanation}</p><div className="context-pronunciation">{readings.map(word=><button key={word.id} className="text-link" aria-label={'听原形 '+word.term} onClick={()=>onListenWord(word.audio)}><Volume2 size={16}/>听原形 <span lang="ko">{word.term}</span></button>)}<button className="text-link" onClick={onListen}><Volume2 size={16}/>听句中读音</button></div></div>}
 </>;
}
