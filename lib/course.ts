import index from '../content/course-index.json';
import {z} from 'zod';

export type Word={id:string;term:string;zh:string;audio:string;entryId?:string;definition?:string;pronunciation?:string[]};
export type SentencePart={text:string;meaning:string;explanation:string;readings?:{term:string;audio:string}[]};
export type Line={id:string;ko:string;zh:string;note:string;words:Word[];parts:SentencePart[];audio:string;speakerIndex:number};
export type Lesson={id:string;stage:number;title:string;scene:string;roles:string[];lines:Line[];day?:number;source?:{url:string;label:string;license:string};questions:{lineIndex:number;options:string[];answer:number}[]};
export type LessonMeta={id:string;stage:number;title:string;scene:string;day:number;lineCount:number;lineStats:number[][];answers:number[];revision:string};
export const lessons:LessonMeta[]=index.lessons;
export const lessonById=new Map(lessons.map(l=>[l.id,l]));
export const stages=['初识韩语','日常生活','表达想法','走进社会','理解观点','学术与论证'];
export const totalSentences=index.totalSentences;
export const totalWords=index.totalWords;
export const sentenceKey=(text:string)=>text.normalize('NFC').replace(/[^\p{L}\p{N}]/gu,'');
export const questionsFor=(lesson:Lesson)=>lesson.questions.map(q=>({...q,line:lesson.lines[q.lineIndex]}));

const wordSchema=z.object({id:z.string(),term:z.string(),zh:z.string(),audio:z.string(),entryId:z.string().optional(),definition:z.string().optional(),pronunciation:z.array(z.string()).optional()});
const lineSchema=z.object({id:z.string(),ko:z.string(),zh:z.string(),note:z.string(),words:z.array(wordSchema),parts:z.array(z.object({text:z.string(),meaning:z.string(),explanation:z.string(),readings:z.array(z.object({term:z.string(),audio:z.string()})).optional()})).min(1),audio:z.string(),speakerIndex:z.number().int().min(0).max(1)});
export const lessonSchema=z.object({id:z.string(),stage:z.number().int().min(0).max(5),title:z.string(),scene:z.string(),roles:z.array(z.string()).length(2),lines:z.array(lineSchema).min(2).max(30),day:z.number().optional(),source:z.object({url:z.string(),label:z.string(),license:z.string()}).optional(),questions:z.array(z.object({lineIndex:z.number().int().nonnegative(),options:z.array(z.string()).length(3),answer:z.number().int().min(0).max(2)})).length(2)});

export type LessonProgress={lesson_id:string;cursor:number;read_mask:number;completed_at:number|null;next_review_at:number|null;review_step:number;updated_at:number;draft:string;draft_revision:number};
export type Progress={rows:LessonProgress[];currentLesson:string;serverTime:number};
export const progressSchema=z.object({rows:z.array(z.object({lesson_id:z.string(),cursor:z.number().int().nonnegative(),read_mask:z.number().int().nonnegative(),completed_at:z.number().nullable(),next_review_at:z.number().nullable(),review_step:z.number().int(),updated_at:z.number(),draft:z.string(),draft_revision:z.number().int()})),currentLesson:z.string(),serverTime:z.number()});
export const errorSchema=z.object({error:z.string(),progress:progressSchema.optional()});
export function countsFor(rows:LessonProgress[]){
 const sentences=new Set<number>(),words=new Set<number>();
 for(const row of rows){const lesson=lessonById.get(row.lesson_id);if(!lesson)continue;lesson.lineStats.forEach(([s,...w],i)=>{if(row.read_mask&(1<<i)){sentences.add(s);w.forEach(id=>words.add(id));}});}
 return {sentences:sentences.size,words:words.size,completed:rows.filter(r=>r.completed_at!==null&&lessonById.has(r.lesson_id)).length};
}
