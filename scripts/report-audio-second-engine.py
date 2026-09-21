"""Keep independent ASR agreement separate from phonetic certification."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
baseline_path = ROOT / 'docs/audio-inventory-screen.jsonl'
targets = [r for r in map(json.loads, baseline_path.read_text().splitlines())
           if r['status'] == 'unresolved_transcription_difference']
raw_path = ROOT / '.sites-runtime/corpus/audio-sensevoice-review.jsonl'
records = {(r['file'], r['sha256']): r for r in map(json.loads, raw_path.read_text().splitlines())}
evidence = []
for target in targets:
    row = records.get((target['file'], target['sha256']))
    if row is None:
        continue
    assert row['expectedTextProvidedToRecognizer'] is False
    assert row['text'] == target['text']
    assert hashlib.sha256((ROOT / 'content/audio' / row['file']).read_bytes()).hexdigest() == row['sha256']
    evidence.append({**row, 'use': target['use'], 'whisperBestTranscript': target['bestTranscript'],
                     'classification': 'independent_transcript_match' if row['similarity'] == 1 else 'difference_persists'})
out = ROOT / 'docs/audio-second-engine-screen.jsonl'
out.write_text(''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n' for r in evidence))
counts = collections.Counter(r['classification'] for r in evidence)
by_use = {use: dict(collections.Counter(r['classification'] for r in evidence if r['use'] == use))
          for use in sorted({r['use'] for r in evidence})}
models = sorted({(r['model'], r['modelRevision'], r['weightsSha256']) for r in evidence})
report = {
    'targetWhisperDifferences': len(targets), 'currentHashBoundSecondEngineReviews': len(evidence),
    'allTargetClipsProcessed': len(evidence) == len(targets),
    'classification': dict(counts), 'classificationByUse': by_use,
    'notYetProcessed': len(targets) - len(evidence),
    'models': [{'name': m, 'revision': v, 'weightsSha256': h} for m, v, h in models],
    'source': 'https://huggingface.co/FunAudioLLM/SenseVoiceSmall',
    'runtime': 'FunASR 1.4.16, CPU, language=ko, use_itn=False, isolated clips, batch size 8',
    'expectedTextProvidedToRecognizer': False,
    'recognitionRunsOnLocalDevice': True, 'publishedAudioFilesChanged': 0,
    'humanListeningReview': False, 'allPronunciationsCertified': False,
    'baselineEvidenceSha256': hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
    'evidenceFile': out.name, 'evidenceSha256': hashlib.sha256(out.read_bytes()).hexdigest(),
    'method': 'A separate non-Whisper model transcribes the audio without expected words. Compare afterward using the existing Korean text/numeral/unit normalizer. The original Whisper classifications remain intact; disagreement between recognizers is reported separately.',
    'limits': 'Independent transcript agreement is additional screening evidence, not a pronunciation repair or certification. Persistent differences may be synthesis or recognition errors. This targets only the previously unresolved clips, not a second complete pass over all 28,779 files.',
}
(ROOT / 'docs/audio-second-engine-review.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
