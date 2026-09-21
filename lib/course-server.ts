import index from '../content/course-index.json';
import type {LessonProgress} from './course';

// Full answer and word/sentence indexes stay in the Worker. Browsers only need
// the compact catalog to navigate; progress responses carry deduplicated totals.
export const lessons=index.lessons;
const byId=new Map(lessons.map(lesson=>[lesson.id,lesson]));

export function countsFor(rows:LessonProgress[]){
 const sentences=new Set<number>(),words=new Set<number>();
 for(const row of rows){
  const lesson=byId.get(row.lesson_id);
  if(!lesson)continue;
  lesson.lineStats.forEach(([sentence,...terms],i)=>{
   if(row.read_mask&(1<<i)){sentences.add(sentence);terms.forEach(id=>words.add(id));}
  });
 }
 return {sentences:sentences.size,words:words.size,completed:rows.filter(row=>row.completed_at!==null&&byId.has(row.lesson_id)).length};
}
