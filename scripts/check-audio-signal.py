"""Decode all shipped SunHi assets and inspect their signal, not their semantics."""
import argparse, concurrent.futures, hashlib, json, math, pathlib, subprocess, tempfile, wave
import numpy as np

ROOT=pathlib.Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'content/audio-manifest.json').read_text())
parser=argparse.ArgumentParser()
parser.add_argument('--baseline-ref',help='Reuse a passed signal report only for byte-identical assets in this Git revision.')
args=parser.parse_args()
baseline=None;baseline_index={};reused=[]
if args.baseline_ref:
    def at_revision(path):
        return json.loads(subprocess.check_output(['git','show',args.baseline_ref+':'+path],cwd=ROOT))
    baseline=at_revision('docs/audio-signal-tests.json')
    baseline_index=at_revision('content/audio-storage-index.json')
    assert baseline['files']==len(baseline_index) and all(baseline[k] for k in ['allDecodeToPCM','noSilentFiles','noSevereClipping'])
    assert baseline['voice']==manifest['voice']
    current_names={pathlib.Path(e['path']).name for e in manifest['entries'].values()}
    assert set(baseline_index)<=current_names, 'Aggregate reuse requires retaining every baseline asset.'
    for name,meta in baseline_index.items():
        raw=(ROOT/'content/audio'/name).read_bytes()
        assert len(raw)==meta['bytes'] and hashlib.sha256(raw).hexdigest()==meta['sha256'], 'Changed baseline audio must be decoded again with a full run.'
        reused.append(name)

def inspect(entry):
    text, meta=entry
    source=ROOT/'content/audio'/pathlib.Path(meta['path']).name
    with tempfile.TemporaryDirectory(prefix='hangeul-audio-') as directory:
        out=pathlib.Path(directory)/'decoded.wav'
        subprocess.run(['/usr/bin/afconvert','-f','WAVE','-d','LEI16',str(source),str(out)],check=True,capture_output=True)
        with wave.open(str(out),'rb') as wav:
            assert wav.getsampwidth()==2
            frames,rate,channels=wav.getnframes(),wav.getframerate(),wav.getnchannels()
            signal=np.frombuffer(wav.readframes(frames),dtype='<i2').astype(np.float64)
        peak=float(np.abs(signal).max())/32768
        rms=float(np.sqrt(np.mean(signal**2)))/32768
        clipped=float(np.mean(np.abs(signal)>=32760))
        assert frames/rate>.1 and rms>.001 and clipped<.01, (text,frames/rate,rms,clipped)
        return {'duration':frames/rate,'peak':peak,'rmsDb':20*math.log10(rms),'clippedFraction':clipped}

pending=[(text,meta) for text,meta in manifest['entries'].items() if pathlib.Path(meta['path']).name not in baseline_index]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    results=list(pool.map(inspect,pending))
levels=[r['rmsDb'] for r in results]+(baseline['rmsDbRange'] if baseline else [])
clipping=[r['clippedFraction'] for r in results]+([baseline['maxClippedSampleFraction']] if baseline else [])
report={'files':len(results)+len(reused),'voice':manifest['voice'],'allDecodeToPCM':True,'noSilentFiles':True,'noSevereClipping':True,'durationSeconds':round(sum(r['duration'] for r in results)+(baseline['durationSeconds'] if baseline else 0),2),'rmsDbRange':[round(min(levels),2),round(max(levels),2)],'maxClippedSampleFraction':max(clipping),'scope':'Decode and signal checks only; no semantic speech recognition and no human pronunciation review.','newlyDecoded':len(results),'byteIdenticalBaselineAssets':len(reused),'baselineRef':args.baseline_ref}
(ROOT/'docs/audio-signal-tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
