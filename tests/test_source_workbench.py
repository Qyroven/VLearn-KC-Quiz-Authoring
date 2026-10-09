import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/vlearn-kc-quiz-authoring/scripts'
sys.path.insert(0, str(SCRIPTS))
import source_workbench as s


class WorkbenchTests(unittest.TestCase):
    def test_page_ranges_are_physical_one_based_and_bounded(self):
        self.assertEqual(s.pages_arg('1,3-4', 4), [1, 3, 4])
        for bad in ('0', '3-2', '5', '1,', '-1'):
            with self.assertRaises(ValueError): s.pages_arg(bad, 4)

    def workspace(self, root):
        pdf = root / 'source.pdf'; pdf.write_bytes(b'synthetic only; renderer mocked')
        (root / 'source.json').write_text(json.dumps({'source_id': 's1', 'path': str(pdf), 'sha256': s.sha(pdf), 'page_count': 2}))
        return pdf

    @staticmethod
    def render(pdf, page, output, dpi, crop=None):
        path = output.with_suffix('.png')
        path.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 8 + struct.pack('>II', 100, 80))
        return path

    def test_outside_crop_rejected_and_no_partial_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.workspace(root)
            with patch.object(s, 'render', side_effect=self.render):
                with self.assertRaises(ValueError): s.recover(root, 1, root / 'attempt', crop=[90, 0, 20, 20])
            self.assertFalse((root / 'attempt').exists())

    def test_changed_source_requires_new_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); pdf = self.workspace(root); pdf.write_bytes(b'changed')
            with self.assertRaises(ValueError): s.recover(root, 1, root / 'attempt')

    def test_missing_ocr_is_reported_not_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); self.workspace(root)
            with patch.object(s, 'render', side_effect=self.render), patch.object(s.shutil, 'which', return_value=None):
                result = s.recover(root, 1, root / 'attempt', crop=[10, 10, 20, 20], ocr_language='vie')
            self.assertEqual(result['ocr']['status'], 'unavailable_tesseract')
            self.assertEqual(result['status'], 'needs_visual_verification')
            self.assertEqual(len(result['artifacts']), 2)
            with self.assertRaises(ValueError): s.recover(root, 1, root / 'attempt')


if __name__ == '__main__':
    unittest.main()
