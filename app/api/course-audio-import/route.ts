// Offline provisioning only. Disabled unless a short-lived import secret is set.
import {env} from 'cloudflare:workers';
import {timingSafeEqual} from 'node:crypto';
import inventory from '../../../content/audio-storage-index.json';

export const dynamic = 'force-dynamic';
const expectedFiles:Record<string,{bytes:number;sha256:string}> = inventory;
const json = (value:unknown,status=200) => Response.json(value,{status,headers:{'Cache-Control':'no-store'}});
const hex = (bytes:ArrayBuffer) => Array.from(new Uint8Array(bytes),b=>b.toString(16).padStart(2,'0')).join('');

export async function POST(request:Request) {
  const settings = env as unknown as Record<string,unknown>;
  const secret = settings.COURSE_AUDIO_IMPORT_KEY;
  const expiry = Number(settings.COURSE_AUDIO_IMPORT_EXPIRES);
  if (typeof secret !== 'string' || !Number.isFinite(expiry) || Date.now() > expiry) return json({error:'Not available'},404);
  const provided = request.headers.get('authorization')?.replace(/^Bearer /,'') ?? '';
  const encode = new TextEncoder();
  if (provided.length !== secret.length || !timingSafeEqual(encode.encode(provided),encode.encode(secret))) return json({error:'Unauthorized'},401);
  if (request.headers.get('origin') && request.headers.get('origin') !== new URL(request.url).origin) return json({error:'Origin mismatch'},403);
  if (!request.headers.get('content-type')?.startsWith('application/json')) return json({error:'JSON required'},415);
  try {
    const reader = request.body?.getReader();
    if (!reader) return json({error:'Body required'},400);
    const chunks:Uint8Array[] = []; let length = 0;
    while (true) {
      const part = await reader.read(); if (part.done) break;
      length += part.value.length;
      if (length > 3500000) {await reader.cancel();return json({error:'Batch too large'},413);}
      chunks.push(part.value);
    }
    const joined = new Uint8Array(length); let offset = 0;
    for (const chunk of chunks) {joined.set(chunk,offset);offset += chunk.length;}
    const payload = JSON.parse(new TextDecoder().decode(joined));
    if (!Array.isArray(payload.files) || payload.files.length < 1 || payload.files.length > 64) return json({error:'Invalid batch'},400);
    const files:{file:string;bytes:Uint8Array;sha256:string}[] = [];
    for (const item of payload.files) {
      const expected = expectedFiles[item.file];
      if (!expected || typeof item.data !== 'string' || item.data.length > 1000000) return json({error:'Unknown audio'},400);
      const bytes = Uint8Array.from(atob(item.data),c=>c.charCodeAt(0));
      if (bytes.length !== expected.bytes || hex(await crypto.subtle.digest('SHA-256',bytes)) !== expected.sha256) return json({error:'Audio checksum mismatch'},422);
      files.push({file:item.file,bytes,sha256:expected.sha256});
    }
    const bucket = env.BUCKET;
    if (!bucket) throw new Error('Audio bucket unavailable');
    let cursor = 0;
    const verified:string[] = [];
    await Promise.all(Array.from({length:Math.min(4,files.length)},async()=>{
      while (cursor < files.length) {
        const item = files[cursor++];
        const key = `course-audio/ko-KR-SunHiNeural/${item.file}`;
        const previous = await bucket.head(key);
        if (previous && (previous.customMetadata?.sha256 !== item.sha256 || previous.size !== item.bytes.length)) throw new Error('Existing audio differs from reviewed source');
        if (!previous) await bucket.put(key,item.bytes,{
          sha256:item.sha256,
          httpMetadata:{contentType:'audio/mpeg',cacheControl:'public, max-age=31536000, immutable'},
          customMetadata:{sha256:item.sha256,voice:'ko-KR-SunHiNeural'},
        });
        const stored = await bucket.get(key);
        if (!stored || hex(await crypto.subtle.digest('SHA-256',await stored.arrayBuffer())) !== item.sha256) throw new Error('Stored audio verification failed');
        verified.push(item.file);
      }
    }));
    return json({verified:verified.sort(),bytes:files.reduce((sum,file)=>sum+file.bytes.length,0)});
  } catch (error) {
    console.error('course_audio_import_failed',error);
    return json({error:'Audio import failed'},503);
  }
}
