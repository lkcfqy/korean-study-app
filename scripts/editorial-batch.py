"""Display and record bounded bilingual review batches; a human/AI editor reads them."""
import argparse,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1];CACHE=ROOT/'.sites-runtime/corpus'
p=argparse.ArgumentParser();p.add_argument('start',type=int);p.add_argument('end',type=int);p.add_argument('--record',action='store_true');args=p.parse_args()
ds=json.loads((CACHE/'selected-dialogues.json').read_text());tr={r['id']:r for r in map(json.loads,(CACHE/'translations-plain.jsonl').read_text().splitlines())}
ed=json.loads((ROOT/'content/editorial-overrides.json').read_text());ex=json.loads((ROOT/'content/source-exclusions.json').read_text())
for f in sorted((ROOT/'content/editorial-batches').glob('*.json')):
 for k,v in json.loads(f.read_text()).items():ed[k]={'translations':v}
batch=[d for d in ds[args.start:args.end] if d['id'] not in ex]
if args.record:
 with (ROOT/'docs/editorial-review-log.jsonl').open('a') as f:f.write(json.dumps({'start':args.start,'end':args.end,'dialogueIds':[d['id'] for d in batch],'sentenceCount':sum(len(d['lines']) for d in batch),'reviewer':'Codex AI editor, original Korean and complete Chinese read together','humanTeacherCertification':False},ensure_ascii=False,separators=(',',':'))+'\n')
 print('Recorded',len(batch),'dialogues')
else:
 for n,d in enumerate(ds[args.start:args.end],args.start):
  if d['id'] in ex:continue
  print(n,d['id'],' | '.join(d['lines']));print(' | '.join(ed.get(d['id'],tr[d['id']])['translations']))
