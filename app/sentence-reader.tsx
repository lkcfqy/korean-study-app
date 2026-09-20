'use client';

import {Fragment,useState} from 'react';
import {Volume2} from 'lucide-react';
import type {Line} from '../lib/course';

export default function SentenceReader({line,meaning,onListen}:{line:Line;meaning:boolean;onListen:()=>void}){
 const [selected,setSelected]=useState<number|null>(null);
 const [expanded,setExpanded]=useState(false);
 const part=selected===null?null:line.parts[selected];
 return <>
  <p className="korean interactive-sentence" lang="ko">{line.parts.map((p,i)=><Fragment key={i}>{i>0?' ':null}<button className={'sentence-token '+(selected===i?'selected':'')} aria-pressed={selected===i} aria-label={`拆解 ${p.text}`} onClick={()=>setSelected(selected===i?null:i)}>{p.text}</button></Fragment>)}</p>
  <p className={'translation '+(!meaning?'hidden-translation':'')}>{meaning?line.zh:'先听一遍，再试着理解。'}</p>
  <p className="line-note">{meaning?line.note:'需要提示时，可以显示中文或点句子里的词语。'}</p>
  <div className="breakdown-tools"><span>点句中词语，看意思和词形</span><button className="text-link" aria-expanded={expanded} aria-controls={'parts-'+line.id} onClick={()=>setExpanded(!expanded)}>{expanded?'收起整句拆解':'展开整句拆解'}</button></div>
  {part&&!expanded&&<div className="selected-part" role="region" aria-label="选中词语的拆解"><div className="overview-row"><strong lang="ko">{part.text}</strong><span>{part.meaning}</span></div><p>{part.explanation}</p></div>}
  <div id={'parts-'+line.id} hidden={!expanded} className="sentence-parts">{line.parts.map((p,i)=><div key={i} className={'part-row '+(selected===i?'selected':'')}><div className="part-heading"><strong lang="ko">{p.text}</strong><span>{p.meaning}</span></div><p>{p.explanation}</p></div>)}</div>
  {(part||expanded)&&<div className="context-pronunciation"><button className="text-link" onClick={onListen}><Volume2 size={16}/>在完整句子中听读音</button><span>连读和语调以整句为准。</span></div>}
 </>;
}
