"""Verify complete sentence-token readings and stage only missing delivery files.

Every previous asset keeps its URL and bytes. New surface-form clips ship as
static MP3s; older clips keep their established static/R2 delivery path.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from course_data import load_course
from surface_readings import surface_reading

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--baseline-ref',required=True)
parser.add_argument('--stage-new',action='store_true')
parser.add_argument('--include-lexical-additions',action='store_true',help='Also allow current sentence and lemma assets in addition to surface forms.')
args=parser.parse_args()
baseline=json.loads(subprocess.check_output(['git','show',args.baseline_ref+':content/audio-manifest.json'],cwd=ROOT))
old_index=json.loads(subprocess.check_output(['git','show',args.baseline_ref+':content/audio-storage-index.json'],cwd=ROOT))
manifest=json.loads((ROOT/'content/audio-manifest.json').read_text())
entries=manifest['entries']
surface_inputs=json.loads((ROOT/'content/surface-audio-inputs.json').read_text())
assert not manifest['failedTexts']
assert manifest['voice']==baseline['voice']=='ko-KR-SunHiNeural'
assert all(entries[text]==entry for text,entry in baseline['entries'].items()),'Existing audio must not be overwritten'
for text,recipe in surface_inputs.items():
    assert text not in baseline['entries'],'Surface repairs must preserve previous audio URLs and bytes'
    assert entries[text]['inputText']==recipe['inputText']
    assert entries[text].get('contextClip')==recipe.get('contextClip')

parts=[(line['id'],part) for lesson in load_course(prefer_cache=False) for line in lesson['lines'] for part in line['parts']]
terms=collections.Counter()
different_from_lemmas=0
for line_id,part in parts:
    reading=part['surfaceReading']
    assert reading==surface_reading(part['text']),(line_id,part['text'])
    assert entries[reading['term']]['path']==reading['audio'],(line_id,part['text'])
    terms[reading['term']]+=1
    different_from_lemmas+=not any(r['term']==reading['term'] for r in part['readings'])

new_entries={text:entry for text,entry in entries.items() if text not in baseline['entries']}
lexical={s['ko'] for l in load_course(prefer_cache=False) for s in l['lines']}|{w['term'] for l in load_course(prefer_cache=False) for s in l['lines'] for w in s['words']}
assert set(new_entries)<=set(terms)|(lexical if args.include_lexical_additions else set()),'Unexpected audio additions'
new_bytes=0
for text,entry in entries.items():
    filename=Path(entry['path']).name
    source=ROOT/'content/audio'/filename
    data=source.read_bytes()
    assert len(data)==entry['bytes']>=1000,(text,'incomplete MP3')
    assert filename==hashlib.sha256(text.encode()).hexdigest()[:20]+'.mp3'
    if text in baseline['entries']:
        assert hashlib.sha256(data).hexdigest()==old_index[filename]['sha256'],(text,'previous audio changed')
    else:
        new_bytes+=len(data)
        cached=ROOT/'public/audio'/filename
        if args.stage_new:
            if cached.exists():assert cached.read_bytes()==data
            else:shutil.copyfile(source,cached)
        assert cached.is_file() and cached.read_bytes()==data,(text,'new audio not staged for delivery')

report={
    'baselineRef':args.baseline_ref,
    'clickableParts':len(parts),
    'partsWithCompleteSurfaceReading':sum(terms.values()),
    'uniqueSurfaceForms':len(terms),
    'partsWhosePreviousReadingsOmittedTheFullForm':different_from_lemmas,
    'newSurfaceAudioFiles':len(set(new_entries)&set(terms)),
    'newOtherAudioFiles':len(set(new_entries)-set(terms)),
    'reusedSurfaceAudioFiles':len(terms)-len(set(new_entries)&set(terms)),
    'newAudioBytes':new_bytes,
    'contextDerivedSurfaceClips':sum('contextClip' in e for e in new_entries.values()),
    'preservedPreviousAudioFiles':len(baseline['entries']),
    'missingSurfaceAudio':0,
    'newAudioStagedByteExactly':True,
    'voice':manifest['voice'],
    'method':'Synthesize the full written sentence-token form including particles and conjugated endings; remove surrounding quotation/sentence punctuation only. Keep lemma buttons separate.',
    'limits':'Most clips are separately synthesized full forms; recorded contextClip exceptions derive from hash-locked published sentence audio. Use full-sentence playback for cross-word liaison and sentence intonation. Structural and file checks do not certify pronunciation or human listening coverage.',
}
(ROOT/'docs/surface-audio-coverage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
