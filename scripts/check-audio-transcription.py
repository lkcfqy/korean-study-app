"""Recognize complete sentence audio without giving ASR the expected transcript.

This is an automatic mismatch screen, not a human pronunciation/prosody review.
It waits for the active TTS build and checkpoints every processed group.
"""
import argparse
import difflib
import hashlib
import json
import pathlib
import re
import subprocess
import tempfile
import time
import wave
import numpy as np
from scipy.signal import resample_poly

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / '.sites-runtime/corpus'
MODEL = pathlib.Path.home()/'.cache/huggingface/hub/models--mlx-community--whisper-large-v3-turbo/snapshots/a4aaeec0636e6fef84abdcbe3544cb2bf7e9f6fb'


def transcribe(*args, **kwargs):
    import mlx_whisper
    return mlx_whisper.transcribe(*args, **kwargs)


def normal(text):
    return re.sub(r'[^가-힣a-zA-Z0-9]', '', text).lower()


def korean_number(n):
    n=int(n)
    if not n:return '영'
    if n>=10000:
        return (korean_number(n//10000) if n//10000>1 else '')+'만'+(korean_number(n%10000) if n%10000 else '')
    result=''
    for unit,name in [(1000,'천'),(100,'백'),(10,'십'),(1,'')]:
        digit,n=divmod(n,unit)
        if digit:result+=('일이삼사오육칠팔구'[digit-1] if digit>1 or unit==1 else '')+name
    return result


def similarity_for(expected,recognized):
    # ASR writes both native and Sino-Korean numerals as digits. Compare the
    # valid orthographic expansions; never supply expected words to the model.
    def variants(text):
        base=re.sub(r'(?<=\d),(?=\d{3}(?:\D|$))','',text)
        for unit,spoken in [('km','킬로미터'),('cm','센티미터'),('mm','밀리미터'),('kg','킬로'),('m','미터'),('TV','티브이'),('UFO','유에프오'),('%','퍼센트'),('℃','도')]:
            base=re.sub(re.escape(unit),spoken,base,flags=re.I)
        def number(match,mode):
            n=int(match.group())
            if mode and 0<n<100:
                tens=['','열','스물','서른','마흔','쉰','예순','일흔','여든','아흔']
                ones=['','하나','둘','셋','넷','다섯','여섯','일곱','여덟','아홉']
                if mode==2:ones[1:5]=['한','두','세','네']
                return ('스무' if mode==2 and n==20 else tens[n//10]+ones[n%10])
            if base[match.end():].lstrip().startswith('월') and n in {6,10}:return {6:'유',10:'시'}[n]
            return korean_number(n)
        return [text,base]+[re.sub(r'\d+',lambda m:number(m,mode),base) for mode in range(3)]
    return max(difflib.SequenceMatcher(None,normal(a),normal(b)).ratio() for a in variants(expected) for b in variants(recognized))


def decode(path):
    with tempfile.TemporaryDirectory(prefix='hangeul-asr-') as directory:
        target=pathlib.Path(directory)/'decoded.wav'
        subprocess.run(['/usr/bin/afconvert','-f','WAVE','-d','LEI16',str(path),str(target)],check=True,capture_output=True)
        with wave.open(str(target),'rb') as w:
            rate,channels=w.getframerate(),w.getnchannels()
            data=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float32)/32768
        if channels>1:data=data.reshape(-1,channels).mean(axis=1)
        return resample_poly(data,16000,rate).astype(np.float32)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--limit',type=int,default=0);parser.add_argument('--available-only',action='store_true');parser.add_argument('--recheck',action='store_true');args=parser.parse_args()
    foundation=json.loads((ROOT/'content/foundation.json').read_text())
    selected=json.loads((CACHE/'selected-dialogues.json').read_text())
    expected=list(dict.fromkeys([s['ko'] for l in foundation for s in l['lines']]+[s for d in selected for s in d['lines']]))
    log=CACHE/'audio-transcription.jsonl'
    prior={r['text']:r for r in map(json.loads,log.read_text().splitlines())} if log.exists() else {}
    complete=set(prior)
    if args.recheck:
        expected=[s for s in expected if prior.get(s,{}).get('requiresReview')]
        complete=set()
    if args.limit:expected=[s for s in expected if s not in complete][:args.limit]
    pending=[s for s in expected if s not in complete]
    started=time.monotonic();count=0
    with log.open('a') as out:
        while pending:
            group,arrays,ends=[],[],[];duration=0
            for text in pending:
                path=ROOT/'content/audio'/(hashlib.sha256(text.encode()).hexdigest()[:20]+'.mp3')
                if not path.exists():continue
                samples=decode(path);seconds=len(samples)/16000
                if duration+seconds>.1+25 and group:break
                group.append(text);arrays.append(samples);ends.append((duration,duration+seconds));duration+=seconds+.45
                arrays.append(np.zeros(7200,dtype=np.float32))
                if args.recheck:break
                if duration>=24:break
            if not group:
                if args.available_only:break
                time.sleep(10);continue
            result=transcribe(np.concatenate(arrays),path_or_hf_repo=str(MODEL),language='ko',temperature=0,
                                        condition_on_previous_text=False,word_timestamps=True,verbose=None)
            words=[w for s in result['segments'] for w in s.get('words',[])]
            for text,(start,end) in zip(group,ends):
                recognized=''.join(w['word'] for w in words if start-.1<=(w['start']+w['end'])/2<end+.22).strip()
                similarity=similarity_for(text,recognized)
                record={'text':text,'recognized':recognized,'similarity':round(similarity,4),'requiresReview':similarity<.85,
                        'model':'whisper-large-v3-turbo','expectedTextProvidedToRecognizer':False}
                out.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n');complete.add(text);count+=1
            out.flush();pending=[s for s in pending if s not in complete]
            if count%100<len(group):print(f'ASR checked {count}; {len(pending)} remaining; {round(time.monotonic()-started)}s',flush=True)
    print(f'ASR run complete: {count} sentences checked.',flush=True)


if __name__=='__main__':main()
