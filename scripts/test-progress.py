"""Integration test for an explicitly local built Worker, using isolated test identities."""
import concurrent.futures, json, pathlib, sqlite3, time, urllib.request, urllib.error, uuid
ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:8787'
USER='qa_'+uuid.uuid4().hex
ALL_LESSONS=json.loads((ROOT/'content/course-index.json').read_text())['lessons']
ALL_META={l['id']:l for l in ALL_LESSONS}
LESSONS=[l for l in ALL_LESSONS if l['id'].startswith('c')]
for stage in range(6):
    extra=[l for l in ALL_LESSONS if l['stage']==stage and not l['id'].startswith('c')]
    if extra:LESSONS.extend([extra[0],extra[-1]])
META={l['id']:l for l in ALL_LESSONS}
checks=[]
def call(body=None,user=USER,origin=BASE,expected=200):
    headers={'Content-Type':'application/json','Origin':origin}
    if user:
        headers.update({'oai-authenticated-user-id':user,'oai-authenticated-user-email':'qa@example.test'})
    request=urllib.request.Request(BASE+'/api/progress',None if body is None else json.dumps(body).encode(),headers)
    try:
        with urllib.request.urlopen(request,timeout=15) as r: status=r.status;raw=r.read();cache=r.headers.get('Cache-Control','')
    except urllib.error.HTTPError as e: status=e.code;raw=e.read();cache=e.headers.get('Cache-Control','')
    assert status==expected,(status,expected,raw[:400])
    assert 'no-store' in cache
    data=json.loads(raw)
    if 'rows' in data:
        words=set();sentences=set();completed=0
        for row in data['rows']:
            lesson=ALL_META.get(row['lesson_id'])
            if not lesson:continue
            completed+=row['completed_at'] is not None
            for i,stats in enumerate(lesson['lineStats']):
                if row['read_mask']&(1<<i):sentences.add(stats[0]);words.update(stats[1:])
        assert data['counts']=={'words':len(words),'sentences':len(sentences),'completed':completed}
    return data
def passed(name): checks.append(name)
call(user=None,expected=401);call({'action':'select','lessonId':'c01'},user=None,expected=401);passed('anonymous reads and writes rejected')
call({'action':'select','lessonId':'c01'},origin='https://invalid.example',expected=403);passed('cross-origin write rejected')
result=call({'action':'select','lessonId':'c36'})
assert result['currentLesson']=='c36' and all(r['completed_at'] is None for r in result['rows'])
call({'action':'read','lessonId':'c36','lineIndex':0})
call({'action':'select','lessonId':'c07'})
passed('fresh account freely selects and studies advanced lessons without prerequisites')
call({'action':'read','lessonId':'c01','lineIndex':4},expected=409);passed('unread dialogue cannot be skipped')
call({'action':'complete','lessonId':'c01','answers':META['c01']['answers']},expected=409);passed('unread lesson cannot be completed')
call({'action':'read','lessonId':'c01','lineIndex':31},expected=400);passed('invalid requests rejected')
for n,lesson in enumerate(LESSONS):
    call({'action':'select','lessonId':lesson['id']})
    for i in range(lesson['lineCount']):call({'action':'read','lessonId':lesson['id'],'lineIndex':i})
    if n==0:
        call({'action':'complete','lessonId':lesson['id'],'answers':[(a+1)%3 for a in lesson['answers']]},expected=422)
        assert call()['rows'][0]['completed_at'] is None
        passed('wrong answer does not mark lesson completed')
    payload={'action':'complete','lessonId':lesson['id'],'answers':lesson['answers']}
    result=call(payload)
    record=next(r for r in result['rows'] if r['lesson_id']==lesson['id'])
    assert record['completed_at'] and record['read_mask']==(1<<lesson['lineCount'])-1
    duplicate=call(payload)
    row2=next(r for r in duplicate['rows'] if r['lesson_id']==lesson['id'])
    assert record['next_review_at']==row2['next_review_at'] and record['review_step']==row2['review_step']
passed('foundation lessons and first/last expanded dialogue in every month save, assess, and resume')
passed('duplicate completion does not inflate review schedule')
assert len(call()['rows'])==len(LESSONS) and call()['currentLesson']==LESSONS[-1]['id']
assert call(user=USER+'_other')['rows']==[];passed('two user identities have isolated progress')
# Every HTTP request uses a new client connection; rereads must come from durable D1 state.
assert all(r['read_mask']==(1<<META[r['lesson_id']]['lineCount'])-1 for r in call()['rows']);passed('fresh sessions restore durable progress')
call({'action':'draft','lessonId':'c31','text':'제 생각에는 근거를 확인해야 합니다.','revision':0})
call({'action':'draft','lessonId':'c31','text':'stale overwrite','revision':0},expected=409)
row=next(r for r in call()['rows'] if r['lesson_id']=='c31')
assert row['draft_revision']==1 and row['draft'].startswith('제 생각')
passed('stale writing revision cannot overwrite another device')
# Move only this test account's local review due time to the past.
for file in (ROOT/'.wrangler/state').rglob('*.sqlite'):
    db=sqlite3.connect(file)
    if db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lesson_progress'").fetchone():
        db.execute('UPDATE lesson_progress SET next_review_at=? WHERE user_id=? AND lesson_id=?',(int(time.time()*1000)-1000,USER,'c01'));db.commit();db.close();break
    db.close()
payload={'action':'complete','lessonId':'c01','answers':META['c01']['answers']}
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: list(pool.map(lambda _:call(payload),range(2)))
row=next(r for r in call()['rows'] if r['lesson_id']=='c01')
assert row['review_step']==1
assert 2.9*86400000<row['next_review_at']-int(time.time()*1000)<3.1*86400000
passed('simultaneous due review advances exactly once')
# Old-device replay changes its cursor but never clears learned lines or completions.
call({'action':'read','lessonId':'c01','lineIndex':0})
row=next(r for r in call()['rows'] if r['lesson_id']=='c01')
assert row['read_mask']==63 and row['completed_at'] and row['review_step']==1
passed('replay from another session preserves all earned progress')
# Listening evidence controls the interval independently of the final corrected answers.
LISTENER=USER+'_listening'
def listening_row():return next(r for r in call(user=LISTENER)['rows'] if r['lesson_id']=='c01')
def listening_attempt(first=None,heard=None,hints=None,include=True):
    payload={'action':'complete','lessonId':'c01','answers':META['c01']['answers']}
    if include:payload['check']={'firstAnswers':first or META['c01']['answers'],'heard':heard or [True,True],'hints':hints or [False,False]}
    return call(payload,user=LISTENER)
def make_due():
    db=sqlite3.connect(file)
    db.execute('UPDATE lesson_progress SET next_review_at=? WHERE user_id=? AND lesson_id=?',(int(time.time()*1000)-1000,LISTENER,'c01'))
    db.commit();db.close()
call({'action':'select','lessonId':'c01'},user=LISTENER)
for i in range(META['c01']['lineCount']):call({'action':'read','lessonId':'c01','lineIndex':i},user=LISTENER)
listening_attempt(hints=[True,False]);hinted=listening_row()
assert hinted['review_step']==-1 and .99*86400000<hinted['next_review_at']-int(time.time()*1000)<=86400000
passed('using a transcript hint schedules one-day consolidation')
listening_attempt(hints=[True,False]);assert listening_row()['next_review_at']==hinted['next_review_at']
listening_attempt(include=False);assert listening_row()['review_step']==-1
passed('duplicate assisted attempts do not postpone review and legacy clients cannot clear consolidation')
listening_attempt();independent=listening_row()
assert independent['review_step']==0 and independent['next_review_at']==hinted['next_review_at']
passed('independent success clears consolidation without skipping the first delayed review')
make_due();listening_attempt();row=listening_row()
assert row['review_step']==1 and 2.99*86400000<row['next_review_at']-int(time.time()*1000)<=3*86400000
passed('independent delayed success advances to a three-day interval')
first=META['c01']['answers'].copy();first[0]=(first[0]+1)%3
listening_attempt(first=first);row=listening_row()
assert row['review_step']==-1 and .99*86400000<row['next_review_at']-int(time.time()*1000)<=86400000
passed('first-answer error shortens a long interval even after the final answer is corrected')
make_due()
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda _:listening_attempt(),range(2)))
row=listening_row()
assert row['review_step']==0 and .99*86400000<row['next_review_at']-int(time.time()*1000)<=86400000
passed('simultaneous consolidation successes retain a one-day check instead of double advancement')
listening_attempt(heard=[False,True]);assert listening_row()['review_step']==-1
passed('an unplayed sentence cannot count as independent listening')
call({'action':'complete','lessonId':'c01','answers':META['c01']['answers'],'check':{'firstAnswers':[3,0],'heard':[True,True],'hints':[False,False]}},user=LISTENER,expected=400)
passed('malformed listening evidence is rejected')
passed('every progress response preserves deduplicated sentence word and completion counts')
# Exercise the largest normal account history without touching any real user.
full_user=USER+'_full'
now=int(time.time()*1000)
db=sqlite3.connect(file)
db.executemany('INSERT INTO lesson_progress (user_id,lesson_id,cursor,read_mask,completed_at,next_review_at,review_step,updated_at) VALUES (?,?,?,?,?,?,?,?)',[(full_user,l['id'],l['lineCount'],(1<<l['lineCount'])-1,now,now+86400000,0,now) for l in ALL_LESSONS])
db.commit();db.close()
full=call(user=full_user)
assert len(full['rows'])==4006 and full['counts']=={'words':6351,'sentences':8154,'completed':4006}
passed('a complete 4006-lesson history returns exact totals without a client-side corpus index')
report={'scope':'local built production Worker with local D1; not a live phone/desktop test','passed':len(checks),'checks':checks,'browserQA':'see docs/browser-qa.json','webMCPQA':'see docs/browser-qa.json'}
(ROOT/'docs/progress-tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
