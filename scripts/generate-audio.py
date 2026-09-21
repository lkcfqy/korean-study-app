"""Generate fixed SunHi assets. Run with Python and edge-tts installed."""
from course_data import load_course
from surface_readings import surface_term,render_context_clip
import argparse, asyncio, hashlib, json, pathlib, time
import edge_tts

ROOT = pathlib.Path(__file__).resolve().parents[1]
VOICE = 'ko-KR-SunHiNeural'
COURSE = load_course()
SYLLABLES = ['아','야','어','여','오','요','우','유','으','이','가','나','다','라','마','바','사','자','차','카','타','파','하','까','따','빠','싸','짜','애','에','얘','예','와','왜','외','워','웨','위','의','한','국','어']
texts = sorted(set(SYLLABLES + [line['ko'] for lesson in COURSE for line in lesson['lines']] + [w['term'] for lesson in COURSE for line in lesson['lines'] for w in line['words']] + [r['term'] for lesson in COURSE for line in lesson['lines'] for p in line['parts'] for r in p.get('readings',[])] + [surface_term(p['text']) for lesson in COURSE for line in lesson['lines'] for p in line['parts']]))
parser = argparse.ArgumentParser()
parser.add_argument('--include-selected', action='store_true')
parser.add_argument('--workers', type=int, default=5)
parser.add_argument('--only-surface-inputs', action='store_true', help='Regenerate only authored punctuation-adjusted surface clips.')
args = parser.parse_args()
assert 1 <= args.workers <= 8
surface_inputs=json.loads((ROOT/'content/surface-audio-inputs.json').read_text())
assert all(surface_term(record['inputText'])==text for text,record in surface_inputs.items())
if args.include_selected:
    selected = json.loads((ROOT / '.sites-runtime/corpus/selected-dialogues.json').read_text())
    texts = sorted(set(texts + [s for d in selected for s in d['lines']] + [w for d in selected for w in d['words']]))
folder = ROOT / 'content/audio'
folder.mkdir(parents=True, exist_ok=True)
semaphore = asyncio.Semaphore(args.workers)
done = 0
failures = []
started = time.monotonic()
# Keep existing assets available to older open tabs while adding corrected
# roots and standalone chunks. Course counts come from lessons, not this cache.
manifest_path=ROOT/'content/audio-manifest.json'
manifest_entries = json.loads(manifest_path.read_text())['entries'] if manifest_path.exists() else {}

def checkpoint():
    manifest = {'voice':VOICE, 'rate':'+0%', 'pitch':'+0Hz', 'entries':manifest_entries,
                'audioListeningReview':'not performed by a human; automated coverage in docs/audio-transcription-tests.json', 'requiredTexts':len(texts), 'failedTexts':failures}
    path = ROOT / 'content/audio-manifest.json'
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)

async def generate(text):
    global done
    key = hashlib.sha256(text.encode()).hexdigest()[:20]
    dest = folder / (key + '.mp3')
    input_text=surface_inputs.get(text,{}).get('inputText',text)
    context_clip=surface_inputs.get(text,{}).get('contextClip')
    async with semaphore:
        if not dest.exists() or dest.stat().st_size < 1000 or (text in surface_inputs and (manifest_entries.get(text,{}).get('inputText')!=input_text or manifest_entries.get(text,{}).get('contextClip')!=context_clip)):
            for attempt in range(7):
                try:
                    temp = dest.with_suffix('.tmp')
                    if context_clip:
                        render_context_clip(ROOT,context_clip,temp)
                    else:
                        await edge_tts.Communicate(input_text, VOICE, rate='+0%', pitch='+0Hz').save(str(temp))
                    if temp.stat().st_size < 1000:
                        raise ValueError('Audio is unexpectedly short')
                    temp.replace(dest)
                    break
                except Exception as error:
                    if attempt == 6:
                        failures.append({'text':text,'error':str(error)[:200]})
                        print(f'Failed: {text}', flush=True)
                        return
                    await asyncio.sleep(min(30, 2 ** attempt))
        done += 1
        manifest_entries[text] = {'path':'/audio/' + dest.name, 'voice':VOICE, 'bytes':dest.stat().st_size}
        if text in surface_inputs:
            manifest_entries[text]['inputText']=input_text
        if context_clip:
            manifest_entries[text]['contextClip']=context_clip
        if done % 75 == 0:
            checkpoint()
            print(f'Generated {done}/{len(texts)} SunHi assets; elapsed {round(time.monotonic()-started)}s', flush=True)

async def main():
    targets=[text for text in texts if text in surface_inputs] if args.only_surface_inputs else texts
    await asyncio.gather(*(generate(text) for text in targets))
    checkpoint()
    print(f'Complete: {done} SunHi assets; failures {len(failures)}', flush=True)
    if failures:
        raise SystemExit(1)

asyncio.run(main())
