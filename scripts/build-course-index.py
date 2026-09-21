"""Publish per-dialogue assets and an exact, deduplicated progress index."""
from course_data import load_course
import hashlib
import json
import pathlib
from course_keys import sentence_key as key
from question_choices import QuestionChoices
from surface_readings import attach_surface_readings

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main():
    course = load_course()
    attach_surface_readings(course)
    foundation_path=ROOT/'content/foundation.json'
    foundation=json.loads(foundation_path.read_text())
    attach_surface_readings(foundation)
    foundation_path.write_text(json.dumps(foundation,ensure_ascii=False,indent=2)+'\n')
    positions_path=ROOT/'content/question-positions.json'
    positions=json.loads(positions_path.read_text()) if positions_path.exists() else {}
    overrides=json.loads((ROOT/'content/question-overrides.json').read_text())
    explanations=json.loads((ROOT/'content/question-explanations.json').read_text())
    choices=QuestionChoices(course,overrides)
    words = sorted({w['term'] for l in course for s in l['lines'] for w in s['words']})
    sentences = sorted({key(s['ko']) for l in course for s in l['lines']})
    wi, si = {w: i for i, w in enumerate(words)}, {s: i for i, s in enumerate(sentences)}
    directory = ROOT / 'public/course'
    directory.mkdir(parents=True, exist_ok=True)
    current_ids = {lesson['id'] for lesson in course}
    for previous in directory.glob('*.json'):
        if previous.stem not in current_ids:
            previous.unlink()
    index = []
    contrast_lessons = []
    for n, lesson in enumerate(course):
        assert 2 <= len(lesson['lines']) <= 30
        indices = [2, 4] if len(lesson['lines']) >= 6 else [0, len(lesson['lines']) - 1]
        if all(lesson['lines'][i]['id'] in overrides for i in indices):
            contrast_lessons.append(lesson['id'])
        questions = []
        for q, line_index in enumerate(indices):
            line = lesson['lines'][line_index]
            options = list(choices.distractors(lesson,line))
            assert len(options) == 2
            # Reordering the curriculum must not invalidate a quiz already
            # open on another device. Existing lessons retain their positions.
            answer = positions.get(lesson['id'],[int(hashlib.sha256((lesson['id']+str(i)).encode()).hexdigest()[:8],16)%3 for i in range(2)])[q]
            options.insert(answer, line['zh'])
            question={'lineIndex': line_index, 'options': options, 'answer': answer}
            if line['id'] in explanations:
                assert line['id'] in overrides, 'Explanations require reviewed contrast choices'
                question['explanation']=explanations[line['id']]
            questions.append(question)
        published = {**lesson, 'questions': questions}
        encoded = json.dumps(published, ensure_ascii=False, separators=(',', ':')) + '\n'
        (directory / f"{lesson['id']}.json").write_text(encoded)
        if n == 0:
            (ROOT / 'content/first-lesson.json').write_text(encoded)
        index.append({'id': lesson['id'], 'stage': lesson['stage'], 'title': lesson['title'],
                      'scene': lesson['scene'], 'day': lesson.get('day', lesson['stage'] * 30 + 1),
                      'lineCount': len(lesson['lines']),
                      'lineStats': [[si[key(s['ko'])], *sorted({wi[w['term']] for w in s['words']})]
                                    for s in lesson['lines']],
                      'answers': [q['answer'] for q in questions],
                      'revision': hashlib.sha256(encoded.encode()).hexdigest()[:12]})
    data = {'totalWords': len(words), 'totalSentences': len(sentences), 'lessons': index}
    (ROOT / 'content/course-index.json').write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
    catalog={'totalWords':len(words),'totalSentences':len(sentences),'lessons':[[l['id'],l['title'],l['day'],l['lineCount'],l['revision']] for l in index]}
    (ROOT/'content/course-catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,separators=(',',':'))+'\n')
    (ROOT/'content/contrast-lessons.json').write_text(json.dumps(contrast_lessons,separators=(',',':'))+'\n')
    print(json.dumps({'lessons': len(index), 'words': len(words), 'sentences': len(sentences),
                      'indexBytes': (ROOT / 'content/course-index.json').stat().st_size}))


if __name__ == '__main__':
    main()
