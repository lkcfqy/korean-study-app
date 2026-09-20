import {getChatGPTUser} from '../../chatgpt-auth';
import {database,readProgress} from '../../../lib/progress-db';
import {lessons,type LessonProgress} from '../../../lib/course';
import {z} from 'zod';
export const dynamic='force-dynamic';
const bodySchema=z.discriminatedUnion('action',[
 z.object({action:z.literal('select'),lessonId:z.string(),restart:z.boolean().optional()}),
 z.object({action:z.literal('read'),lessonId:z.string(),lineIndex:z.number().int().min(0).max(30)}),
 z.object({action:z.literal('complete'),lessonId:z.string(),answers:z.array(z.number().int().min(0).max(2)).length(2)}),
 z.object({action:z.literal('draft'),lessonId:z.string(),text:z.string().max(4000),revision:z.number().int().nonnegative()}),
]);
function json(data:unknown,status=200){return Response.json(data,{status,headers:{'Cache-Control':'private, no-store','Vary':'Cookie'}});}
export async function GET(){
 const user=await getChatGPTUser();if(!user)return json({error:'请先登录，才能读取云端进度。'},401);
 try{return json(await readProgress(user.userId));}catch(e){console.error('progress_load_failed',e);return json({error:'暂时无法读取云端进度，请稍后重试。'},503);}
}
export async function POST(request:Request){
 const user=await getChatGPTUser();if(!user)return json({error:'请先登录，才能保存云端进度。'},401);
 const origin=request.headers.get('origin');
 if(origin&&origin!==new URL(request.url).origin)return json({error:'请求来源不正确。'},403);
 if(!request.headers.get('content-type')?.startsWith('application/json'))return json({error:'请求格式不正确。'},415);
 let body;try{
  const reader=request.body?.getReader();if(!reader)return json({error:'缺少学习记录。'},400);
  const decoder=new TextDecoder();let bytes=0;let raw='';
  while(true){const part=await reader.read();if(part.done)break;bytes+=part.value.byteLength;if(bytes>16000){await reader.cancel();return json({error:'内容过长。'},413);}raw+=decoder.decode(part.value,{stream:true});}
  raw+=decoder.decode();body=bodySchema.parse(JSON.parse(raw));
 }catch{return json({error:'学习记录格式不正确。'},400);}
 const lessonIndex=lessons.findIndex(l=>l.id===body.lessonId);if(lessonIndex<0)return json({error:'关卡不存在。'},404);
 const lesson=lessons[lessonIndex];
 try{
  const db=database();const now=Date.now();const uid=user.userId;
  if(body.action==='select'){
   await db.prepare('INSERT INTO lesson_progress (user_id,lesson_id,updated_at) VALUES (?,?,?) ON CONFLICT(user_id,lesson_id) DO UPDATE SET updated_at=excluded.updated_at, cursor=CASE WHEN ? THEN 0 ELSE lesson_progress.cursor END').bind(uid,lesson.id,now,body.restart?1:0).run();
  }else if(body.action==='read'){
   if(body.lineIndex>=lesson.lineCount)return json({error:'句子不存在。'},400);
   const prev=await db.prepare('SELECT read_mask FROM lesson_progress WHERE user_id=? AND lesson_id=?').bind(uid,lesson.id).first<{read_mask:number}>();
   const requiredMask=(1<<body.lineIndex)-1;
   if(((prev?.read_mask??0)&requiredMask)!==requiredMask)return json({error:'请按顺序完成前面的对话。'},409);
   await db.prepare('INSERT INTO lesson_progress (user_id,lesson_id,cursor,read_mask,updated_at) VALUES (?,?,?,?,?) ON CONFLICT(user_id,lesson_id) DO UPDATE SET cursor=excluded.cursor,read_mask=lesson_progress.read_mask | excluded.read_mask,updated_at=excluded.updated_at').bind(uid,lesson.id,body.lineIndex+1,1<<body.lineIndex,now).run();
  }else if(body.action==='complete'){
   if(lesson.answers.some((answer,i)=>answer!==body.answers[i]))return json({error:'还有一处理解需要再确认，回听后再试。'},422);
   const prev=await db.prepare('SELECT * FROM lesson_progress WHERE user_id=? AND lesson_id=?').bind(uid,lesson.id).first<LessonProgress>();
   if(!prev||prev.read_mask!==((1<<lesson.lineCount)-1))return json({error:'先学完这一关的全部对话。'},409);
   // This single conditional SQL update advances a due review at most once, even on retries from another device.
   await db.prepare('UPDATE lesson_progress SET completed_at=COALESCE(completed_at,?),cursor=?,updated_at=?,next_review_at=CASE WHEN completed_at IS NULL THEN ? WHEN next_review_at <= ? THEN ? + (CASE review_step WHEN 0 THEN 3 WHEN 1 THEN 7 WHEN 2 THEN 14 ELSE 30 END)*86400000 ELSE next_review_at END,review_step=CASE WHEN completed_at IS NOT NULL AND next_review_at <= ? THEN MIN(review_step+1,4) ELSE review_step END WHERE user_id=? AND lesson_id=?').bind(now,lesson.lineCount,now,now+86400000,now,now,now,uid,lesson.id).run();
  }else if(body.action==='draft'){
   if(lesson.stage!==5)return json({error:'这一关没有书面回复练习。'},400);
   const result=await db.prepare('UPDATE lesson_progress SET draft=?,draft_revision=draft_revision+1,updated_at=? WHERE user_id=? AND lesson_id=? AND draft_revision=?').bind(body.text,now,uid,lesson.id,body.revision).run();
   if(result.meta.changes!==1)return json({error:'另一台设备更新了这段回复。你的文字仍保留在输入框中，请先重新读取云端内容。',progress:await readProgress(uid)},409);
  }
  return json(await readProgress(uid));
 }catch(e){console.error('progress_save_failed',e);return json({error:'这一步还未保存成功，请检查网络后重试。'},503);}
}
