"""Regression scenarios for source meanings previously overwritten by templates."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('apply_context', ROOT / 'scripts/apply-context.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def meaning(previous, current, entry, sense):
    parts = [
        {'tokens': [{'lemma': lemma, 'form': form, 'tag': tag}
                    for lemma, form, tag in previous]},
        {'tokens': [{'lemma': '보다', 'form': '보', 'tag': 'VX'},
                    {'lemma': current, 'form': current, 'tag': 'EC'}]},
    ]
    return module.context_expression('보다', 'VX', parts, 1,
                                     sense={'entryId': entry, 'senseId': sense})


class ContextExpressionTests(unittest.TestCase):
    def test_never_experienced_is_not_trial(self):
        # 일찍이 느껴 보지 못한 감동: a feeling never experienced before.
        value = meaning([('느끼다', '느끼', 'VV'), ('어', '어', 'EC')],
                        '지', '62171', '2')
        self.assertIn('经历过', value)
        self.assertNotIn('试着', value)

    def test_trying_food_remains_trial(self):
        value = meaning([('먹다', '먹', 'VV'), ('어', '어', 'EC')],
                        '어', '62171', '1')
        self.assertIn('试着做', value)

    def test_incorrect_pos_cannot_turn_watching_into_trying(self):
        # 즐겨 보는 프로그램: a lexical source must survive a bad VX tag.
        self.assertIsNone(meaning([('즐기다', '즐기', 'VV'), ('어', '어', 'EC')],
                                  '는', '61190', '2'))

    def test_other_source_senses_are_not_replaced_with_trial(self):
        # A source choice still needs editorial review; the renderer must not
        # hide its distinct meaning behind a generic trying template.
        self.assertIsNone(meaning([('가다', '가', 'VV'), ('아', '아', 'EC')],
                                  '니', '62171', '3'))


if __name__ == '__main__':
    unittest.main()
