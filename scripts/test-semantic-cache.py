"""Review evidence is reusable only for the input it actually saw."""
import hashlib
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('audit', Path(__file__).with_name('audit-course-semantics.py'))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class ReviewCacheTest(unittest.TestCase):
    def test_current_input_can_be_reused_across_recorded_backends(self):
        row = {'methodVersion': audit.VERSION, 'model': audit.MLX_MODEL_NAME,
               'inputSignature': audit.input_signature('reviewed dialogue')}
        self.assertTrue(audit.is_current(row, 'reviewed dialogue'))
        self.assertFalse(audit.is_current(row, 'edited dialogue'))

    def test_historical_mlx_key_keeps_actual_model_provenance(self):
        encoded = 'unchanged historical input'
        row = {'methodVersion': audit.VERSION, 'model': audit.MLX_MODEL_NAME,
               'signature': hashlib.sha256((audit.VERSION + 'mlx' + 'qwen3.6:35b' + audit.INSTRUCTION + encoded).encode()).hexdigest()}
        self.assertTrue(audit.is_current(row, encoded))
        self.assertEqual(row['model'], audit.MLX_MODEL_NAME)
        self.assertFalse(audit.is_current(row, encoded + ' changed'))

    def test_older_instructions_are_not_current_evidence(self):
        row = {'methodVersion': 'old-method', 'inputSignature': audit.input_signature('same input')}
        self.assertFalse(audit.is_current(row, 'same input'))

    def test_unbound_record_is_never_current(self):
        self.assertFalse(audit.is_current({'methodVersion': audit.VERSION}, 'input'))


if __name__ == '__main__':
    unittest.main()
