import unittest
import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)

sys.path.append(os.path.abspath(sys.path[0]) + '/../')
import pact.split


class TestSplit_sensible_start_times(unittest.TestCase):

    def assert_compressed(self, arr, minlen, expected):
        actual = pact.split.sensible_start_times(arr, minlen)
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


class TestSplit_raw_chunks_characterization(unittest.TestCase):

    def setUp(self):
        logger.debug('\n\n')
        # pact.split.logger.setLevel(logging.DEBUG)

    def tearDown(self):
        pass
        # pact.split.logger.setLevel(logging.INFO)

    def test_characterization_full_clip(self):
        """Recording silences for refactoring."""
        actual = pact.split.raw_chunks(
            in_filename = 'test/assets/testing.mp3',
            silence_threshold = -10,
            silence_duration = 0.3,
            end_ms = 100000
        )
        expected = [
            (0.0, 773),
            (1142, 3413),
            (3801, 5369),
            (5918, 7311),
            (7645, 8379),
            (8893, 9998),
            (10419, 11844),
            (12295, 13273),
            (13721, 14805),
            (15386, 100000)
        ]
        self.assertEqual(actual, expected)


    def test_characterization_trimmed_with_silence_on_each_side(self):
        # Hard to find the "right" start_ms and end_ms for
        # raw_chunks ... have to pick them such that the
        # silence is long enough to be recognized.
        actual = pact.split.raw_chunks(
            in_filename = 'test/assets/testing.mp3',
            silence_threshold = -10,
            silence_duration = 0.3,
            start_ms = 7320,
            end_ms = 10400
        )
        expected = [
            (7645, 8379),
            (8893, 9998)
        ]
        self.assertEqual(actual, expected)


    def test_characterization_various_single_chunk(self):
        def test_case(name, start_ms, end_ms, expected):
            logger.debug(f'\n{name}:')
            actual = pact.split.raw_chunks(
                in_filename = 'test/assets/testing.mp3',
                silence_threshold = -10,
                silence_duration = 0.3,
                start_ms = start_ms,
                end_ms = end_ms
            )
            self.assertEqual(actual, expected, name)

        test_case('start sound, end silence', 8000, 8800, [(8000, 8379)])
        test_case('start silence, end sound', 7320, 8200, [(7645, 8200)])
        test_case('start sound, end sound', 7800, 8200, [(7800, 8200)])
        test_case('no chunks', 10000, 10400, [])


class TestSplit_silences(unittest.TestCase):

    def test_two_chunks(self):
        actual = pact.split.silences([(0, 500), (600, 1000)])
        self.assertEqual(actual, [100])

    def test_single_chunk_no_silences(self):
        actual = pact.split.silences([(0, 500)])
        self.assertEqual(actual, [])


class TestSplit_group_chunks(unittest.TestCase):
    """INCOMPLETE, NOT IMPLEMENTED ...

Grouping chunks, using their silence intervals to determine likely groupings.

For example, given the following audio recording, where each character
represents 1 second of audio, and each space is 1 second of silence:

   aaa bbb ccc   ddd eee     fff ggg

The sound and silence implies that there are the following phrases:

aaa bbb ccc
ddd eee
fff ggg

Note that ccc is joined with aaa bbb, instead of with ddd, because the
spacing implies that ccc belongs with the earlier clips.

This consideration is important because it's common to get very small
chunks of sound when splitting using ffmeg, followed by long periods
of silence.  These small chunks should be grouped with prior chunks,
rather than being used as the starting point for new grouped chunks.
    """

    def test_first_case(self):
        chunks = [
            (1, 4),
            (9, 10),
            (12, 15),
            (20, 24),
            (26, 30)
        ]
        expected = [
            [
                (1, 4)
            ],
            [
                (9, 10),
                (12, 15)
            ],
            [
                (20, 24),
                (26, 30)
            ]
        ]
