"""Decode all shipped SunHi assets and inspect their signal, not their semantics."""
import concurrent.futures, json, math, pathlib, subprocess, tempfile, wave
import numpy as np

ROOT=pathlib.Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'content/audio-manifest.json').read_text())

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

with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    results=list(pool.map(inspect,manifest['entries'].items()))
report={'files':len(results),'voice':manifest['voice'],'allDecodeToPCM':True,'noSilentFiles':True,'noSevereClipping':True,'durationSeconds':round(sum(r['duration'] for r in results),2),'rmsDbRange':[round(min(r['rmsDb'] for r in results),2),round(max(r['rmsDb'] for r in results),2)],'maxClippedSampleFraction':max(r['clippedFraction'] for r in results),'scope':'Decode and signal checks only; no semantic speech recognition and no human pronunciation review.'}
(ROOT/'docs/audio-signal-tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
