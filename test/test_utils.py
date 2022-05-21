import unittest
import sys
import os

sys.path.append(os.path.abspath(sys.path[0]) + '/../')
from pact.utils import TimeUtils, compress_array_of_start_times

class TestUtils_timeutils(unittest.TestCase):

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


class TestUtils_compress_array_of_start_times(unittest.TestCase):

    def assert_compressed(self, arr, minlen, expected):
        actual = compress_array_of_start_times(arr, minlen)
        self.assertEqual(actual, expected)

    def test_compress(self):
        cases = [
            [ [*range(0, 12)], 5, [0,5,10] ],
            [ [0, 1, 5, 8, 20], 4, [0, 5, 20] ],
            [ [0, 4, 10, 20], 5, [0, 10, 20] ],
            [ [0, 1, 1.1, 1.2, 1.3, 2, 2.1, 2.2 ], 1, [0, 1, 2] ]
        ]
        for c in cases:
            self.assert_compressed(c[0], c[1], c[2])
