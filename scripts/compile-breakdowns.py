"""Attach editorial annotations only when they cover the exact source sentence."""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
course = json.loads((ROOT / 'content/foundation.json').read_text())
annotations = {}
for row in (ROOT / 'content/breakdowns.txt').read_text().splitlines():
    if not row or row.startswith('#'):
        continue
    line_id, body = row.split('\t', 1)
    assert line_id not in annotations, line_id
    parts = []
    for item in body.split('|'):
        text, meaning, explanation = item.split('~')
        assert text and meaning and explanation, line_id
        parts.append(dict(text=text, meaning=meaning, explanation=explanation))
    annotations[line_id] = parts

corrections = {
    'c04-4': ('不用，请给我冷的。', '차가운 表示温度低；句子没有明确要求加冰，所以不直接译成“加冰的”。'),
    'c20-3': ('口头报告和书面报告，哪个让你压力更大？', '课堂语境中 발표 指口头报告，보고서 指书面报告；중에 表示从若干对象中选择。'),
    'c20-4': ('目前还是口头报告更让我有压力。', '아직은 强调现阶段；발표 在这里指课堂上的口头报告。'),
    'c26-1': ('个性化服务提供便利的同时，也要求大量信息。', '만큼 在这里表达与便利相伴的信息要求，并不是在断言严格的“越……越……”因果规律。'),
}
seen = set()
for lesson in course:
    for line in lesson['lines']:
        parts = annotations[line['id']]
        assert ' '.join(p['text'] for p in parts) == line['ko'], (line['id'], line['ko'])
        line['parts'] = parts
        seen.add(line['id'])
        if line['id'] in corrections:
            line['zh'], line['note'] = corrections[line['id']]
        if line['id'] == 'c20-3':
            for word in line['words']:
                if word['term'] == '발표':
                    word['zh'] = '口头报告（课堂语境）'
assert seen == set(annotations), set(annotations) ^ seen
(ROOT / 'content/foundation.json').write_text(json.dumps(course, ensure_ascii=False, indent=2) + '\n')
# Keep the human-readable dialogue source aligned with the published data.
rows = []
for lesson in course:
    rows.append(f"# {lesson['stage']+1}|{lesson['title']}|{lesson['scene']}|{'|'.join(lesson['roles'])}")
    for line in lesson['lines']:
        terms = ';'.join(f"{w['term']}={w['zh']}" for w in line['words'])
        rows.append('|'.join([line['ko'], line['zh'], line['note'], terms]))
(ROOT / 'content/course-source.txt').write_text('\n'.join(rows) + '\n')
print(json.dumps({'annotatedSentences': len(seen), 'annotatedParts': sum(len(x) for x in annotations.values()), 'translationCorrections': list(corrections)}, ensure_ascii=False))
