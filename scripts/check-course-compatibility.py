"""Check course revisions against the IDs used by existing cloud progress."""
import argparse
import io
import json
import pathlib
import subprocess

ROOT=pathlib.Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--baseline-ref',required=True)
args=parser.parse_args()

def read(path):return json.loads((ROOT/path).read_text())

baseline=json.loads(subprocess.check_output(['git','show',args.baseline_ref+':content/course-index.json'],cwd=ROOT))
current=read('content/course-index.json')
old_meta={l['id']:l for l in baseline['lessons']}
new_meta={l['id']:l for l in current['lessons']}
assert old_meta.keys()==new_meta.keys(), 'Existing lesson IDs must remain available.'
edits=read('content/context-editorial.json')
paths=['public/course/'+identity+'.json' for identity in old_meta]
request=''.join(args.baseline_ref+':'+path+'\n' for path in paths)
result=subprocess.run(['git','cat-file','--batch'],input=request.encode(),stdout=subprocess.PIPE,check=True,cwd=ROOT)
stream=io.BytesIO(result.stdout)
ko_changes=[];zh_changes=[];line_count=0
for path in paths:
    header=stream.readline().decode().split()
    assert len(header)==3 and header[1]=='blob', path
    old=json.loads(stream.read(int(header[2])));assert stream.read(1)==b'\n'
    new=read(path)
    assert [s['id'] for s in old['lines']]==[s['id'] for s in new['lines']], path
    assert [q['answer'] for q in old['questions']]==[q['answer'] for q in new['questions']], path
    for before,after in zip(old['lines'],new['lines']):
        identity=before['id'];line_count+=1
        assert before['speakerIndex']==after['speakerIndex'], identity
        for field,changes in [('ko',ko_changes),('zh',zh_changes)]:
            if before[field]!=after[field]:
                assert edits.get(identity,{}).get(field)==after[field], (identity,'unrecorded text change')
                changes.append({'id':identity,'before':before[field],'after':after[field]})
        if before['ko']==after['ko']:assert before['audio']==after['audio'], identity

report={'baselineRef':args.baseline_ref,'lessons':len(new_meta),'lineIdsAndOrderPreserved':line_count,
        'quizAnswerPositionsPreserved':True,'speakerAssignmentsPreserved':True,
        'koreanTextCorrections':ko_changes,'chineseTextCorrections':zh_changes,
        'scope':'Source compatibility; durable database behavior is tested separately in progress-tests.json.'}
(ROOT/'docs/course-compatibility.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in {'koreanTextCorrections','chineseTextCorrections'}}|
                 {'koreanCorrections':len(ko_changes),'chineseCorrections':len(zh_changes)},ensure_ascii=False))
