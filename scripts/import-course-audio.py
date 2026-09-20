"""Import reviewed MP3 bytes into Site R2 through the temporary migration route.

The authorization key is read from stdin, never saved. Every acknowledged file
has been read back from R2 and SHA-256 checked by the server. A local receipt
makes interrupted imports resumable. This script does not publish Site versions.
"""
import argparse
import base64
import concurrent.futures
import hashlib
import json
import pathlib
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--base', required=True)
parser.add_argument('--receipt', required=True)
parser.add_argument('--limit', type=int)
args = parser.parse_args()
url = urllib.parse.urlsplit(args.base)
assert url.scheme == 'https' or (url.scheme == 'http' and url.hostname == '127.0.0.1')
assert not url.username and not url.password and not url.query and not url.fragment
secret = sys.stdin.readline().strip()
assert secret, 'Authorization key required on stdin'
inventory = json.loads((ROOT / 'content/audio-storage-index.json').read_text())
receipt = pathlib.Path(args.receipt)
receipt.parent.mkdir(parents=True, exist_ok=True)
completed = {}
if receipt.exists():
    for line in receipt.read_text().splitlines():
        item = json.loads(line)
        if inventory.get(item['file'], {}).get('sha256') == item['sha256']:
            completed[item['file']] = item
pending = [name for name in sorted(inventory) if name not in completed]
if args.limit:
    pending = pending[:args.limit]
batches, batch, size = [], [], 0
for name in pending:
    estimate = inventory[name]['bytes'] * 4 // 3 + 100
    if batch and (len(batch) >= 60 or size + estimate > 3200000):
        batches.append(batch)
        batch, size = [], 0
    batch.append(name)
    size += estimate
if batch:
    batches.append(batch)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise RuntimeError('Unexpected migration redirect; stopped without forwarding authorization')

lock = threading.Lock()
done = len(completed)

def upload(names):
    global done
    files = []
    for name in names:
        data = (ROOT / 'content/audio' / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == inventory[name]['sha256']
        files.append({'file': name, 'data': base64.b64encode(data).decode()})
    body = json.dumps({'files': files}, separators=(',', ':')).encode()
    for attempt in range(4):
        request = urllib.request.Request(args.base.rstrip('/') + '/api/course-audio-import',
            data=body, method='POST', headers={
                'Content-Type': 'application/json', 'Authorization': 'Bearer ' + secret,
            })
        try:
            with urllib.request.build_opener(NoRedirect).open(request, timeout=90) as response:
                assert response.status == 200
                result = json.load(response)
            assert sorted(result['verified']) == sorted(names)
            assert result['bytes'] == sum(inventory[name]['bytes'] for name in names)
            break
        except urllib.error.HTTPError as error:
            if error.code < 500 and error.code != 429:
                raise RuntimeError(f'Migration rejected with HTTP {error.code}: {error.read(200).decode(errors="replace")}') from None
            if attempt == 3:
                raise RuntimeError(f'Migration failed with HTTP {error.code}') from None
            time.sleep(2 ** attempt)
        except (TimeoutError, urllib.error.URLError):
            if attempt == 3:
                raise RuntimeError('Migration transport timed out after retries') from None
            time.sleep(2 ** attempt)
    with lock:
        with receipt.open('a') as stream:
            for name in names:
                stream.write(json.dumps({'file':name, **inventory[name], 'serverReadBackVerified':True}) + '\n')
        done += len(names)
        print(json.dumps({'verifiedFiles':done,'totalFiles':len(inventory)}), flush=True)

print(json.dumps({'alreadyVerified':len(completed),'pendingFiles':len(pending),'batches':len(batches)}),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(upload,batches))
print(json.dumps({'finished':True,'verifiedFiles':done,'totalFiles':len(inventory)}),flush=True)
