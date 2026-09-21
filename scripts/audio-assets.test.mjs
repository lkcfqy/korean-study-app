import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdtemp, mkdir, readFile, rm, writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {prepareStaticAssets} from './prepare-static-assets.mjs';

const known = '0'.repeat(20) + '.mp3';
const changed = '1'.repeat(20) + '.mp3';
const unknown = '2'.repeat(20) + '.mp3';
const metadata = value => ({bytes: Buffer.byteLength(value),
  sha256: createHash('sha256').update(value).digest('hex')});

async function fixture(t) {
  const root = await mkdtemp(join(tmpdir(), 'course-audio-assets-'));
  t.after(() => rm(root, {recursive: true, force: true}));
  for (const folder of ['.openai', 'content', 'public/audio']) {
    await mkdir(join(root, folder), {recursive: true});
  }
  await writeFile(join(root, '.openai/hosting.json'), JSON.stringify({project_id: 'site-one', r2: 'BUCKET'}));
  const proof = {schemaVersion: 1, projectId: 'site-one', binding: 'BUCKET',
    prefix: 'course-audio/ko-KR-SunHiNeural/', allObjectsReadBackSha256Verified: true,
    entries: {[known]: metadata('unchanged'), [changed]: metadata('old')}};
  await writeFile(join(root, 'content/audio-cloud-verified.json'), JSON.stringify(proof));
  await writeFile(join(root, 'public/content-sources.html'), 'source notice');
  for (const [file, data] of [[known, 'unchanged'], [changed, 'new'], [unknown, 'unknown']]) {
    await writeFile(join(root, 'public/audio', file), data);
  }
  return {root, proof};
}

test('only identical cloud-verified generated copies are omitted; source and unknown audio remain', async t => {
  const {root} = await fixture(t);
  assert.deepEqual(await prepareStaticAssets(root), {removed: 1, bytesRemoved: 9, kept: 2});
  await assert.rejects(readFile(join(root, '.sites-runtime/build-public/audio', known)), {code: 'ENOENT'});
  assert.equal(await readFile(join(root, 'public/audio', known), 'utf8'), 'unchanged');
  assert.equal(await readFile(join(root, '.sites-runtime/build-public/audio', changed), 'utf8'), 'new');
  assert.equal(await readFile(join(root, '.sites-runtime/build-public/audio', unknown), 'utf8'), 'unknown');
  assert.equal(await readFile(join(root, '.sites-runtime/build-public/content-sources.html'), 'utf8'), 'source notice');
});

test('evidence for another Site or a missing inventory cannot remove assets', async t => {
  const {root, proof} = await fixture(t);
  proof.projectId = 'another-site';
  const path = join(root, 'content/audio-cloud-verified.json');
  await writeFile(path, JSON.stringify(proof));
  assert.equal((await prepareStaticAssets(root)).removed, 0);
  await rm(path);
  assert.equal((await prepareStaticAssets(root)).removed, 0);
  assert.equal(await readFile(join(root, '.sites-runtime/build-public/audio', known), 'utf8'), 'unchanged');
});

test('malformed verification evidence fails before removing any assets', async t => {
  const {root, proof} = await fixture(t);
  proof.entries[changed].sha256 = 'invalid';
  await writeFile(join(root, 'content/audio-cloud-verified.json'), JSON.stringify(proof));
  await assert.rejects(prepareStaticAssets(root), /Invalid verified audio entry/);
  assert.equal(await readFile(join(root, '.sites-runtime/build-public/audio', known), 'utf8'), 'unchanged');
});
