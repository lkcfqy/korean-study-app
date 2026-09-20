"""Generate fixed SunHi assets. Run with Python and edge-tts installed."""
import asyncio, hashlib, json, pathlib
import edge_tts

ROOT = pathlib.Path(__file__).resolve().parents[1]
VOICE = 'ko-KR-SunHiNeural'
COURSE = json.loads((ROOT / 'content/course.json').read_text())
SYLLABLES = ['아','야','어','여','오','요','우','유','으','이','가','나','다','라','마','바','사','자','차','카','타','파','하','까','따','빠','싸','짜','애','에','얘','예','와','왜','외','워','웨','위','의','한','국','어']
texts = sorted(set(SYLLABLES + [line['ko'] for lesson in COURSE for line in lesson['lines']] + [w['term'] for lesson in COURSE for line in lesson['lines'] for w in line['words']]))
folder = ROOT / 'public/audio'
folder.mkdir(parents=True, exist_ok=True)
semaphore = asyncio.Semaphore(5)
done = 0

async def generate(text):
    global done
    key = hashlib.sha256(text.encode()).hexdigest()[:20]
    dest = folder / (key + '.mp3')
    async with semaphore:
        if not dest.exists() or dest.stat().st_size < 1000:
            for attempt in range(4):
                try:
                    temp = dest.with_suffix('.tmp')
                    await edge_tts.Communicate(text, VOICE, rate='+0%', pitch='+0Hz').save(str(temp))
                    if temp.stat().st_size < 1000:
                        raise ValueError('Audio is unexpectedly short')
                    temp.replace(dest)
                    break
                except Exception:
                    if attempt == 3:
                        raise
                    await asyncio.sleep(2 ** attempt)
        done += 1
        if done % 75 == 0:
            print(f'Generated {done}/{len(texts)} SunHi assets', flush=True)
    return text, {'path':'/audio/' + dest.name, 'voice':VOICE, 'bytes':dest.stat().st_size}

async def main():
    entries = await asyncio.gather(*(generate(text) for text in texts))
    manifest = {'voice':VOICE, 'rate':'+0%', 'pitch':'+0Hz', 'entries':dict(entries), 'audioListeningReview':'pending'}
    (ROOT / 'content/audio-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(f'Complete: {len(entries)} SunHi assets', flush=True)

asyncio.run(main())
