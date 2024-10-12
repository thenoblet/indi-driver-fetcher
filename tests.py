# tests.py
import unittest
from unittest.mock import patch
from task_1 import check_modules
import io
import sys


class TestModuleImports(unittest.TestCase):
    
    @patch('builtins.__import__')
    def test_check_modules_missing_requests(self, mock_import):
        mock_import.side_effect = ImportError
        
        captured_output = io.StringIO()
        sys.stderr = captured_output
        
        with self.assertRaises(SystemExit) as cm:
            check_modules()

        sys.stderr = sys.__stderr__  # Restore stderr

        self.assertEqual(cm.exception.code, 1)
        self.assertIn("requests", captured_output.getvalue())

if __name__ == '__main__':
    unittest.main()
