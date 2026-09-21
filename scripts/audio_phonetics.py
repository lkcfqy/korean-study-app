"""Conservative, local spelling-to-sound comparison for ASR triage.

Equal outputs are a phonetic-normalizer agreement, not proof of pronunciation.
In particular, do not merge Korean vowel classes or accept fuzzy similarity.
"""
from functools import lru_cache
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'g2pkiwi-0.1.0-kiwi-cong-strict-v1'


@lru_cache(maxsize=1)
def converter():
    import nltk
    import kiwipiepy
    nltk.data.path.insert(0, str(ROOT / '.sites-runtime/nltk_data'))
    original = kiwipiepy.Kiwi

    # g2pkiwi 0.1.0 requests Kiwi's removed sbg model. Adapt that one import
    # to the installed 0.23 cong model, without modifying either package.
    def compatible(*args, **kwargs):
        if kwargs.get('model_type') == 'sbg':
            kwargs['model_type'] = 'cong'
        return original(*args, **kwargs)

    kiwipiepy.Kiwi = compatible
    try:
        from g2pkiwi import G2p
    finally:
        kiwipiepy.Kiwi = original
    return G2p()


@lru_cache(maxsize=65536)
def phonetic(text):
    text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', text).strip()
    if not text:
        return ''
    result = converter()(text, descriptive=False, group_vowels=False)
    return re.sub(r'[^가-힣a-zA-Z0-9]', '', result).lower()


def agrees(expected, recognized):
    expected_sound, recognized_sound = phonetic(expected), phonetic(recognized)
    return bool(expected_sound) and expected_sound == recognized_sound


if __name__ == '__main__':
    import argparse
    import json
    parser = argparse.ArgumentParser()
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test:
        for a, b in [('옷이', '오시'), ('같이', '가치'), ('들었을', '드러쓸'), ('무를', '물을')]:
            assert agrees(a, b), (a, b)
        for a, b in [('놨거든', '났거든'), ('비', '피'), ('안 가요', '가요'), ('기다려', '기다리'), ('세', '새')]:
            assert not agrees(a, b), (a, b)
        print('Strict sound-equivalence controls passed; this does not certify any clip.')
    else:
        source = ROOT / '.sites-runtime/corpus/audio-inventory-review.jsonl'
        target = ROOT / '.sites-runtime/corpus/audio-phonetic-review.jsonl'
        previous = {}
        if target.exists():
            for line in target.read_text().splitlines():
                row = json.loads(line)
                previous[(row['text'], row['sha256'], row['recognized'], row['mode'])] = row
        count = matches = 0
        with target.open('a') as output:
            for line in source.read_text().splitlines():
                row = json.loads(line)
                key = (row['text'], row['sha256'], row['recognized'], row['mode'])
                if row['similarity'] == 1 or key in previous:
                    continue
                expected, heard = phonetic(row['text']), phonetic(row['recognized'])
                match = bool(expected) and expected == heard
                result = {k: row[k] for k in ['text', 'sha256', 'recognized', 'mode']}
                result.update(expectedSound=expected, recognizedSound=heard,
                              phoneticMatch=match, methodVersion=VERSION)
                output.write(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n')
                count += 1
                matches += match
                if count % 1000 == 0:
                    output.flush()
                    print(f'{count} spelling differences compared; {matches} strict sound agreements', flush=True)
        print('Phonetic triage completed:', count, 'comparisons;', matches, 'strict agreements')
