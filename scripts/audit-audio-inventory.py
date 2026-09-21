"""Hash-bound, resumable blind ASR over every released audio file.

This is a discrepancy screen, not a phonetic or human-listening certificate.
The expected text is used only after recognition, never in an ASR prompt.
"""
import argparse
import collections
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('speech_check', ROOT / 'scripts/check-audio-transcription.py')
speech = importlib.util.module_from_spec(spec)
spec.loader.exec_module(speech)
VERSION = 'blind-inventory-v1'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['grouped', 'isolated', 'repeat'], default='grouped')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--model', default=str(speech.MODEL))
    args = parser.parse_args()
    entries = json.loads((ROOT / 'content/audio-manifest.json').read_text())['entries']
    log = ROOT / '.sites-runtime/corpus/audio-inventory-review.jsonl'
    records = {}
    by_sound = collections.defaultdict(list)
    if log.exists():
        for line in log.read_text().splitlines():
            row = json.loads(line)
            records[(row['text'], row['sha256'], row['mode'], row['model'])] = row
            by_sound[(row['text'], row['sha256'])].append(row)
    inventory = []
    for text, entry in sorted(entries.items()):
        path = ROOT / 'content/audio' / Path(entry['path']).name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        key = (text, digest, args.mode, args.model)
        if key in records:
            continue
        if args.mode != 'grouped':
            existing = by_sound[(text, digest)]
            if not existing or any(r['similarity'] == 1 for r in existing):
                continue
        inventory.append((text, path, digest))
    if args.limit:
        inventory = inventory[:args.limit]
    started = time.monotonic()
    processed = 0
    flagged = 0
    print(f'{args.mode}: {len(inventory)} files pending; expected text is not supplied to ASR', flush=True)
    with log.open('a') as output:
        while processed < len(inventory):
            group, arrays, intervals = [], [], []
            duration = 0.0
            for text, path, digest in inventory[processed:]:
                samples = speech.decode(path)
                seconds = len(samples) / 16000
                if group and duration + seconds + .65 > 24:
                    break
                lead = np.zeros(3200, dtype=np.float32)
                tail = np.zeros(7200, dtype=np.float32)
                group.append((text, digest))
                intervals.append((duration + .2, duration + .2 + seconds))
                arrays.extend((lead, samples, tail))
                duration += seconds + .65
                if args.mode != 'grouped':
                    if args.mode == 'repeat':
                        arrays.extend((samples, tail, samples, tail))
                    break
            result = speech.mlx_whisper.transcribe(
                np.concatenate(arrays), path_or_hf_repo=args.model, language='ko',
                temperature=0, condition_on_previous_text=False,
                word_timestamps=args.mode == 'grouped', verbose=None,
            )
            words = [w for segment in result['segments'] for w in segment.get('words', [])]
            for (text, digest), (start, end) in zip(group, intervals):
                recognized = (''.join(w['word'] for w in words if start - .15 <= (w['start'] + w['end']) / 2 < end + .25).strip()
                              if args.mode == 'grouped' else result['text'].strip())
                similarity = speech.similarity_for(text, recognized)
                if args.mode == 'repeat':
                    similarity = max(similarity, speech.similarity_for(' '.join([text] * 3), recognized))
                row = {
                    'text': text, 'sha256': digest, 'recognized': recognized,
                    'similarity': round(similarity, 4), 'requiresReview': similarity < 1,
                    'mode': args.mode, 'model': args.model, 'methodVersion': VERSION,
                    'expectedTextProvidedToRecognizer': False,
                }
                output.write(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n')
                processed += 1
                flagged += similarity < 1
            output.flush()
            if processed % 100 < len(group) or processed == len(inventory):
                print(f'{args.mode}: {processed}/{len(inventory)}; {flagged} transcript differences; {time.monotonic()-started:.0f}s', flush=True)
    print('Finished', args.mode, processed, 'files', flush=True)


if __name__ == '__main__':
    main()
