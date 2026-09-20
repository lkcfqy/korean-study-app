"""Verify every published audio asset through the explicitly local production Worker."""
import concurrent.futures
import datetime
import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8787'
entries = json.loads((ROOT / 'content/audio-manifest.json').read_text())['entries']


def check(entry):
    expected = (ROOT / 'public' / entry['path'].lstrip('/')).read_bytes()
    with urllib.request.urlopen(BASE + entry['path'], timeout=30) as response:
        assert response.status == 200, entry['path']
        assert response.headers.get_content_type() == 'audio/mpeg', entry['path']
        actual = response.read()
    assert actual == expected and len(actual) == entry['bytes'], entry['path']
    return len(actual)


with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    total = sum(pool.map(check, entries.values()))

report = {
    'checkedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'files': len(entries),
    'allHttpResponses': '200 audio/mpeg',
    'byteExact': True,
    'totalBytes': total,
    'scope': 'local built production Worker, not live deployment',
}
(ROOT / 'docs/audio-delivery-tests.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
