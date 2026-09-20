"""Import reusable NIKL text, preserving sense IDs, Chinese glosses and dialogues.

The upstream 2023-09-01 export is mirrored by 71/study-korean. NIKL text is
CC BY-SA 2.0 KR; audio from that dictionary is deliberately not downloaded.
This imports source data, not reviewed/translated lessons.
"""
import collections
import hashlib
import html
import json
import pathlib
import re
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / '.sites-runtime/corpus'


def many(x):
    return x if isinstance(x, list) else ([x] if x else [])


def features(x):
    if isinstance(x, list):
        return {k: v for item in reversed(x) for k, v in features(item).items()}
    return {f['att']: html.unescape(str(f['val'])).strip()
            for f in many(x.get('feat')) if 'att' in f and 'val' in f}


def main():
    dictionary, dialogues = [], []
    archive = CACHE / 'kodict.zip'
    with zipfile.ZipFile(archive) as z:
        for name in sorted(z.namelist()):
            if not name.endswith('.json'):
                continue
            entries = json.loads(z.read(name))['LexicalResource']['Lexicon']['LexicalEntry']
            for entry in entries:
                f = features(entry)
                term = features(entry['Lemma']).get('writtenForm', '')
                if not term:
                    continue
                senses = []
                for sense in many(entry.get('Sense')):
                    zh = next((features(e) for e in many(sense.get('Equivalent'))
                               if features(e).get('language') == '중국어'), {})
                    if not zh.get('definition'):
                        continue
                    sid = str(sense.get('val', len(senses) + 1))
                    sf = features(sense)
                    senses.append({'id': sid, 'zh': zh.get('lemma', ''),
                                   'definition': zh['definition'],
                                   'koDefinition': sf.get('definition', '')})
                    for number, example in enumerate(many(sense.get('SenseExample'))):
                        ef = features(example)
                        if ef.get('type') != '대화':
                            continue
                        lines = [html.unescape(str(x['val'])).strip()
                                 for x in many(example.get('feat')) if x.get('att') == 'example']
                        if len(lines) < 2 or len(lines) > 8:
                            continue
                        if any(not re.search('[가-힣]', s) or len(s) > 200 for s in lines):
                            continue
                        dialogues.append({'id': f"n{entry['val']}-{sid}-{number}",
                                          'entryId': str(entry['val']), 'term': term,
                                          'senseId': sid, 'zh': zh.get('lemma', ''),
                                          'definition': zh['definition'],
                                          'level': f.get('vocabularyLevel', '없음'),
                                          'category': f.get('semanticCategory', ''),
                                          'topic': f.get('subjectCategiory', f.get('subjectCategory', '')),
                                          'lines': lines})
                if senses:
                    pronunciations = [features(w).get('pronunciation', '')
                                      for w in many(entry.get('WordForm'))
                                      if features(w).get('type') == '발음']
                    dictionary.append({'id': str(entry['val']), 'term': term,
                                       'pos': f.get('partOfSpeech', ''),
                                       'level': f.get('vocabularyLevel', '없음'),
                                       'category': f.get('semanticCategory', ''),
                                       'pronunciation': [p for p in pronunciations if p],
                                       'senses': senses})
            print(f'Imported {name}: {len(dictionary)} entries, {len(dialogues)} dialogues', flush=True)
    for name, data in [('nikl-dictionary', dictionary), ('nikl-dialogues', dialogues)]:
        (CACHE / f'{name}.json').write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')))
    report = {'source': 'National Institute of Korean Language, Korean Basic Dictionary',
              'sourceDate': '2023-09-01', 'mirror': 'https://github.com/71/study-korean/blob/master/data/kodict.zip',
              'license': 'https://creativecommons.org/licenses/by-sa/2.0/kr/',
              'archiveSha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
              'entries': len(dictionary), 'dialogues': len(dialogues),
              'levels': dict(collections.Counter(x['level'] for x in dictionary)),
              'scope': 'Dictionary Chinese senses are source translations. Dialogue Chinese translations are not in the source.'}
    (CACHE / 'nikl-source.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
