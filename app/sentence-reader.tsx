'use client';

import {Fragment,useId,useRef,useState} from 'react';
import {Volume2} from 'lucide-react';
import type {Line} from '../lib/course';

export default function SentenceReader({line,meaning,onListen,onListenWord}:{line:Line;meaning:boolean;onListen:()=>void;onListenWord:(path:string)=>void}){
 const [selected,setSelected]=useState<number|null>(null);
 const noteId=useId();
 const tokens=useRef<(HTMLButtonElement|null)[]>([]);
 const part=selected===null?null:line.parts[selected];
 const readings=part?.readings??[];
 return <>
  <p className="korean interactive-sentence" lang="ko">{line.parts.map((p,i)=><Fragment key={i}>{i>0?' ':null}<button ref={node=>{tokens.current[i]=node;}} className={'sentence-token '+(selected===i?'selected':'')} aria-expanded={selected===i} aria-controls={selected===i?noteId:undefined} aria-label={`查看 ${p.text} 的注释`} onClick={()=>setSelected(selected===i?null:i)} onKeyDown={event=>{if(event.key==='Escape'){setSelected(null);event.stopPropagation();}}}>{p.text}</button></Fragment>)}</p>
  <p className={'translation '+(!meaning?'hidden-translation':'')}>{meaning?line.zh:'先听一遍，再试着理解。'}</p>
  <p className="line-note">{meaning?line.note:'需要提示时，可以显示中文或点句子里的词语。'}</p>
  <div className="breakdown-tools"><span>点句中词语，看注释、听读音</span></div>
  {part&&<div id={noteId} className="selected-part" role="region" aria-label="选中词语的注释" aria-live="polite" onKeyDown={event=>{if(event.key==='Escape'){if(selected!==null)tokens.current[selected]?.focus();setSelected(null);event.stopPropagation();}}}><div className="overview-row"><strong lang="ko">{part.text}</strong><span>{part.meaning}</span></div><p>{part.explanation}</p><div className="context-pronunciation">{readings.map(word=><button key={word.term} className="text-link" aria-label={'听词语 '+word.term} onClick={()=>onListenWord(word.audio)}><Volume2 size={16}/>听词语 <span lang="ko">{word.term}</span></button>)}<button className="text-link" onClick={onListen}><Volume2 size={16}/>听整句</button></div></div>}
 </>;
}
