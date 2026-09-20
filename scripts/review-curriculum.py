"""A fixed local bilingual text-review pass, with no tools or agent loop."""
import argparse
import json
import pathlib
import re
import time
from mlx_lm import load
from mlx_lm.generate import batch_generate
from mlx_lm.sample_utils import make_sampler
from opencc import OpenCC

ROOT=pathlib.Path(__file__).resolve().parents[1]
CACHE=ROOT/'.sites-runtime/corpus'
cc=OpenCC('t2s')


def make_prompt(d,draft):
    source=[{'ko':ko,'zh':zh} for ko,zh in zip(d['lines'],draft)]
    return ('检查下面两轮韩语对话的中文是否存在实质性误译。只检查意义，不改写已经准确的措辞。'
            '重点检查谁是动作主体、否定、时态、数值、条件、因果、反问与引用。'
            '不根据词汇字面义否定自然的整句翻译。不要把韩语省略主语一律补成“我”或“你”。'
            '若准确，ok=true且translations原样保留；若有明确错译，ok=false，给出简短具体的reason及修正后的两句中文。'
            '只输出JSON对象：{"ok":true或false,"reason":"具体的意义问题或空字符串","translations":["第一句中文","第二句中文"]}。'
            '人名지수=智秀，민준=敏俊，승규=承奎，유민=裕敏。\n'
            +json.dumps(source,ensure_ascii=False,separators=(',',':')))


def parse(raw,d):
    if '</think>' in raw:raw=raw.split('</think>')[-1]
    data=json.loads(raw[raw.find('{'):raw.rfind('}')+1])
    assert len(data['translations'])==len(d['lines'])
    assert isinstance(data.get('ok'),bool) and isinstance(data.get('reason'),str)
    for zh in data['translations']:
        assert isinstance(zh,str) and re.search('[\u4e00-\u9fff]',zh) and len(zh)<350
    data['translations']=[cc.convert(s.strip()) for s in data['translations']]
    return data


def main():
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int,default=0);p.add_argument('--sample',action='store_true');p.add_argument('--batch-size',type=int,default=24);p.add_argument('--retry',action='store_true');args=p.parse_args()
    selected=json.loads((CACHE/'selected-dialogues.json').read_text())
    drafts={r['id']:r for r in map(json.loads,(CACHE/'translations-plain.jsonl').read_text().splitlines())}
    output=CACHE/'translation-comparisons.jsonl';failures=CACHE/'review-failures.jsonl'
    previous={r['id'] for r in map(json.loads,output.read_text().splitlines())} if output.exists() else set()
    todo=[d for d in selected if d['id'] in drafts and d['id'] not in previous]
    if args.limit:
        todo=[todo[i*(len(todo)-1)//(args.limit-1)] for i in range(args.limit)] if args.sample else todo[:args.limit]
    if not todo:print('All review outputs cached.',flush=True);return
    print('Loading fixed bilingual review model; pending',len(todo),flush=True)
    model,tokenizer=load(str(ROOT/'.sites-runtime/models/qwen3.5-9b'))
    started=time.monotonic();valid=failed=0
    with output.open('a') as out,failures.open('a') as err:
        for offset in range(0,len(todo),args.batch_size):
            batch=todo[offset:offset+args.batch_size]
            prompts=[tokenizer.apply_chat_template([{'role':'user','content':make_prompt(d,drafts[d['id']]['translations'])}],tokenize=True,add_generation_prompt=True,enable_thinking=False) for d in batch]
            result=batch_generate(model,tokenizer,prompts,max_tokens=420,sampler=make_sampler(temp=.2 if args.retry else 0),completion_batch_size=args.batch_size,prefill_batch_size=min(4,args.batch_size),prefill_step_size=512)
            for d,raw in zip(batch,result.texts):
                try:
                    data=parse(raw,d);data.update(id=d['id'],ko=d['lines'],model='mlx-community/Qwen3.5-9B-4bit',revision='8b2b98c00a6b4d291155e4890773ca8f769aee53',review='automatic bilingual comparison; not human certification')
                    out.write(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n');valid+=1
                except Exception as e:
                    err.write(json.dumps({'id':d['id'],'error':str(e),'raw':raw},ensure_ascii=False)+'\n');failed+=1
            out.flush();err.flush()
            print(f'Review {offset+len(batch)}/{len(todo)}; {valid} structurally valid, {failed} need repair; {round(time.monotonic()-started)}s; {result.stats.generation_tps:.0f} tokens/s',flush=True)
    print('Review pass complete',valid,'valid,',failed,'need repair',flush=True)


if __name__=='__main__':main()
