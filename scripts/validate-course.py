"""Validate release coverage. This does not certify semantic or spoken accuracy."""
import hashlib, json, pathlib, re, subprocess
ROOT = pathlib.Path(__file__).resolve().parents[1]
course = json.loads((ROOT/'content/course.json').read_text())
audio = json.loads((ROOT/'content/audio-manifest.json').read_text())
hangul = json.loads((ROOT/'content/hangul.json').read_text())
assert audio['voice'] == 'ko-KR-SunHiNeural'
ids, sentences, words, required = set(), set(), set(), set()
for i, lesson in enumerate(course):
    assert lesson['id'] == f'c{i+1:02d}' and lesson['stage'] == i//6
    assert len(lesson['lines']) == 6 and len(lesson['roles']) == 2
    for j, line in enumerate(lesson['lines']):
        assert line['id'] not in ids
        ids.add(line['id'])
        assert re.search('[가-힣]', line['ko']) and re.search('[\u4e00-\u9fff]', line['zh'])
        assert line['note'] and line['speakerIndex'] in (0,1)
        sentences.add(re.sub(r'[\s.!?。？！]','',line['ko']))
        assert line['audio'] == audio['entries'][line['ko']]['path']
        required.add(line['audio'])
        for word in line['words']:
            words.add(word['term'])
            assert word['zh'] and word['audio'] == audio['entries'][word['term']]['path']
            required.add(word['audio'])
    for line_index in (2,4):
        assert len({lesson['lines'][line_index]['zh'],lesson['lines'][0]['zh'],lesson['lines'][1]['zh']}) == 3
for entry in hangul:
    assert entry['audio']==audio['entries'][entry['syllable']]['path']
    required.add(entry['audio'])
durations=[]
for text, entry in audio['entries'].items():
    path=ROOT/'public'/entry['path'].lstrip('/')
    assert path.is_file() and path.stat().st_size==entry['bytes'] and entry['bytes']>=1000
    assert path.stem == hashlib.sha256(text.encode()).hexdigest()[:20]
    # CoreAudio inspection checks decodability and duration, not pronunciation.
    info=subprocess.run(['/usr/bin/afinfo',str(path)],capture_output=True,text=True,check=True).stdout
    match=re.search(r'estimated duration:\s+([0-9.]+)',info)
    assert match and float(match.group(1))>0.1
    durations.append(float(match.group(1)))
report={'lessons':len(course),'dialogueRows':len(ids),'uniqueSentences':len(sentences),'uniqueCoreEntries':len(words),'voice':audio['voice'],'audioFiles':len(audio['entries']),'requiredAudioReferences':len(required),'audioDurationSeconds':round(sum(durations),2),'missingAudio':0,'structuralValidation':'passed','semanticReview':'author self-review only; no independent bilingual review','audioListeningReview':'not performed','mobileDeviceQA':'pending','fullSixMonthCurriculum':'not complete'}
(ROOT/'docs/content-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
