import data from '../content/course.json';
import {z} from 'zod';
export type Word = {id:string;term:string;zh:string;audio:string};
export type Line = {id:string;ko:string;zh:string;note:string;words:Word[];audio:string;speakerIndex:number};
export type Lesson = {id:string;stage:number;title:string;scene:string;roles:string[];lines:Line[]};
export const lessons: Lesson[] = data;
export const stages = ['初识韩语','日常生活','表达想法','走进社会','理解观点','学术与论证'];
export const sentenceKey = (text:string) => text.replace(/[\s.!?。？！]/g,'');
export const totalSentences = new Set(lessons.flatMap(l=>l.lines.map(s=>sentenceKey(s.ko)))).size;
export const totalWords = new Set(lessons.flatMap(l=>l.lines.flatMap(s=>s.words.map(w=>w.term)))).size;
export function questionsFor(lesson:Lesson){
  const n=lessons.findIndex(l=>l.id===lesson.id);
  return [2,4].map((lineIndex,q)=>{
    const answer=(n+q)%3;
    const options=[lesson.lines[0].zh,lesson.lines[1].zh];
    options.splice(answer,0,lesson.lines[lineIndex].zh);
    return {line:lesson.lines[lineIndex],options,answer};
  });
}
export type LessonProgress={lesson_id:string;cursor:number;read_mask:number;completed_at:number|null;next_review_at:number|null;review_step:number;updated_at:number;draft:string;draft_revision:number};
export type Progress={rows:LessonProgress[];currentLesson:string;serverTime:number};
export const progressSchema=z.object({rows:z.array(z.object({lesson_id:z.string(),cursor:z.number().int().nonnegative(),read_mask:z.number().int().nonnegative(),completed_at:z.number().nullable(),next_review_at:z.number().nullable(),review_step:z.number().int(),updated_at:z.number(),draft:z.string(),draft_revision:z.number().int()})),currentLesson:z.string(),serverTime:z.number()});
export const errorSchema=z.object({error:z.string(),progress:progressSchema.optional()});
export function countsFor(rows:LessonProgress[]){
  const sentences=new Set<string>();const words=new Set<string>();
  for(const row of rows){const lesson=lessons.find(l=>l.id===row.lesson_id);if(!lesson)continue;lesson.lines.forEach((s,i)=>{if(row.read_mask&(1<<i)){sentences.add(sentenceKey(s.ko));s.words.forEach(w=>words.add(w.term));}});}
  return {sentences:sentences.size,words:words.size,completed:rows.filter(r=>r.completed_at!==null).length};
}
