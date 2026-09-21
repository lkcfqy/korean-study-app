"""An unfinished model job must not change the course's selected meanings."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import contextual_senses as senses


class CandidateIsolationTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.cache = self.root/'cache'
        self.cache.mkdir()
        (self.root/'content').mkdir()
        self.source = self.root/'content/context-senses.json'
        self.candidates = self.cache/'context-sense-selections.jsonl'
        self.record = {'id': 'lesson', 'signature': 'same-input',
                       'choices': {'0_0_0': 1}, 'model': 'historical provenance'}
        self.source.write_text(json.dumps({'records': [self.record]}))
        for name, value in [('ROOT', self.root), ('CACHE', self.cache)]:
            patched = patch.object(senses, name, value)
            patched.start()
            self.addCleanup(patched.stop)

    def test_conflicting_candidate_cannot_replace_versioned_choice(self):
        candidate = {**self.record, 'choices': {'0_0_0': 0}, 'model': 'new model'}
        self.candidates.write_text(json.dumps(candidate)+'\n')
        before = self.source.read_bytes()
        self.assertEqual(senses.load_selections(), {'lesson': self.record})
        self.assertEqual(self.source.read_bytes(), before)
        # The generation job can still resume from its own non-published output.
        self.assertEqual(senses.load_selections(include_candidates=True),
                         {'lesson': candidate})

    def test_candidate_only_lesson_is_not_accepted_for_assembly(self):
        candidate = {**self.record, 'id': 'unreviewed-new-lesson'}
        self.candidates.write_text(json.dumps(candidate)+'\n')
        self.assertNotIn(candidate['id'], senses.load_selections())
        self.source.unlink()
        self.assertEqual(senses.load_selections(), {})

    def test_interrupted_candidate_write_does_not_break_rebuilding(self):
        self.candidates.write_text('{"id":"unfinished')
        self.assertEqual(senses.load_selections(), {'lesson': self.record})

    def test_broken_versioned_source_cannot_fall_back_to_model_cache(self):
        self.candidates.write_text(json.dumps(self.record)+'\n')
        self.source.write_text('{"records":')
        with self.assertRaises(json.JSONDecodeError):
            senses.load_selections()


if __name__ == '__main__':
    unittest.main()
