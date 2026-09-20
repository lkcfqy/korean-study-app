import {env} from 'cloudflare:workers';

export const dynamic = 'force-dynamic';
const immutable = 'public, max-age=31536000, immutable';
const keyFor = (file:string) => `course-audio/ko-KR-SunHiNeural/${file}`;
type Context = {params:Promise<{file:string}>};

async function serve(request:Request, context:Context, headOnly:boolean) {
  const {file} = await context.params;
  if (!/^[a-f0-9]{20}\.mp3$/.test(file)) return new Response(null, {status:404});
  try {
    const bucket = env.BUCKET;
    if (!bucket) throw new Error('Course audio storage unavailable');
    const key = keyFor(file);
    const rangeHeader = request.headers.get('range');
    const metadata = headOnly || rangeHeader ? await bucket.head(key) : null;
    if ((headOnly || rangeHeader) && !metadata) return new Response(null, {status:404});
    let range: {offset:number;length:number} | undefined;
    if (rangeHeader && metadata && (!request.headers.has('if-range') || request.headers.get('if-range') === metadata.httpEtag)) {
      const match = /^bytes=(\d*)-(\d*)$/.exec(rangeHeader);
      let offset = 0, end = metadata.size - 1;
      if (match && (match[1] || match[2])) {
        offset = match[1] ? Number(match[1]) : Math.max(0, metadata.size - Number(match[2]));
        end = match[1] && match[2] ? Math.min(Number(match[2]), end) : end;
      } else offset = metadata.size;
      if (!Number.isSafeInteger(offset) || !Number.isSafeInteger(end) || offset > end || offset >= metadata.size) {
        return new Response(null, {status:416, headers:{'Content-Range':`bytes */${metadata.size}`}});
      }
      range = {offset, length:end - offset + 1};
    }
    const object = headOnly ? metadata : await bucket.get(key, range ? {range} : undefined);
    if (!object) return new Response(null, {status:404});
    const body = !headOnly ? (object as R2ObjectBody).body : null;
    const headers = new Headers({
      'Content-Type':'audio/mpeg', 'Cache-Control':immutable,
      'ETag':object.httpEtag, 'Accept-Ranges':'bytes', 'X-Content-Type-Options':'nosniff',
    });
    if (!range && request.headers.get('if-none-match') === object.httpEtag) {
      if (body) await body.cancel();
      return new Response(null, {status:304, headers});
    }
    headers.set('Content-Length', String(range?.length ?? object.size));
    if (range) headers.set('Content-Range', `bytes ${range.offset}-${range.offset + range.length - 1}/${object.size}`);
    return new Response(body, {status:range ? 206 : 200, headers});
  } catch (error) {
    console.error('course_audio_load_failed', error);
    return new Response('音频暂时无法加载，请稍后重试。', {status:503, headers:{'Cache-Control':'no-store'}});
  }
}

export const GET = (request:Request, context:Context) => serve(request, context, false);
export const HEAD = (request:Request, context:Context) => serve(request, context, true);
