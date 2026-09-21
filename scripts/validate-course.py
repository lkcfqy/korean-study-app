"""Validate release inventory, annotations, provenance and audio references.

Structural checks do not certify language semantics or human listening quality.
"""
from course_data import load_course
import argparse
import hashlib
import json
import pathlib
import re
from course_keys import sentence_key
from context_grammar import number_meaning
from surface_readings import surface_reading,surface_term

ROOT = pathlib.Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--metadata-only',action='store_true',help='Validate committed metadata without requiring local audio files; does not verify audio bytes.')
args=parser.parse_args()


def read(name):
    return json.loads((ROOT / name).read_text())


course = load_course(prefer_cache=False)
index = read('content/course-index.json')
catalog = read('content/course-catalog.json')
audio = read('content/audio-manifest.json')
surface_inputs = read('content/surface-audio-inputs.json')
audio_storage = read('content/audio-storage-index.json')
hangul = read('content/hangul.json')
plan = read('content/study-plan.json')
packed_plan = read('content/study-plan-client.json')
foundation = read('content/foundation.json')
context_coverage=read('docs/context-annotation-coverage.json')
context_decisions=read('content/context-senses.json')
context_edits=read('content/context-editorial.json')
question_positions=read('content/question-positions.json')
question_overrides=read('content/question-overrides.json')
contrast_lessons=read('content/contrast-lessons.json')
assert set(contrast_lessons)=={l['id'] for l in course if all(l['lines'][i]['id'] in question_overrides for i in ([2,4] if len(l['lines'])>=6 else [0,len(l['lines'])-1]))}
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
assert catalog['totalWords']==index['totalWords'] and catalog['totalSentences']==index['totalSentences']
assert catalog['lessons']==[[l['id'],l['title'],l['day'],l['lineCount'],l['revision']] for l in index['lessons']]
assert len(packed_plan['days'])==len(plan['days'])
for compact,original in zip(packed_plan['days'],plan['days']):
    decoded={**compact,'lessonIds':[catalog['lessons'][i][0] for i in compact['lessonIds']],
        'reviewGroups':[{'title':group['title'],'lessonIds':[catalog['lessons'][i][0] for i in group['lessonIds']]} for group in compact['reviewGroups']],
        'tasks':[{**packed_plan['taskCopies'][copy],'minutes':minutes} for minutes,copy in compact['tasks']]}
    assert all(value==original[key] for key,value in decoded.items()),original['day']
assert all(value==plan[key] for key,value in packed_plan.items() if key not in {'days','taskCopies'})
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
            assert part['surfaceReading']==surface_reading(part['text']), (line['id'],part['text'],'incomplete sentence-token pronunciation')
            surface=part['surfaceReading']
            assert surface['audio']==audio['entries'][surface['term']]['path']
            required.add(surface['audio'])
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
        question_line=lesson['lines'][q['lineIndex']]['id']
        if lesson['id'].startswith('c'):assert question_line in question_overrides
        if question_line in question_overrides:
            assert [text for i,text in enumerate(q['options']) if i!=q['answer']]==question_overrides[question_line]
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
assert '想买' not in part_at('n77610-1-10-1',6)['meaning']
assert part_at('n79167-2-7-1',1)['readings'][0]['term']=='하나'
assert '不太好' in part_at('n49297-1-7-2',3)['meaning']
assert '것 + 이' in part_at('n29724-1-13-1',4)['meaning']
assert part_at('n79167-2-7-1',5)['sources'][0]['senseId']=='1'
assert part_at('n58163-5-6-2',4)['readings'][0]['term']=='날'
assert part_at('n65234-2-6-1',3)['readings'][0]['term']=='아니다'
assert part_at('n85791-2-7-1',6)['readings'][0]['term']=='알다'
assert '33' in part_at('n70812-1-7-2',1)['meaning']
assert '李' in part_at('n64703-4-10-1',0)['meaning']
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
# Regressions for the actual false senses found in the product review.
assert '观看' in part_at('n71624-1-32-1',3)['meaning']
assert '观看' in part_at('n71624-1-32-2',7)['meaning']
assert any(s['entryId']=='82136' for s in part_at('n55498-1-7-1',4)['sources'])
assert '什么样' in part_at('n57383-1-8-1',9)['meaning']
assert any(r['term']=='듣다' for r in part_at('n15110-2-6-1',2)['readings'])
# Cases found by reading the actual dialogue, with controls for homographs and
# auxiliary constructions. Regeneration must not reintroduce these errors.
assert '四' in part_at('n34873-1-2-2',2)['meaning']
assert part_at('n69518-14-6-2',0)['readings'][0]['term']=='옴'
assert part_at('n49308-3-4-1',0)['sources'][0]['entryId']=='62156'
assert '尽可能' in part_at('n31952-2-2-2',2)['meaning']
assert '59' in part_at('n71105-2-7-2',1)['meaning']
assert '62' in part_at('n70813-1-7-2',2)['meaning']
assert part_at('n83344-3-5-2',2)['text'] == '삼사'
assert '34' not in part_at('n83344-3-5-2',2)['meaning']
assert '你的' not in part_at('n43832-1-23-2',1)['meaning']
assert part_at('n62391-1-14-2',9)['sources'][0]['senseId']=='8'
assert part_at('n62597-1-8-2',3)['sources'][0]['entryId']=='61346'
assert '原因' in part_at('n62597-1-8-2',3)['explanation']
assert '疑问句末' in part_at('n69533-1-13-1',4)['explanation']
assert '原因' not in part_at('n69533-1-13-1',4)['explanation']
assert part_at('n60201-4-7-1',8)['sources'][0]['entryId']=='62601'
assert part_at('n15765-1-7-1',2)['sources'][0]['senseId']=='2'
assert part_at('n67897-1-7-1',5)['readings'][0]['term']=='밝다'
assert '祝福' in part_at('n67897-1-7-2',5)['meaning']
assert not any(r['term']=='하다' for r in part_at('n74128-1-7-2',5)['readings'])
assert part_at('n30189-1-16-2',4)['sources'][0]['entryId']=='73815'
assert '踢足球' in part_at('n27821-1-7-2',1)['meaning']
assert part_at('n27821-1-7-2',1)['sources'][0]['entryId']=='36700'
assert '今年' in part_at('n71700-1-12-1',0)['meaning']
assert '线股' in part_at('n89458-7-6-1',0)['meaning']
assert '引用' not in part_at('n62508-1-8-2',3)['meaning']
assert '外面' in part_at('n71354-2-3-1',3)['meaning']
assert '位置' in part_at('n15631-3-6-2',2)['meaning']
assert '马上' in part_at('n70378-15-8-2',2)['meaning']
# Every recorded decision must survive regeneration, including legitimate
# auxiliary exceptions. This does not certify unreviewed semantic cases.
for decision in read('docs/context-safety-review.json')['decisions']:
    part=part_at(decision['lineId'],decision['part'])
    assert all(part['sources'][decision['item']][k]==v for k,v in decision['after'].items()),decision
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
    assert entry['bytes'] >= 1000
    if not args.metadata_only:assert path.is_file() and path.stat().st_size == entry['bytes']
    assert path.stem == hashlib.sha256(text.encode()).hexdigest()[:20]
    assert entry['voice'] == audio['voice']
    if 'inputText' in entry:assert surface_term(entry['inputText'])==text
    if 'contextClip' in entry:
        clip=entry['contextClip'];source_line=lines_by_id[clip['sourceLineId']]
        assert source_line['ko']==clip['sourceText']
        assert any(p['surfaceReading']['term']==text for p in source_line['parts'])
        source_file=ROOT/'content/audio'/pathlib.Path(source_line['audio']).name
        assert audio_storage[source_file.name]['sha256']==clip['sourceSha256']
        if not args.metadata_only:assert hashlib.sha256(source_file.read_bytes()).hexdigest()==clip['sourceSha256']
    assert audio_storage[path.name]['bytes']==entry['bytes']
    assert re.fullmatch('[a-f0-9]{64}',audio_storage[path.name]['sha256'])
    if not args.metadata_only:assert audio_storage[path.name]['sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
assert len(audio_storage) == len(audio['entries'])
for text,recipe in surface_inputs.items():
    assert audio['entries'][text]['inputText']==recipe['inputText']
    assert audio['entries'][text].get('contextClip')==recipe.get('contextClip')
for cached in (ROOT / 'public/audio').glob('*.mp3'):
    assert hashlib.sha256(cached.read_bytes()).hexdigest()==audio_storage[cached.name]['sha256']
assert required <= {e['path'] for e in audio['entries'].values()}

assert [d['day'] for d in plan['days']] == list(range(1, 181))
assert all(sum(t['minutes'] for t in d['tasks']) == 240 for d in plan['days'])
assert all(d['newWords'] <= 60 for d in plan['days']), 'Avoid overloading any one day with novel vocabulary'
assert all(d['newWords'] <= 24 for d in plan['days'][:7]), 'Gentle first week'
assert all(d['newWords'] <= 36 for d in plan['days'][7:14]), 'Gradual second week'
assert all(d['newWords'] <= 48 for d in plan['days'][:30]), 'First month vocabulary limit'
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
    'annotationMethod': 'Original 216 rows have authored notes. Added dialogue uses source-constrained contextual sense selection, authored grammar, dictionary supplements, and recorded morphology/editorial repairs. Every clickable chunk has a complete surface-form audio mapping, with lexical readings kept separately. Automatic selection is not independent teacher certification.',
    'surfacePronunciationParts': sum(len(s['parts']) for l in course for s in l['lines']),
    'uniqueSurfacePronunciations': len({p['surfaceReading']['term'] for l in course for s in l['lines'] for p in s['parts']}),
    'contextSelectionDialogues':len(context_coverage),
    'contextSelectionItems':sum(len(r['items']) for r in context_coverage),
    'explicitContextEdits':len(context_edits),
    'breakdownSemanticRegressions': 'passed: derived lemmas, noun-modifying endings, necessity, names vs homonyms, live vs buy, bloom vs country name, honorific eat, sweet vs close, grain-buying idiom, missing terms, numerals and source typo',
    'studyPlanDays': 180, 'studyPlanHours': 720, 'includesExternalMaterialsInCounts': False,
    'newWordsPerLearningDay': [min(d['newWords'] for d in plan['days'] if d['lessonIds']), max(d['newWords'] for d in plan['days'])],
    'voice': audio['voice'], 'audioFiles': len(audio['entries']),
    'requiredAudioReferences': len(required), 'audioBytesVerification': 'skipped: metadata-only mode' if args.metadata_only else 'all local files match manifest bytes and SHA-256', 'missingAudio': None if args.metadata_only else 0, 'structuralValidation': 'passed',
    'bilingualReview': {'releasedDialoguesCovered': len(set(by_id) & reviewed),
                       'method': 'All complete Korean sentences and Chinese translations read together by Codex AI editor; source dictionary Chinese senses retained with attribution.',
                       'correctedPublishedDialoguePairs': len((set(by_id) - {b['id'] for b in foundation}) & set(corrections)),
                       'humanTeacherCertification': False},
    'excludedSourceDialogues': len(excluded),
    'audioReview': 'Audio bytes and references are checked here. Hash-bound blind transcription coverage and unresolved differences are recorded separately in docs/audio-inventory-review.json. No full human listening review.',
    'examOutcome': 'Course inventory and time commitment do not certify a TOPIK score.'
}
(ROOT / ('docs/content-metadata-audit.json' if args.metadata_only else 'docs/content-audit.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
