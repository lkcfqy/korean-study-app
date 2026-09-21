"""Use reviewed contrasts; preserve existing choices until editorial review.

New questions require an explicit pair. Answer positions stay stable.
"""
import json
import re
from pathlib import Path

def normalize(text):
    return re.sub(r'[^\w]', '', text)

class QuestionChoices:
    def __init__(self,course,overrides):
        self.overrides=overrides
        self.existing={}
        directory=Path(__file__).resolve().parents[1]/'public/course'
        for lesson in course:
            path=directory/(lesson['id']+'.json')
            if not path.exists():continue
            published=json.loads(path.read_text())
            for q in published.get('questions',[]):
                line=published['lines'][q['lineIndex']]
                self.existing[line['id']]=[text for i,text in enumerate(q['options']) if i!=q['answer']]

    def distractors(self,lesson,line):
        options=self.overrides.get(line['id'],self.existing.get(line['id']))
        if not options or len(options)!=2 or len({normalize(t) for t in [line['zh'],*options]})!=3:
            raise ValueError('Review distractors for '+line['id'])
        return options
