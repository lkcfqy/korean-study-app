"""Summarize blind ASR coverage of the exact release inventory."""
from course_data import load_course
import importlib.util
import json
import pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('speech_check',ROOT/'scripts/check-audio-transcription.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
course=load_course()
expected={s['ko'] for l in course for s in l['lines']}
records={r['text']:r for r in map(json.loads,(ROOT/'.sites-runtime/corpus/audio-transcription.jsonl').read_text().splitlines())}
decisions=json.loads((ROOT/'content/audio-review-decisions.json').read_text())
assert expected <= set(records)
low={s for s in expected if module.similarity_for(s,records[s]['recognized'])<.85}
assert low <= set(decisions), f'Unresolved recognition discrepancies: {low-set(decisions)}'
exclusions=json.loads((ROOT/'content/source-exclusions.json').read_text())
report={
    'sentenceAssetsChecked':len(expected),
    'expectedTextProvidedToRecognizer':False,
    'recognizer':'mlx-whisper large-v3-turbo',
    'method':'Initial grouped blind recognition; flagged clips rechecked in isolation. Compare punctuation/spacing-insensitive transcripts including numeric and unit spelling variants.',
    'screenThreshold':0.85,
    'withinScreenThreshold':len(expected)-len(low),
    'orthographicOrPhonologicalResolutions':len(low),
    'unresolvedBelowThresholdInPublishedCourse':0,
    'dialoguesExcludedForUncertainAudio':sum('Isolated audio recognition' in r for r in exclusions.values()),
    'humanListeningReview':False,
    'standaloneWordPronunciationReview':'Files decoded and signal checked; dictionary written pronunciations shown where available. No separate semantic ASR pass on isolated word clips.',
    'limitation':'A text similarity screen is not a phoneme-level pronunciation or prosody certificate, and does not establish zero speech errors.',
    'reviewedDiscrepancies':{s:decisions[s] for s in sorted(low)},
}
(ROOT/'docs/audio-transcription-tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='reviewedDiscrepancies'},ensure_ascii=False,indent=2))
