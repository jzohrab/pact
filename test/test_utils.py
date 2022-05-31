import unittest
import sys
import os

sys.path.append(os.path.abspath(sys.path[0]) + '/../')
from pact.utils import TimeUtils

class TestUtils_timeutils(unittest.TestCase):

    def assert_time_string(self, hrs, mins, secs, expected, case_name):
        ms = (hrs * 3600 + mins * 60 + secs) * 1000
        s = TimeUtils.time_string(ms)
        self.assertEqual(s, expected, case_name)

    def test_time_strings(self):
        self.assert_time_string(0, 16, 40, '16:40.0', 'basic')
        self.assert_time_string(0, 0, 0, '00:00.0', 'zero')
        self.assert_time_string(0, 10, 0, '10:00.0', 'ten')
        self.assert_time_string(0, 10, 0.1, '10:00.1', 'just after 0')
        self.assert_time_string(0, 9, 59.9999999999, '10:00.0', 'rounding')

        self.assert_time_string(1, 16, 40, '1:16:40.0', '1 hour')
        self.assert_time_string(10, 16, 40, '10:16:40.0', '10 hours')
