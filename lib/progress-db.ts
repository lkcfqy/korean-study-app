import {env} from 'cloudflare:workers';
import type {LessonProgress,Progress} from './course';
import {lessons,countsFor} from './course-server';
export function database(){if(!env.DB)throw new Error('Progress database unavailable');return env.DB;}
export async function readProgress(userId:string):Promise<Progress>{
 const result=await database().prepare('SELECT lesson_id,cursor,read_mask,completed_at,next_review_at,review_step,updated_at,draft,draft_revision FROM lesson_progress WHERE user_id = ? ORDER BY updated_at DESC, lesson_id DESC').bind(userId).all<LessonProgress>();
 return {rows:result.results,currentLesson:result.results[0]?.lesson_id??lessons[0].id,serverTime:Date.now(),counts:countsFor(result.results)};
}
