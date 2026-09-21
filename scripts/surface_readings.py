"""Complete written forms for sentence-token audio, separate from lemmas."""
import hashlib

# Remove surrounding quotation/sentence marks only. Keep every syllable,
# conjugation, particle, number, unit, and internal punctuation as written.
SURROUNDING_PUNCTUATION = '.,?!:;"\'“”‘’…()[]{}〈〉《》「」『』'


def surface_term(text):
    term = text.strip().strip(SURROUNDING_PUNCTUATION).strip()
    if not term:
        raise ValueError(f'Clickable text has no spoken form: {text!r}')
    return term


def surface_reading(text):
    term = surface_term(text)
    return {'term': term, 'audio': '/audio/' + hashlib.sha256(term.encode()).hexdigest()[:20] + '.mp3'}


def attach_surface_readings(course):
    for lesson in course:
        for line in lesson['lines']:
            for part in line['parts']:
                part['surfaceReading'] = surface_reading(part['text'])


def render_context_clip(root, clip, target):
    """Create a new short MP3 from an explicitly reviewed sentence interval.

    Source audio is hash-locked and never changed. The build does not need these
    local generation dependencies; only regenerating a recorded excerpt does.
    """
    import subprocess
    import tempfile
    import wave
    from pathlib import Path
    import lameenc

    source=root/'content/audio'/(hashlib.sha256(clip['sourceText'].encode()).hexdigest()[:20]+'.mp3')
    assert hashlib.sha256(source.read_bytes()).hexdigest()==clip['sourceSha256']
    start,end=clip['startSeconds'],clip['endSeconds']
    assert 0<=start<end
    with tempfile.TemporaryDirectory(prefix='surface-audio-') as folder:
        decoded=Path(folder)/'source.wav'
        subprocess.run(['/usr/bin/afconvert','-f','WAVE','-d','LEI16',str(source),str(decoded)],check=True,capture_output=True)
        with wave.open(str(decoded),'rb') as wav:
            rate,channels=wav.getframerate(),wav.getnchannels()
            assert wav.getsampwidth()==2 and end<=wav.getnframes()/rate
            wav.setpos(round(start*rate))
            pcm=wav.readframes(round((end-start)*rate))
        silence=bytes(round(.1*rate)*channels*2)
        encoder=lameenc.Encoder()
        encoder.set_bit_rate(128)
        encoder.set_in_sample_rate(rate)
        encoder.set_channels(channels)
        encoder.set_quality(2)
        encoder.silence()
        target.write_bytes(encoder.encode(silence+pcm+silence)+encoder.flush())
