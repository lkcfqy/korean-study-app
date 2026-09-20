"""Pace the real inventory by source level, sentence complexity and new-word load.

Lesson/line identities stay stable. This is a study sequence, not a TOPIK score
prediction. Source headword level is one constraint, not a whole-sentence label.
"""
import collections
import json
import math
import pathlib
import statistics

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / '.sites-runtime/corpus'
LEVELS = ['초급','중급','고급']


def words(lesson):
    return {w['term'] for s in lesson['lines'] for w in s['words']}


def schedule(course):
    foundations = sorted((l for l in course if l['id'].startswith('c')), key=lambda l:l['id'])
    sources = [l for l in course if not l['id'].startswith('c')]
    frequency = collections.Counter(w for l in sources for w in words(l))
    complex_forms = ('더라도','기는커녕','느니','으므로','기 마련','는 반면','다고','냐고','면서도','었더라면','는 한','뿐만 아니라')
    def complexity(l):
        text = ' '.join(s['ko'] for s in l['lines'])
        length = sum(len(s['ko'].split()) for s in l['lines']) / len(l['lines'])
        return round(l.get('difficulty', length*.4) + sum(text.count(f) for f in complex_forms)*.65 - math.log1p(frequency.get(l['title'].split(' · ')[0],1))*.25, 4)
    ordered = []
    seen = set()
    for phase, level in enumerate(LEVELS):
        pool = sorted((l for l in sources if l['sourceLevel']==level), key=lambda l:(complexity(l),l['id']))
        n = len(pool)
        days = [d for d in range(phase*60+1, phase*60+61) if d%5]
        bases = {}
        for i, day in enumerate(days):
            if i%4 == 0:
                bases[i] = foundations[((day-1)//30)*6+(i%24)//4]
        first_at = {}
        for k,l in enumerate(pool):
            for w in words(l)-seen:
                first_at.setdefault(w,k)
        # Dynamic programming partitions the ordered inventory; it cannot hide
        # difficult overflow on the last day or pad days with duplicate lessons.
        current = {0:0.0}
        parents = []
        prior_foundation = set(seen)
        phase_words = set(first_at) | set().union(*(words(l) for l in bases.values()))
        total_novel = len(phase_words-seen)
        target_normal = (total_novel-(6*24 if phase==0 else 0))/(42 if phase==0 else 48)
        for di, day in enumerate(days):
            base = bases.get(di)
            base_words = words(base) if base else set()
            base_novel = base_words-prior_foundation
            introduced = [0]*n
            for w,k in first_at.items():
                if w not in prior_foundation:
                    introduced[k] += 1
            prefix = [0]
            for count in introduced:
                prefix.append(prefix[-1]+count)
            base_after = [sum(first_at.get(w,n)>=k for w in base_novel) for k in range(n+1)]
            next_states, back = {}, {}
            remaining = 47-di
            cap = 28 if phase==0 and day<=7 else 60
            target_words = 24 if phase==0 and day<=7 else target_normal
            target_rows = (n*2+sum(len(l['lines']) for l in bases.values()))/48
            max_take = (96-(len(base['lines']) if base else 0))//2
            for start, previous_cost in current.items():
                first_end = max(start+1,n-remaining*48)
                last_end = min(n-remaining,start+max_take)
                if remaining==0:
                    first_end=last_end=n
                for end in range(first_end,last_end+1):
                    if end-start>max_take:
                        continue
                    novel = prefix[end]-prefix[start]+base_after[end]
                    if novel>cap:
                        continue
                    rows = (end-start)*2+(len(base['lines']) if base else 0)
                    cost = previous_cost+(novel-target_words)**2*2+(rows-target_rows)**2*.3
                    if cost<next_states.get(end,float('inf')):
                        next_states[end]=cost
                        back[end]=start
            assert next_states, f'Cannot satisfy workload bounds on day {day}'
            parents.append(back)
            current=next_states
            prior_foundation.update(base_words)
        assert n in current, f'Unallocated {level} dialogues'
        cuts=[n]
        for back in reversed(parents):
            cuts.append(back[cuts[-1]])
        cuts.reverse()
        for di,day in enumerate(days):
            daily=([bases[di]] if di in bases else [])+pool[cuts[di]:cuts[di+1]]
            for lesson in daily:
                lesson['day']=day
                lesson['stage']=(day-1)//30
                lesson['sequenceScore']=complexity(lesson)
                ordered.append(lesson)
                seen.update(words(lesson))
    assert len(ordered)==len(course) and ordered[0]['id']=='c01'
    return ordered


def main():
    course=json.loads((CACHE/'compiled-course.json').read_text())
    ordered=schedule(course)
    (CACHE/'compiled-course.json').write_text(json.dumps(ordered,ensure_ascii=False,separators=(',',':'))+'\n')
    seen=set();days=[]
    for day in range(1,181):
        daily=[l for l in ordered if l['day']==day]
        all_words=set().union(*(words(l) for l in daily))
        days.append({'day':day,'lessons':len(daily),'rows':sum(len(l['lines']) for l in daily),'newWords':len(all_words-seen)})
        seen.update(all_words)
    months=[]
    for month in range(6):
        ls=[l for l in ordered if l['stage']==month]
        months.append({'month':month+1,'lessons':len(ls),'sourceHeadwordLevels':dict(collections.Counter(l.get('sourceLevel','foundation') for l in ls)),
                       'medianWordsPerTurn':statistics.median(len(s['ko'].split()) for l in ls for s in l['lines'])})
    report={'method':'source-level gates plus sentence complexity; exact workload-constrained partition', 'sourceLevelIsNotWholeSentenceLevel':True,
            'preservesLessonAndLineIds':True,'firstWeekNewWordCap':28,'newWordCap':60,'dialogueRowCap':96,'months':months,'days':days}
    (ROOT/'docs/schedule-quality.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'months':months,'newWordRange':[min(d['newWords'] for d in days if d['lessons']),max(d['newWords'] for d in days)],'maxRows':max(d['rows'] for d in days)},ensure_ascii=False))


if __name__=='__main__':main()
