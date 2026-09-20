"""Integration test for an explicitly local built Worker, using isolated test identities."""
import concurrent.futures, json, pathlib, sqlite3, time, urllib.request, urllib.error, uuid
ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:8787'
USER='qa_'+uuid.uuid4().hex
LESSONS=json.loads((ROOT/'content/course.json').read_text())
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
    return json.loads(raw)
def passed(name): checks.append(name)
call(user=None,expected=401);call({'action':'select','lessonId':'c01'},user=None,expected=401);passed('anonymous reads and writes rejected')
call({'action':'select','lessonId':'c01'},origin='https://invalid.example',expected=403);passed('cross-origin write rejected')
call({'action':'select','lessonId':'c02'},expected=403);passed('locked lesson enforced on server')
call({'action':'read','lessonId':'c01','lineIndex':4},expected=409);passed('unread dialogue cannot be skipped')
call({'action':'complete','lessonId':'c01','answers':[0,1]},expected=409);passed('unread lesson cannot be completed')
call({'action':'read','lessonId':'c01','lineIndex':31},expected=400);passed('invalid requests rejected')
for n,lesson in enumerate(LESSONS):
    call({'action':'select','lessonId':lesson['id']})
    for i in range(6):call({'action':'read','lessonId':lesson['id'],'lineIndex':i})
    if n==0:
        call({'action':'complete','lessonId':lesson['id'],'answers':[2,2]},expected=422)
        assert call()['rows'][0]['completed_at'] is None
        passed('wrong answer does not unlock lesson')
    payload={'action':'complete','lessonId':lesson['id'],'answers':[n%3,(n+1)%3]}
    result=call(payload)
    record=next(r for r in result['rows'] if r['lesson_id']==lesson['id'])
    assert record['completed_at'] and record['read_mask']==63
    duplicate=call(payload)
    row2=next(r for r in duplicate['rows'] if r['lesson_id']==lesson['id'])
    assert record['next_review_at']==row2['next_review_at'] and record['review_step']==row2['review_step']
passed('all 36 lessons save, assess, unlock, and resume')
passed('duplicate completion does not inflate review schedule')
assert len(call()['rows'])==36 and call()['currentLesson']=='c36'
assert call(user=USER+'_other')['rows']==[];passed('two user identities have isolated progress')
# Every HTTP request uses a new client connection; rereads must come from durable D1 state.
assert all(r['read_mask']==63 for r in call()['rows']);passed('fresh sessions restore durable progress')
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
payload={'action':'complete','lessonId':'c01','answers':[0,1]}
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
report={'scope':'local built production Worker with local D1; not a live phone/desktop test','passed':len(checks),'checks':checks,'browserQA':'unavailable: CUA localhost navigation blocked','webMCPQA':'unavailable: no supported browser context'}
(ROOT/'docs/progress-tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
