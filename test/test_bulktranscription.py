import unittest
import sys
import os

sys.path.append(os.path.abspath(sys.path[0]) + '/../')
from pact.bulktranscription import make_bounds

class TestBulkTranscription_make_bounds(unittest.TestCase):

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

