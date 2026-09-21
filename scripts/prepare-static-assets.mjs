// Stage public files before the framework records its static routes. Keep source
// audio; omit only byte-identical objects already read back and verified in R2.
import {createHash} from 'node:crypto';
import {cp, mkdir, readFile, readdir, rm, stat, unlink} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

export async function prepareStaticAssets(root) {
  const staging = resolve(root, '.sites-runtime/build-public');
  await mkdir(resolve(root, '.sites-runtime'), {recursive: true});
  await rm(staging, {recursive: true, force: true});
  await cp(resolve(root, 'public'), staging, {recursive: true});
  const directory = resolve(staging, 'audio');
  let files;
  try {
    files = (await readdir(directory, {withFileTypes: true})).filter(file => file.isFile());
  } catch (error) {
    if (error.code === 'ENOENT') return {removed: 0, bytesRemoved: 0, kept: 0};
    throw error;
  }
  const result = {removed: 0, bytesRemoved: 0, kept: files.length};
  let proof;
  try {
    proof = JSON.parse(await readFile(resolve(root, 'content/audio-cloud-verified.json'), 'utf8'));
  } catch (error) {
    if (error.code === 'ENOENT') return {...result, reason: 'Cloud verification inventory absent; keeping static audio.'};
    throw error;
  }
  const hosting = JSON.parse(await readFile(resolve(root, '.openai/hosting.json'), 'utf8'));
  if (proof.schemaVersion !== 1 || proof.projectId !== hosting.project_id ||
      proof.binding !== hosting.r2 || proof.prefix !== 'course-audio/ko-KR-SunHiNeural/' ||
      proof.allObjectsReadBackSha256Verified !== true) {
    return {...result, reason: 'Cloud evidence does not match this Site; keeping static audio.'};
  }
  if (!proof.entries || typeof proof.entries !== 'object' || Array.isArray(proof.entries)) {
    throw new Error('Invalid cloud audio verification inventory.');
  }
  for (const [file, expected] of Object.entries(proof.entries)) {
    if (!/^[a-f0-9]{20}\.mp3$/.test(file) ||
        !Number.isSafeInteger(expected?.bytes) || expected.bytes <= 0 ||
        !/^[a-f0-9]{64}$/.test(expected?.sha256 ?? '')) {
      throw new Error('Invalid verified audio entry: ' + file);
    }
  }
  for (const file of files) {
    const expected = proof.entries[file.name];
    if (!expected) continue;
    const path = resolve(directory, file.name);
    if ((await stat(path)).size !== expected.bytes) continue;
    const bytes = await readFile(path);
    if (createHash('sha256').update(bytes).digest('hex') !== expected.sha256) continue;
    await unlink(path);
    result.removed++;
    result.kept--;
    result.bytesRemoved += bytes.length;
  }
  return result;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  console.log('Static audio staging:', await prepareStaticAssets(process.cwd()));
}
