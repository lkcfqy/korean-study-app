"""Report hash-bound blind transcription evidence without claiming perfect speech."""
import collections
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'content/audio-manifest.json').read_text())['entries']
storage=json.loads((ROOT/'content/audio-storage-index.json').read_text())
dialogue_texts={line['ko'] for path in (ROOT/'public/course').glob('*.json')
                for line in json.loads(path.read_text())['lines']}
rows=collections.defaultdict(dict)
for line in (ROOT/'.sites-runtime/corpus/audio-inventory-review.jsonl').read_text().splitlines():
    r=json.loads(line)
    if r.get('expectedTextProvidedToRecognizer') is False:
        rows[(r['text'],r['sha256'])][(r['mode'],r['model'])]=r
phonetic=set()
for line in (ROOT/'.sites-runtime/corpus/audio-phonetic-review.jsonl').read_text().splitlines():
    r=json.loads(line)
    if r['phoneticMatch'] and r.get('methodVersion')=='g2pkiwi-0.1.0-kiwi-cong-strict-v1':
        phonetic.add((r['text'],r['sha256'],r['recognized'],r['mode']))
counts=collections.Counter();modes=collections.Counter();evidence=[]
by_use=collections.defaultdict(collections.Counter)
for text,entry in sorted(manifest.items()):
    name=Path(entry['path']).name;digest=storage[name]['sha256']
    assert hashlib.sha256((ROOT/'content/audio'/name).read_bytes()).hexdigest()==digest
    trials=list(rows[(text,digest)].values())
    assert trials,('Current file has no blind transcription record',text)
    modes.update({r['mode'] for r in trials})
    best=max(trials,key=lambda r:r['similarity'])
    exact=best['similarity']==1
    sound=any((text,digest,r['recognized'],r['mode']) in phonetic for r in trials)
    status='transcript_match' if exact else 'strict_normalizer_agreement_only' if sound else 'unresolved_transcription_difference'
    counts[status]+=1
    use='dialogue_line' if text in dialogue_texts else 'word_form_lemma_or_alphabet'
    by_use[use][status]+=1
    evidence.append({'text':text,'file':name,'sha256':digest,'status':status,
                     'use':use,
                     'bestTextSimilarity':best['similarity'],'bestTranscript':best['recognized'],
                     'modes':sorted({r['mode'] for r in trials})})
out=ROOT/'docs/audio-inventory-screen.jsonl'
out.write_text(''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\n' for r in evidence))
report={'inventoryFiles':len(manifest),'filesWithCurrentHashBoundBlindASR':len(evidence),
        'expectedTextProvidedToRecognizer':False,'coverageByMode':dict(modes),'classification':dict(counts),
        'classificationByUse':{use:dict(count) for use,count in by_use.items()},
        'inventoryIndexSha256':hashlib.sha256((ROOT/'content/audio-storage-index.json').read_bytes()).hexdigest(),
        'evidenceSha256':hashlib.sha256(out.read_bytes()).hexdigest(),'evidenceFile':out.name,
        'humanListeningReview':False,'allPronunciationsCertified':False,
        'method':'Blind Whisper large-v3-turbo; grouped clips followed by isolated discrepancy checks. Numeric/unit variants are normalized after recognition. Strict g2p comparison does not merge vowel classes.',
        'limits':'Transcription differences, especially short isolated words, are unresolved screening signals, not confirmed synthesis errors. Transcript or normalizer agreement cannot certify phonemes, naturalness, prosody or listening comprehension. The evidence is a snapshot of completed checks only.'}
(ROOT/'docs/audio-inventory-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
