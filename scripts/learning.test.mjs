import assert from 'node:assert/strict';
import {test} from 'node:test';
import {planSession,searchLessons} from '../lib/study-session.ts';
import {mergeProgress} from '../lib/merge-progress.ts';
import {listeningCheckSchema,independentAnswers,hasContrastQuestions} from '../lib/listening-check.ts';

const row=(lesson_id,overrides={})=>({lesson_id,cursor:2,read_mask:3,completed_at:10,next_review_at:100,review_step:0,updated_at:10,draft:'',draft_revision:0,...overrides});
const catalog=Array.from({length:20},(_,i)=>({id:`l${i}`,title:`课程 ${i}`,day:i+1}));

test('a review backlog prevents extra new lessons and prioritizes consolidation',()=>{
 const rows=catalog.slice(0,10).map(l=>row(l.id));rows[9].review_step=-1;
 const session=planSession(catalog,rows,200,4);
 assert.deepEqual(session.ids,['l9','l0','l1','l2']);assert.equal(session.newIds.length,0);assert.equal(session.remainingReviews,6);
});
test('a larger session adds at most four unseen lessons, never already completed or unknown IDs',()=>{
 const rows=[row('l0',{next_review_at:999}),row('removed',{review_step:-1}),row('l1')];
 const session=planSession(catalog,rows,200,12);
 assert.deepEqual(session.ids,['l1','l2','l3','l4','l5']);assert.equal(session.dueCount,1);
});
test('due time is inclusive; future reviews wait; unfinished lessons resume',()=>{
 const rows=[row('l0',{next_review_at:201}),row('l1',{next_review_at:200}),row('l2',{completed_at:null,next_review_at:null,cursor:1})];
 assert.deepEqual(planSession(catalog,rows,200,4).ids,['l1','l2','l3','l4']);
});
test('empty and fully completed courses do not create nonexistent work',()=>{
 assert.deepEqual(planSession([],[],200).ids,[]);
 assert.deepEqual(planSession(catalog,catalog.map(l=>row(l.id,{next_review_at:999})),200).ids,[]);
});
test('course search handles Korean, Chinese, Unicode width and multiple title terms',()=>{
 const lessons=[{id:'c01',title:'点咖啡 · 커피',day:1},{id:'c02',title:'买衬衫 · 셔츠',day:1}];
 for(const query of ['커피','咖啡','Ｃ０１','咖啡 커피'])assert.equal(searchLessons(lessons,query)[0].id,'c01');
 assert.deepEqual(searchLessons(lessons,'不存在'),[]);assert.deepEqual(searchLessons(lessons,'  '),[]);
});
test('incremental progress preserves other lessons, drafts and authoritative counters',()=>{
 const old={rows:[row('l0',{draft:'다른 기기',draft_revision:3}),row('l1')],currentLesson:'l0',serverTime:20,counts:{sentences:4,words:9,completed:2}};
 const delta={kind:'delta',row:row('l1',{updated_at:30,review_step:-1}),currentLesson:'l1',serverTime:30,counts:{sentences:4,words:10,completed:2}};
 const merged=mergeProgress(old,delta);
 assert.equal(merged.rows.length,2);assert.equal(merged.rows[0].review_step,-1);assert.equal(merged.rows[1].draft,'다른 기기');assert.equal(merged.counts.words,10);
 assert.deepEqual(mergeProgress(merged,delta),merged);assert.equal(old.rows[1].review_step,0);
});
test('self-rated recall does not claim independent success for hints or unfinished audio',()=>{
 const check={mode:'recall',recalled:[true,true],heard:[true,true],hints:[false,false]};
 assert.equal(independentAnswers(listeningCheckSchema.parse(check),[0,2]),2);
 assert.equal(independentAnswers({...check,hints:[true,false]},[0,2]),1);
 assert.equal(independentAnswers({...check,heard:[false,false]},[0,2]),0);
 assert.equal(independentAnswers({...check,recalled:[false,true]},[0,2]),1);
});
test('legacy choice evidence remains compatible and malformed recall is rejected',()=>{
 const check={firstAnswers:[0,2],heard:[true,true],hints:[false,false]};
 assert.equal(independentAnswers(listeningCheckSchema.parse(check),[0,2]),2);
 assert.equal(independentAnswers({...check,firstAnswers:[1,2]},[0,2]),1);
 assert.equal(listeningCheckSchema.safeParse({mode:'recall',recalled:[true],heard:[true,true],hints:[false,false]}).success,false);
 assert.equal(listeningCheckSchema.safeParse({...check,mode:'unknown'}).success,false);
 assert.equal(hasContrastQuestions('c01'),true);assert.equal(hasContrastQuestions('n79167-2-7'),false);
});
