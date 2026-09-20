"""Index original SunHi files for verified R2 provisioning; never transcode them."""
import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / 'content/audio-manifest.json').read_text())
inventory = {}
for entry in manifest['entries'].values():
    source = ROOT / 'content/audio' / pathlib.Path(entry['path']).name
    data = source.read_bytes()
    assert len(data) == entry['bytes']
    inventory[source.name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
(ROOT / 'content/audio-storage-index.json').write_text(json.dumps(dict(sorted(inventory.items())),separators=(',',':'))+'\n')
print(json.dumps({'files':len(inventory),'bytes':sum(entry['bytes'] for entry in inventory.values())}))
