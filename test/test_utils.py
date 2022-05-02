import unittest
import sys
import os

sys.path.append(os.path.abspath(sys.path[0]) + '/../')
from pact.utils import TimeUtils

class TestUtils(unittest.TestCase):

    def assert_time_string(self, mins, secs, expected, case_name):
        ms = (mins * 60 + secs) * 1000
        s = TimeUtils.time_string(ms)
        self.assertEqual(s, expected, case_name)

    def test_time_strings(self):
        self.assert_time_string(16, 40, '16:40.0', 'basic')
        self.assert_time_string(0, 0, '00:00.0', 'zero')
        self.assert_time_string(10, 0, '10:00.0', 'ten')
        self.assert_time_string(10, 0.1, '10:00.1', 'just after 0')
        self.assert_time_string(9, 59.9999999999, '10:00.0', 'rounding')
