"""Source-constrained contextual sense selection, with inspectable evidence.

The fixed local model can only select existing NIKL meanings. It cannot invent
grammar, lexical roots, readings or translations. Ambiguous/unmatched selections
are retained for editorial review rather than silently accepted as a new gloss.
"""
import argparse
import collections
import concurrent.futures
import hashlib
import json
import pathlib
import re
import runpy
import time
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
CACHE=ROOT/'.sites-runtime/corpus'
VERSION='nikl-context-senses-3'
RULES=runpy.run_path(str(ROOT/'scripts/compile-curriculum.py'))
JAMO=RULES['JAMO']
TAGS={'VV':{'동사'},'VA':{'형용사'},'VX':{'보조 동사','보조 형용사'},'NNG':{'명사'},'NP':{'대명사'},'NR':{'수사'},'NNB':{'의존 명사'},'MM':{'관형사'},'MAG':{'부사'},'MAJ':{'부사'},'IC':{'감탄사'}}


def load_selections():
    """Published decisions are reproducible; the local cache may add new ones."""
    released=ROOT/'content/context-senses.json'
    records={r['id']:r for r in json.loads(released.read_text())['records']} if released.exists() else {}
    cache=CACHE/'context-sense-selections.jsonl'
    if cache.exists():
        for row in cache.read_text().splitlines():
            record=json.loads(row);records[record['id']]=record
    return records


class Lexicon:
    def __init__(self):
        self.morphology=json.loads((CACHE/'selected-morphology.json').read_text())
        self.byid={};self.byterm=collections.defaultdict(list)
        for e in json.loads((CACHE/'nikl-dictionary.json').read_text()):
            if e['id'] not in self.byid or (not self.byid[e['id']]['pos'] and e['pos']):self.byid[e['id']]=e
        supplements=ROOT/'content/context-lexicon.json'
        if supplements.exists():
            for e in json.loads(supplements.read_text()):
                entry={'id':'course:'+e['term']+':'+str(e.get('variant',1)), 'term':e['term'], 'pos':e['pos'], 'pronunciation':[], 'origin':'course-authored supplement', 'senses':[{'id':'1','zh':e['meaning'],'definition':e['definition']}]}
                self.byid[entry['id']]=entry
        for e in self.byid.values():self.byterm[e['term']].append(e)
        edits=ROOT/'content/context-morphology.json'
        self.edits=json.loads(edits.read_text()) if edits.exists() else {}
        editorial=ROOT/'content/context-editorial.json'
        self.editorial=json.loads(editorial.read_text()) if editorial.exists() else {}

    def parts(self,lesson,line):
        edit=self.editorial.get(line['id'],{})
        analysis=self.morphology[edit.get('sourceKo',line['ko'])]
        line={**line,'ko':edit.get('ko',line['ko'])}
        result=[]
        for span in re.finditer(r'\S+',line['ko']):
            tokens=[]
            for original in analysis['tokens']:
                if not span.start()<=original['start']<span.end():continue
                t=dict(original)
                if line['ko']=='그러게! 산에 단풍이 예쁘게 들었어.' and t['start']==16 and t['tag']=='VV':
                    t.update(form='들',lemma='들다',entryIds=[e['id'] for e in self.byterm['들다'] if e['pos']=='동사'])
                if line['ko']=='응. 걸을 때마다 돌멩이가 툭툭 차여.' and t['start']==18:
                    if t['tag']=='VV':t.update(form='차이',lemma='차이다',entryIds=['78220'])
                    if t['tag']=='EF':t.update(form='어',lemma='어')
                if tokens and t['tag'] in {'XSV','XSA','XSN'}:
                    previous=tokens[-1]
                    candidate=previous['form']+t['form']+('다' if t['tag'] in {'XSV','XSA'} else '')
                    wanted={'XSV':'동사','XSA':'형용사','XSN':'명사'}[t['tag']]
                    matches=[e for e in self.byterm[candidate] if e['pos']==wanted]
                    if matches and previous['tag'] in {'XR','NNG','NNP','MAG'}:
                        tokens.pop();t={**previous,'form':candidate,'lemma':candidate,'tag':{'XSV':'VV','XSA':'VA','XSN':'NNG'}[t['tag']],'entryIds':[e['id'] for e in matches]}
                tokens.append(t)
            # Keep dictionary compounds intact, e.g. 창문, instead of showing
            # an unrelated standalone sense of 창 beside a second noun 문.
            ti=0
            while ti+1<len(tokens):
                a,b=tokens[ti:ti+2]
                combined=a['lemma']+b['lemma']
                matches=[e for e in self.byterm[combined] if e['pos']=='명사']
                if a['tag'] in {'NNG','NNP','XPN'} and b['tag'] in {'NNG','NNP'} and matches:
                    tokens[ti:ti+2]=[{**a,'form':combined,'lemma':combined,'tag':'NNG','entryIds':[e['id'] for e in matches]}]
                else:ti+=1
            ti=0
            while ti+1<len(tokens):
                a,b=tokens[ti:ti+2]
                compound=a['lemma']+b['lemma']
                entries=self.byterm.get(compound,[])
                if a['tag'] in {'NNG','MAG','XR','XPN'} and b['tag'] in {'VV','VA','VX'} and entries:
                    tokens[ti:ti+2]=[{**a,'lemma':compound,'form':compound[:-1],'tag':b['tag'],'entryIds':[e['id'] for e in entries]}]
                else:ti+=1
            # Dictionary-backed repairs for recognisable irregular forms and
            # noun + 하다 derivations. Preserve their actual endings separately.
            for ti in range(len(tokens)-1):
                a,b=tokens[ti:ti+2]
                if b['tag']=='MM' and b['form']=='한' and self.byterm.get(a['lemma']+'하다'):
                    combined=a['lemma']+'하다'
                    tokens[ti:ti+2]=[{**a,'lemma':combined,'form':combined,'tag':'VV','entryIds':[e['id'] for e in self.byterm[combined]]}, {**b,'form':'ㄴ','lemma':'ㄴ','tag':'ETM','entryIds':[]}]
            if span.group().rstrip('.?!')=='아는' and any(t['lemma']=='아' for t in tokens):
                tokens=[{'form':'알','lemma':'알다','tag':'VV','start':span.start(),'length':1,'entryIds':[]}, {'form':'는','lemma':'는','tag':'ETM','start':span.start()+1,'length':1,'entryIds':[]}]
            if '전화' in line['ko'] and span.group().startswith('거셨'):
                tokens=[t for t in tokens if t['tag']!='VCP']
                for t in tokens:
                    if t['lemma']=='거':t.update(form='걸',lemma='걸다',tag='VV',entryIds=[])
            bare=span.group().strip('.,?!\"\'“”‘’')
            lexical_tokens=[t for t in tokens if t['tag'] not in {'SF','SP','SS','SSO','SSC','SE','SO','SW'}]
            exact=[e for e in self.byterm.get(bare,[]) if e['pos']=='명사']
            if exact and len(lexical_tokens)>1 and all(t['tag'] in {'NNG','NNP','NNB','NR','MM','XSN'} for t in lexical_tokens):
                tokens=[{'form':bare,'lemma':bare,'tag':'NNG','start':span.start(),'length':len(bare),'entryIds':[e['id'] for e in exact]}]
            if len(tokens)>1:
                for ti,t in enumerate(tokens):
                    if ti and t['tag'] in {'NNG','MM'} and t['form'] in {'이','가'} and bare.endswith(t['form']):
                        prefix=bare[:-1]
                        if any(e['pos']=='명사' for e in self.byterm.get(prefix,[])):
                            t.update(tag='JKS',entryIds=[])
            if re.match('그만[두둔둘둡뒀둬]',bare):
                tokens=[t for t in tokens if t['lemma']!='그만']
                for t in tokens:
                    if t['lemma']=='두다':t.update(form='그만두',lemma='그만두다',start=span.start(),entryIds=[])
            if bare=='어떻게':
                tokens=[{'form':'어떻','lemma':'어떻다','tag':'VA','start':span.start(),'length':2,'entryIds':[]},{'form':'게','lemma':'게','tag':'EC','start':span.start()+2,'length':1,'entryIds':[]}]
            if re.search('잖아(요)?$',bare) and any(t['lemma']=='않다' for t in tokens):
                # Reminding -잖아 is not a literal negative -지 않아.
                stop=next((i for i,t in enumerate(tokens) if t['tag']=='EC' and t['form']=='지'),None)
                if stop is not None:
                    ending='잖아요' if bare.endswith('요') else '잖아'
                    tokens=tokens[:stop]+[{'form':ending,'lemma':ending,'tag':'EF','start':span.end()-len(ending),'length':len(ending),'entryIds':[]}]
            if bare in {'한번','한번만','한번은','한번도'}:
                tokens=[{'form':'한번','lemma':'한번','tag':'MAG','start':span.start(),'length':2,'entryIds':[]}]+[t for t in tokens if t['start']>=span.start()+2]
            if any(t['lemma']=='데' and t['tag']=='NNB' for t in tokens) and any(t['tag'] in {'VV','VA','VX'} for t in tokens):
                match=re.search(r'(는데요|는데)$',bare)
                if match:
                    start=span.start()+match.start()
                    tokens=[t for t in tokens if t['start']<start]+[{'form':match.group(),'lemma':match.group(),'tag':'EF' if span.group().endswith(('.', '?', '!')) or bare.endswith('요') else 'EC','start':start,'length':len(match.group()),'entryIds':[]}]
            for t in tokens:
                if t['lemma'] in {'지수','유민','승규','민준','영수','영희','민지'} and any(n in line['zh'] for n in {'智秀','裕敏','承奎','敏俊','英洙','英姬','敏智'}):
                    t.update(tag='NNP',entryIds=[])
                if t['lemma']=='드시다':
                    # 들다 is the honorific 'eat' verb; -시- is kept visible.
                    t.update(lemma='들다',form='들',tag='VV',entryIds=['57293'])
                    tokens.insert(tokens.index(t)+1,{'lemma':'시','form':'시','tag':'EP','start':t['start'],'length':0,'entryIds':[]})
            override=self.edits.get(line['id'],{}).get(str(len(result)))
            if override:
                tokens=[{'lemma':lemma,'form':form,'tag':tag,'start':span.start(),'length':len(form),'entryIds':[]} for lemma,form,tag in override]
            result.append({'text':span.group(),'tokens':tokens,'items':[]})
        for part in result:
            for t in part['tokens']:
                if t['tag'] not in TAGS:continue
                # POS is a morphology hint, not a semantic gate: 부르다 can be
                # 'call' (verb) or 'full' (adjective). The sentence decides.
                entries=[e for e in self.byterm[t['lemma']] if e['pos'] in set().union(*TAGS.values()) or e['pos']=='품사 없음' and re.fullmatch('[가-힣]+',e['term'])]
                if t['tag']=='NR' and len(t['lemma'])>1 and set(t['lemma'])<=set('영공일이삼사오육칠팔구십백천만억조'):
                    # A quantified 이만 is 20,000, not the unrelated adverb
                    # 'stop here'. Unlisted composed numbers are computed.
                    entries=[e for e in entries if e['pos']=='수사' or e['pos']=='관형사' and any('数' in s['definition'] for s in e['senses'])]
                candidates=[]
                for e in entries:
                    for s in e['senses']:
                        candidates.append({'entryId':e['id'],'senseId':s['id'],'lemma':e['term'],'meaning':RULES['clean_gloss'](s),'definition':s['definition'],'pos':e['pos']})
                if candidates:
                    part['items'].append({'lemma':t['lemma'],'tag':t['tag'],'candidates':candidates})
        return result

    def prepare(self,lesson):
        parts=[self.parts(lesson,line) for line in lesson['lines']]
        choices={}
        for i,row in enumerate(parts):
            for j,part in enumerate(row):
                for k,item in enumerate(part['items']):
                    if len(item['candidates'])>1:
                        choices[f'{i}_{j}_{k}']={'词形':part['text'],'原形':item['lemma'],'义项':{str(ci):c['meaning']+'：'+c['definition'] for ci,c in enumerate(item['candidates'])}}
        context=[[self.editorial.get(s['id'],{}).get('ko',s['ko']),self.editorial.get(s['id'],{}).get('zh',s['zh'])] for s in lesson['lines']]
        signature=hashlib.sha256((VERSION+json.dumps([context,choices],ensure_ascii=False)).encode()).hexdigest()
        return {'id':lesson['id'],'signature':signature,'context':context,'choices':choices,'parts':parts}


def select(prepared,retry=False):
    choices=prepared['choices']
    if not choices:return {'id':prepared['id'],'signature':prepared['signature'],'choices':{},'model':'unambiguous source entries'}
    prompt='根据完整韩语对话和中文翻译，为每题的词选择最适合本句的词典义项。题号和义项均从0开始编号；没有合适的义项选-1。只返回以题号字符串为 key、义项编号为整数值的对象，例如 {"0":1,"1":0}。不改写义项。注意同形异义词、辅助动词和固定搭配。\n'
    keys=list(choices)
    data={'对话':prepared['context'],'题目':[{'题号':i,**choices[k]} for i,k in enumerate(keys)]}
    body={'model':'qwen3.6:35b','messages':[{'role':'user','content':prompt+json.dumps(data,ensure_ascii=False,separators=(',',':'))}], 'think':False,'stream':False,'format':{'type':'object','properties':{str(i):{'type':'integer','minimum':-1,'maximum':len(choices[k]['义项'])-1} for i,k in enumerate(keys)},'required':[str(i) for i in range(len(keys))],'additionalProperties':False},'options':{'temperature':.15 if retry else 0,'num_ctx':8192,'num_predict':max(96,len(keys)*12)},'keep_alive':'15m'}
    req=urllib.request.Request('http://127.0.0.1:11434/api/chat',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=240) as response:result=json.load(response)
    selected=json.loads(result['message']['content'])
    assert isinstance(selected,dict) and set(selected)=={str(i) for i in range(len(keys))},'choice count'
    values={k:selected[str(i)] for i,k in enumerate(keys)}
    assert set(values)==set(choices),'choice keys'
    assert all(type(v)==int and -1<=v<len(choices[k]['义项']) for k,v in values.items()),'choice range: '+str([(k,v,len(choices[k]['义项'])) for k,v in values.items() if type(v)!=int or not -1<=v<len(choices[k]['义项'])])
    return {'id':prepared['id'],'signature':prepared['signature'],'choices':values,'model':'qwen3.6:35b','review':'source-constrained automatic selection; editorial review recorded separately','outputTokens':result.get('eval_count',0),'timing':{k:result.get(k) for k in ['total_duration','load_duration','prompt_eval_duration','eval_duration']}}


def main():
    p=argparse.ArgumentParser();p.add_argument('--limit',type=int,default=0);p.add_argument('--workers',type=int,default=4);p.add_argument('--sample',action='store_true');p.add_argument('--retry',action='store_true');args=p.parse_args()
    course=[l for l in json.loads((CACHE/'compiled-course.json').read_text()) if not l['id'].startswith('c')]
    lexicon=Lexicon();outpath=CACHE/'context-sense-selections.jsonl';errpath=CACHE/'context-sense-failures.jsonl'
    previous=load_selections()
    if args.limit and args.sample:
        ids={'n63510-5-8','n93441-1-5','n30837-1-8','n57383-1-8'}
        risk=[l for l in course if l['id'] in ids];rest=[l for l in course if l['id'] not in ids];count=args.limit-len(risk)
        course=risk+[rest[i*(len(rest)-1)//max(count-1,1)] for i in range(count)]
    prepared=[lexicon.prepare(l) for l in course]
    todo=[r for r in prepared if previous.get(r['id'],{}).get('signature')!=r['signature']]
    if args.limit:todo=todo[:args.limit]
    started=time.monotonic();valid=failed=0
    print('Contextual dictionary selections pending:',len(todo),flush=True)
    with outpath.open('a') as out,errpath.open('a') as err,concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending={pool.submit(select,r,args.retry):r['id'] for r in todo}
        for future in concurrent.futures.as_completed(pending):
            try:
                record=future.result();out.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n');out.flush();valid+=1
            except Exception as error:
                err.write(json.dumps({'id':pending[future],'error':str(error)},ensure_ascii=False)+'\n');err.flush();failed+=1
            if (valid+failed)%40==0 or valid+failed==len(todo):print(f'Sense choices {valid+failed}/{len(todo)}: {valid} valid, {failed} need repair; {time.monotonic()-started:.0f}s',flush=True)


if __name__=='__main__':main()
