"""Validate release inventory, annotations, provenance and audio references.

Structural checks do not certify language semantics or human listening quality.
"""
from course_data import load_course
import hashlib
import json
import pathlib
import re
from course_keys import sentence_key
from context_grammar import number_meaning

ROOT = pathlib.Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / name).read_text())


course = load_course(prefer_cache=False)
index = read('content/course-index.json')
audio = read('content/audio-manifest.json')
audio_storage = read('content/audio-storage-index.json')
hangul = read('content/hangul.json')
plan = read('content/study-plan.json')
foundation = read('content/foundation.json')
context_coverage=read('docs/context-annotation-coverage.json')
context_decisions=read('content/context-senses.json')
context_edits=read('content/context-editorial.json')
question_positions=read('content/question-positions.json')
excluded = read('content/source-exclusions.json')
review = [json.loads(row) for row in (ROOT / 'docs/editorial-review-log.jsonl').read_text().splitlines()]
reviewed = {identity for row in review for identity in row['dialogueIds']}
corrections = read('content/editorial-overrides.json')
for path in (ROOT / 'content/editorial-batches').glob('*.json'):
    corrections.update(json.loads(path.read_text()))
by_id = {lesson['id']: lesson for lesson in course}
by_meta = {m['id']: m for m in index['lessons']}
assert len(course) == len(by_id)
assert not set(by_id) & set(excluded)
assert set(by_id) <= reviewed, 'Every released dialogue needs a recorded bilingual review'
assert audio['voice'] == 'ko-KR-SunHiNeural' and not audio['failedTexts']
assert len(index['lessons']) == len(course)
assert {r['id'] for r in context_coverage}=={l['id'] for l in course if not l['id'].startswith('c')}, 'Partial annotation drafts cannot be released'
assert {r['id']:r['signature'] for r in context_coverage}=={r['id']:r['signature'] for r in context_decisions['records']}
assert not context_decisions['teacherCertification']

ids, sentences, words, required = set(), set(), set(), set()
for lesson in course:
    assert len(lesson['lines']) in (2, 6) and len(lesson['roles']) == 2
    assert lesson['stage'] == (lesson['day'] - 1) // 30
    assert 1 <= lesson['day'] <= 180 and lesson['day'] % 5
    if not lesson['id'].startswith('c'):
        assert lesson['source']['url'].startswith('https://krdict.korean.go.kr/chn/')
        assert lesson['source']['license'] == 'https://creativecommons.org/licenses/by-sa/2.0/kr/'
        assert lesson['sourceLevel']==['초급','중급','고급'][lesson['stage']//2]
    for line in lesson['lines']:
        assert line['id'] not in ids
        ids.add(line['id'])
        assert re.search('[가-힣]', line['ko']) and re.search('[\u4e00-\u9fff]', line['zh'])
        assert line['note'] and line['speakerIndex'] in (0, 1)
        assert line['parts'] and ' '.join(p['text'] for p in line['parts']) == ' '.join(line['ko'].split())
        assert all(p['meaning'] and p['explanation'] for p in line['parts'])
        assert not any('结合本句译文理解的构词成分' in p['explanation'] for p in line['parts'])
        assert all('词义参考' not in p['explanation'] for p in line['parts'])
        for part in line['parts']:
            assert part['readings'], (line['id'],part['text'],'missing clickable reading')
            for reading in part['readings']:
                assert reading['audio']==audio['entries'][reading['term']]['path']
                required.add(reading['audio'])
        if line['id'] in context_edits and 'zh' in context_edits[line['id']]:
            assert line['zh']==context_edits[line['id']]['zh']
        if line['id'] in context_edits and 'ko' in context_edits[line['id']]:
            assert line['ko']==context_edits[line['id']]['ko']
        sentences.add(sentence_key(line['ko']))
        assert line['audio'] == audio['entries'][line['ko']]['path']
        required.add(line['audio'])
        for word in line['words']:
            words.add(word['term'])
            assert word['zh'] and word['audio'] == audio['entries'][word['term']]['path']
            required.add(word['audio'])
    published = read('public/course/' + lesson['id'] + '.json')
    assert all(published[k] == v for k, v in lesson.items())
    meta = by_meta[lesson['id']]
    assert meta['lineCount'] == len(lesson['lines']) and len(meta['lineStats']) == len(lesson['lines'])
    for q in published['questions']:
        assert len(set(q['options'])) == 3
        assert q['options'][q['answer']] == lesson['lines'][q['lineIndex']]['zh']
    assert meta['answers'] == [q['answer'] for q in published['questions']]
    assert meta['answers']==question_positions[lesson['id']], 'Course reordering must preserve answers for already-open lessons'
    assert meta['revision'] == hashlib.sha256((ROOT / 'public/course' / (lesson['id'] + '.json')).read_bytes()).hexdigest()[:12]

# Existing IDs and content stay compatible with saved account progress.
for base in foundation:
    assert by_id[base['id']]['lines'] == base['lines']
    assert by_id[base['id']]['stage'] == base['stage']
assert {p.stem for p in (ROOT / 'public/course').glob('*.json')} == set(by_id)

# Regression examples for real learner-facing errors: derived words must have
# a lexical meaning, and a noun-modifying ending must not show a command sense.
advanced_parts = {p['text']: p for p in by_id['n57383-1-8']['lines'][0]['parts']}
assert '全球化' in advanced_parts['세계화']['meaning']
assert '迎接' in advanced_parts['맞이하여']['meaning']
assert '追求' in advanced_parts['추구해야']['meaning']
assert '可取' in advanced_parts['바람직한']['meaning']
assert '命令' not in advanced_parts['바람직한']['explanation']
assert '应该、必须' in advanced_parts['할']['meaning']
lines_by_id={s['id']:s for l in course for s in l['lines']}
def part_at(identity,index):return lines_by_id[identity]['parts'][index]
assert '是什么事' in part_at('n93441-1-5-1',1)['meaning']
assert '일（事情）' in part_at('n93441-1-5-1',1)['explanation']
assert '染上' in part_at('n63510-5-8-2',4)['meaning']
assert any(r['term']=='들다' for r in part_at('n63510-5-8-2',4)['readings'])
assert '非敬语' in part_at('n93441-1-5-2',3)['explanation']
assert '智秀' in part_at('n65234-2-6-1',1)['meaning'] and '指数' not in part_at('n65234-2-6-1',1)['explanation']
assert any(r['term']=='피다' for r in part_at('n73270-1-5-2',2)['readings'])
assert any(r['term']=='살다' for r in part_at('n62524-2-7-1',2)['readings'])
assert any(r['term']=='들다' for r in part_at('n30204-1-19-1',5)['readings'])
assert any(r['term']=='달다' for r in part_at('n62507-1-7-1',5)['readings'])
assert '买粮食' in part_at('n82837-11-7-2',5)['meaning']
assert '停学' in part_at('n58272-22-7-1',2)['meaning']
assert '曲调' in part_at('n20195-1-28-2',0)['meaning']
assert '最' in part_at('n31629-2-17-2',0)['meaning']
assert '未铺装' in part_at('n48602-1-8-2',0)['meaning']
assert '致死' not in part_at('n47384-3-5-1',1)['meaning']
assert '卑鄙' in part_at('n47384-3-5-1',1)['meaning']
assert '被解雇' in part_at('n72649-1-11-2',7)['meaning']
assert not any(r['term']=='않다' for r in part_at('n64618-1-9-2',4)['readings'])
assert lines_by_id['n56388-1-11-2']['ko']=='바느질하다가 바늘에 찔렸어.'
for text,expected in [('오백','500'),('이십사','24'),('스물다섯','25'),('열일곱','17'),('이천이십육','2026'),('일일구','119'),('일조','1000000000000'),('이만','20000')]:
    assert number_meaning(text).split('（')[0]==expected
assert all('不知失措' not in l['title'] for l in course)
assert len(sentences) == index['totalSentences'] >= 8000
assert len(words) == index['totalWords'] >= 6000
for entry in hangul:
    assert entry['audio'] == audio['entries'][entry['syllable']]['path']
    required.add(entry['audio'])
for text, entry in audio['entries'].items():
    path = ROOT / 'content/audio' / pathlib.Path(entry['path']).name
    assert path.is_file() and path.stat().st_size == entry['bytes'] >= 1000
    assert path.stem == hashlib.sha256(text.encode()).hexdigest()[:20]
    assert entry['voice'] == audio['voice']
    assert audio_storage[path.name] == {'bytes':entry['bytes'],'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
assert len(audio_storage) == len(audio['entries'])
for cached in (ROOT / 'public/audio').glob('*.mp3'):
    assert cached.read_bytes() == (ROOT / 'content/audio' / cached.name).read_bytes()
assert required <= {e['path'] for e in audio['entries'].values()}

assert [d['day'] for d in plan['days']] == list(range(1, 181))
assert all(sum(t['minutes'] for t in d['tasks']) == 240 for d in plan['days'])
assert all(d['newWords'] <= 60 for d in plan['days']), 'Avoid overloading any one day with novel vocabulary'
assert all(d['newWords'] <= 28 for d in plan['days'][:7]), 'Gentle first week'
assigned = [i for d in plan['days'] for i in d['lessonIds']]
assert len(assigned) == len(set(assigned)) == len(course) and set(assigned) == set(by_id)
seen_words, seen_sentences = set(), set()
for day in plan['days']:
    old_words, old_sentences = len(seen_words), len(seen_sentences)
    for identity in day['lessonIds']:
        lesson = by_id[identity]
        assert lesson['day'] == day['day']
        for line in lesson['lines']:
            seen_sentences.add(sentence_key(line['ko']))
            seen_words.update(w['term'] for w in line['words'])
    assert day['newWords'] == len(seen_words) - old_words
    assert day['newSentences'] == len(seen_sentences) - old_sentences
    assert day['cumulativeWords'] == len(seen_words)
    assert day['cumulativeSentences'] == len(seen_sentences)
    assert sum(len(by_id[i]['lines']) for i in day['lessonIds'])<=96
    review_days=list(range(max(1,day['day']-(4 if day['day']%5==0 else 1)),day['day']))+[day['day']-7,day['day']-30]
    assert set(day['reviewLessonIds'])=={l['id'] for l in course if l['day'] in review_days}
    assert day['reviewRows']==sum(len(by_id[i]['lines']) for i in day['reviewLessonIds'])
    assert day['reviewLessonIds']==list(dict.fromkeys(i for g in day['reviewGroups'] for i in g['lessonIds']))
    if day['day'] % 5 == 0:
        assert not day['lessonIds'] and day['newWords'] == day['newSentences'] == 0
        assert day['reviewLessonIds']
assert seen_words == words and seen_sentences == sentences
for month in plan['months']:
    last = plan['days'][month['endDay'] - 1]
    assert month['words'] == last['cumulativeWords'] and month['sentences'] == last['cumulativeSentences']
assert (ROOT / 'public/content-sources.html').exists()

report = {
    'lessons': len(course), 'dialogueRows': len(ids), 'uniqueSentences': len(sentences),
    'uniqueCoreEntries': len(words), 'annotatedSentences': len(ids),
    'annotatedParts': sum(len(s['parts']) for l in course for s in l['lines']),
    'annotationMethod': 'Original 216 rows have authored notes. Added dialogue uses source-constrained contextual sense selection, authored grammar, dictionary supplements, and recorded morphology/editorial repairs. Every chunk has a structured audio mapping. Automatic selection is not independent teacher certification.',
    'contextSelectionDialogues':len(context_coverage),
    'contextSelectionItems':sum(len(r['items']) for r in context_coverage),
    'explicitContextEdits':len(context_edits),
    'breakdownSemanticRegressions': 'passed: derived lemmas, noun-modifying endings, necessity, names vs homonyms, live vs buy, bloom vs country name, honorific eat, sweet vs close, grain-buying idiom, missing terms, numerals and source typo',
    'studyPlanDays': 180, 'studyPlanHours': 720, 'includesExternalMaterialsInCounts': False,
    'newWordsPerLearningDay': [min(d['newWords'] for d in plan['days'] if d['lessonIds']), max(d['newWords'] for d in plan['days'])],
    'voice': audio['voice'], 'audioFiles': len(audio['entries']),
    'requiredAudioReferences': len(required), 'missingAudio': 0, 'structuralValidation': 'passed',
    'bilingualReview': {'releasedDialoguesCovered': len(set(by_id) & reviewed),
                       'method': 'All complete Korean sentences and Chinese translations read together by Codex AI editor; source dictionary Chinese senses retained with attribution.',
                       'correctedPublishedDialoguePairs': len((set(by_id) - {b['id'] for b in foundation}) & set(corrections)),
                       'humanTeacherCertification': False},
    'excludedSourceDialogues': len(excluded),
    'audioReview': 'Baseline audio has prior decoding, signal and sentence-ASR reports. Baseline hashes are rechecked; newly added clips receive decoding/signal checks. One spelling-corrected sentence and new word/chunk clips are outside the baseline ASR report. No full human listening review.',
    'examOutcome': 'Course inventory and time commitment do not certify a TOPIK score.'
}
(ROOT / 'docs/content-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
