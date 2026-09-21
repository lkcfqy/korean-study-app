"""Verify every published audio asset through the explicitly local production Worker."""
import concurrent.futures
import datetime
import http.client
import json
import pathlib
import threading

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8787'
entries = json.loads((ROOT / 'content/audio-manifest.json').read_text())['entries']
clients=threading.local()
connections=[]


def check(entry):
    expected = (ROOT / 'content/audio' / pathlib.Path(entry['path']).name).read_bytes()
    # Reuse one connection per worker; opening tens of thousands of short-lived
    # sockets can exhaust macOS ephemeral ports without testing the application.
    if not hasattr(clients,'connection'):
        clients.connection=http.client.HTTPConnection('127.0.0.1',8787,timeout=30)
        connections.append(clients.connection)
    clients.connection.request('GET',entry['path'])
    response=clients.connection.getresponse()
    assert response.status == 200, (entry['path'],response.status)
    assert response.getheader('Content-Type','').split(';')[0] == 'audio/mpeg', entry['path']
    actual=response.read()
    assert actual == expected and len(actual) == entry['bytes'], entry['path']
    return len(actual)


total=0
try:
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for count,size in enumerate(pool.map(check,entries.values()),1):
            total+=size
            if count%2000==0:print(f'Checked audio delivery {count}/{len(entries)}',flush=True)
finally:
    for connection in connections:connection.close()

report = {
    'checkedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'files': len(entries),
    'allHttpResponses': '200 audio/mpeg',
    'byteExact': True,
    'totalBytes': total,
    'scope': 'local built production Worker, not live deployment',
    'transport': 'Eight reusable local HTTP connections; byte comparison for every asset.',
}
(ROOT / 'docs/audio-delivery-tests.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
