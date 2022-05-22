import unittest
import sys
import os

sys.path.append(os.path.abspath(sys.path[0]) + '/../')
from pact.split import sensible_start_times, make_bounds


class TestSplit_sensible_start_times(unittest.TestCase):

    def assert_compressed(self, arr, minlen, expected):
        actual = sensible_start_times(arr, minlen)
        self.assertEqual(actual, expected)

    def test_compress(self):
        cases = [
            [ [*range(0, 12)], 5, [0,5,10] ],
            [ [0, 1, 5, 8, 20], 4, [0, 5, 20] ],
            [ [0, 4, 10, 20], 5, [0, 10, 20] ],
            [ [0, 1, 1.1, 1.2, 1.3, 2, 2.1, 2.2 ], 1, [0, 1, 2] ],
            [ [0, 1.3, 2, 1, 2.1, 1.1, 1.2, 2.2 ], 1, [0, 1, 2] ]
        ]
        for c in cases:
            self.assert_compressed(c[0], c[1], c[2])


class TestSplit_make_bounds(unittest.TestCase):

    def test_bounds(self):
        endtime = 1000
        cases = [
            [ [1, 2, 3], [ [1,2], [2,3], [3, endtime] ] ],
            [ [], [] ],
            [ [1], [ [1, endtime] ] ]
        ]
        for c in cases:
            actual = make_bounds(c[0], endtime)
            self.assertEqual(actual, c[1])
        
