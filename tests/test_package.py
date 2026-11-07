import unittest

import py_vchart


class PackageTests(unittest.TestCase):
    def test_version_is_available(self):
        self.assertTrue(py_vchart.__version__)
