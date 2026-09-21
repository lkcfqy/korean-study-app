"""Independent, blind SenseVoice screening of unresolved Whisper differences.

Expected text is only compared after recognition. Audio is never rewritten.
Install FunASR and its dependencies in a separate audit environment; model
weights stay outside the application. Run report-audio-second-engine.py after.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import time

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'FunAudioLLM/SenseVoiceSmall'
MODEL_DIR = ROOT / '.sites-runtime/models/sensevoice-small'
VERSION = 'sensevoice-blind-ko-v1'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--batch-size', type=int, default=8)
    args = parser.parse_args()
    revision = (MODEL_DIR / 'review-revision.txt').read_text().strip()
    weights_hash = hashlib.sha256((MODEL_DIR / 'model.pt').read_bytes()).hexdigest()
    output = ROOT / '.sites-runtime/corpus/audio-sensevoice-review.jsonl'
    previous = {}
    if output.exists():
        previous = {(r['file'], r['sha256'], r['methodVersion'], r['modelRevision']): r
                    for r in map(json.loads, output.read_text().splitlines())}
    candidates = [r for r in map(json.loads, (ROOT / 'docs/audio-inventory-screen.jsonl').read_text().splitlines())
                  if r['status'] == 'unresolved_transcription_difference']
    pending = [r for r in candidates if (r['file'], r['sha256'], VERSION, revision) not in previous]
    if args.limit:
        pending = pending[:args.limit]
    if not pending:
        print('All target clips already have current evidence.', flush=True)
        return
    spec = importlib.util.spec_from_file_location('speech', ROOT / 'scripts/check-audio-transcription.py')
    speech = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(speech)
    import torch
    from funasr import AutoModel
    torch.set_num_threads(4)
    model = AutoModel(model=str(MODEL_DIR), device='cpu', ncpu=4,
                      disable_update=True, disable_pbar=True, disable_log=True)
    started = time.monotonic()
    print(f'{len(pending)} clips; blind Korean recognition; no expected words or hotwords', flush=True)
    with output.open('a') as out:
        for offset in range(0, len(pending), args.batch_size):
            batch = pending[offset:offset + args.batch_size]
            samples = []
            for row in batch:
                path = ROOT / 'content/audio' / row['file']
                assert hashlib.sha256(path.read_bytes()).hexdigest() == row['sha256']
                samples.append(speech.decode(path))
            results = model.generate(input=samples, cache={}, language='ko',
                                     use_itn=False, batch_size=args.batch_size,
                                     disable_pbar=True, disable_log=True)
            assert len(results) == len(batch), 'Recognition output must map one-to-one to files'
            for row, result in zip(batch, results):
                raw = result['text']
                recognized = re.sub(r'<\|[^|]*\|>', '', raw).strip()
                similarity = speech.similarity_for(row['text'], recognized)
                record = {
                    'text': row['text'], 'file': row['file'], 'sha256': row['sha256'],
                    'recognized': recognized, 'rawRecognition': raw,
                    'similarity': round(similarity, 4), 'model': MODEL,
                    'modelRevision': revision, 'weightsSha256': weights_hash,
                    'methodVersion': VERSION, 'expectedTextProvidedToRecognizer': False,
                    'languageHint': 'ko', 'humanListeningReview': False,
                }
                out.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n')
            out.flush()
            count = offset + len(batch)
            if count % 100 < args.batch_size or count == len(pending):
                print(f'SenseVoice {count}/{len(pending)}; {time.monotonic()-started:.0f}s', flush=True)


if __name__ == '__main__':
    main()
