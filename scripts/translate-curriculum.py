"""Local, resumable contextual translation. Outputs require review before release.

Runs a fixed translation model, without tools or autonomous agent actions.
The model is deliberately not called from the deployed learning application.
"""
import argparse
import json
import pathlib
import re
import time
from mlx_lm import load
from mlx_lm.generate import batch_generate
from mlx_lm.sample_utils import make_sampler
from opencc import OpenCC

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / '.sites-runtime/corpus'
MODEL = ROOT / '.sites-runtime/models/hy-mt2-7b'
cc = OpenCC('t2s')


def prompt_for(d, mode):
    if mode == 'plain':
        data = d['lines']
        return ('将下面 JSON 数组中的韩语对话翻译为准确、自然的简体中文。保持数组顺序和项目数量不变，只输出 JSON 数组。'
                '这是日常对话，保留否定、时态、数量、条件、推测和说话人的态度，不额外补充信息。'
                '人名 지수=智秀，민준=敏俊，승규=承奎，유민=裕敏，영수=英洙，영희=英姬。问候语按交际用途自然翻译。\n'
                + json.dumps(data, ensure_ascii=False))
    data = [{'zh': s, 'glosses': s.split()} for s in d['lines']]
    return ('将下面 JSON 中的韩语对话翻译为简体中文。只输出有效 JSON，保持键名、数组顺序和每个数组的项目数量不变。'
            'zh 是整句自然中文翻译；glosses 的每一项是原韩语词组在该句中的中文含义，必须参考完整对话，'
            '而非无上下文的词典义。助词、语尾的功能可简短写在括号内。'
            '忠实保留否定、时间、数量、条件、推测和礼貌程度，不编造人物关系或省略重要信息。\n'
            f"词典语境：{d['term']}：{d['zh']}。{d['definition']}\n"
            + json.dumps(data, ensure_ascii=False, separators=(',', ':')))


def parse_result(raw, d, mode):
    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw)
    start, end = raw.find('['), raw.rfind(']')
    data = json.loads(raw[start:end+1])
    assert isinstance(data, list) and len(data) == len(d['lines']), 'line count'
    if mode == 'plain':
        assert all(isinstance(s, str) and re.search('[\u4e00-\u9fff]', s) for s in data), 'Chinese translation'
        return [cc.convert(s.strip()) for s in data]
    for s, source in zip(data, d['lines']):
        assert isinstance(s, dict) and isinstance(s.get('zh'), str), 'sentence translation'
        assert re.search('[\u4e00-\u9fff]', s['zh']), 'Chinese sentence'
        assert isinstance(s.get('glosses'), list) and len(s['glosses']) == len(source.split()), 'gloss count'
        assert all(isinstance(g, str) and g.strip() for g in s['glosses']), 'empty gloss'
        assert len(s['zh']) < 300 and all(len(g) < 180 for g in s['glosses']), 'excess output'
        s['zh'] = cc.convert(s['zh'].strip())
        s['glosses'] = [cc.convert(g.strip()) for g in s['glosses']]
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--mode', choices=['annotated', 'plain'], default='annotated')
    parser.add_argument('--retry', action='store_true')
    parser.add_argument('--sample', action='store_true')
    args = parser.parse_args()
    output = CACHE / f'translations-{args.mode}.jsonl'
    failures = CACHE / f'translation-failures-{args.mode}.jsonl'
    previous = {r['id'] for r in map(json.loads, output.read_text().splitlines())} if output.exists() else set()
    selected = json.loads((CACHE / 'selected-dialogues.json').read_text())
    todo = [d for d in selected if d['id'] not in previous]
    if args.sample and args.limit:
        todo = [todo[i*(len(todo)-1)//(args.limit-1)] for i in range(args.limit)]
    if args.limit:
        todo = todo[:args.limit]
    if not todo:
        print('All translations already cached.', flush=True)
        return
    print(f'Loading translation model. Remaining: {len(todo)} dialogues; cached: {len(previous)}', flush=True)
    model, tokenizer = load(str(MODEL))
    sampler = make_sampler(temp=0 if not args.retry else .3, top_p=.6, top_k=20)
    started, completed, failed = time.monotonic(), 0, 0
    with output.open('a') as out, failures.open('a') as err:
        for offset in range(0, len(todo), args.batch_size):
            batch = todo[offset:offset+args.batch_size]
            prompts = [tokenizer.apply_chat_template([{'role':'user','content':prompt_for(d,args.mode)}],
                                                    tokenize=True, add_generation_prompt=True) for d in batch]
            result = batch_generate(model, tokenizer, prompts, max_tokens=720 if args.mode == 'annotated' else 240,
                                    sampler=sampler, completion_batch_size=args.batch_size,
                                    prefill_batch_size=min(8,args.batch_size), prefill_step_size=512)
            for d, raw in zip(batch, result.texts):
                try:
                    value = parse_result(raw, d, args.mode)
                    record = {'id':d['id'], 'ko':d['lines'], 'translations':value,
                              'model':'mlx-community/Hy-MT2-7B-4bit',
                              'revision':'9b7204bdb161490a8ce49ce607c1310cc3fd03ad', 'review':'pending'}
                    out.write(json.dumps(record, ensure_ascii=False, separators=(',', ':'))+'\n')
                    completed += 1
                except Exception as e:
                    err.write(json.dumps({'id':d['id'],'error':str(e),'raw':raw},ensure_ascii=False)+'\n')
                    failed += 1
            out.flush(); err.flush()
            print(f'{args.mode}: {offset+len(batch)}/{len(todo)} processed, {completed} valid, {failed} need repair, '
                  f'{round(time.monotonic()-started)}s, {result.stats.generation_tps:.0f} output tokens/s', flush=True)
    print(f'Done: {completed} translated, {failed} need repair.', flush=True)


if __name__ == '__main__':
    main()
