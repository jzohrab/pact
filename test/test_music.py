import unittest
import sys
import os
import json

sys.path.append(os.path.abspath(sys.path[0]) + '/../')
from pact.music import Bookmark

class TestBookmark_display(unittest.TestCase):

    def test_display(self):
        time = (5 * 60 + 14) * 1000 + 870
        b = Bookmark(time)
        self.assertEqual('Bookmark 05:14.9', b.display())

        b.clip_bounds_ms = [time, None]
        self.assertEqual('Bookmark 05:14.9', b.display())

        b.clip_bounds_ms = [time, time + 1000]
        self.assertEqual('05:14.9 - 05:15.9', b.display())

        b.transcription = ''
        self.assertEqual('05:14.9 - 05:15.9', b.display())

        s = 'long string of stuff'
        b.transcription = s
        self.assertEqual(f'05:14.9 - 05:15.9  "{s}"', b.display(100))

class TestBookmark_serialization(unittest.TestCase):

    def test_sanity(self):
        b = Bookmark(42.0)
        self.assertEqual(42.0, b.position_ms)
        self.assertIsNone(b.clip_bounds_ms)
        self.assertIsNone(b.transcription)

    def test_to_from_dict_nothing_set(self):
        b = Bookmark(42.0)
        jb = Bookmark.from_dict(b.to_dict())
        self.assertEqual(42.0, jb.position_ms)
        self.assertIsNone(jb.clip_bounds_ms)
        self.assertIsNone(jb.transcription)

    def test_to_from_dict(self):
        b = Bookmark(42.0)
        b.clip_bounds_ms = [55.0, 66.0]
        b.transcription = '"Here is some transcription with \n\n things."'
        jb = Bookmark.from_dict(b.to_dict())
        self.assertEqual(b.position_ms, jb.position_ms)
        self.assertEqual(b.clip_bounds_ms, jb.clip_bounds_ms)
        self.assertEqual(b.transcription, jb.transcription)

    # Smoke test, really.
    def test_to_from_json(self):
        b = Bookmark(42.0)
        b.clip_bounds_ms = [55.0, 66.0]
        b.transcription = '"Here is some transcription with \n\n things."'
        b_json = json.dumps(b.to_dict())
        # print(b_json)
        jb = Bookmark.from_dict(json.loads(b_json))
        self.assertEqual(b.position_ms, jb.position_ms)
        self.assertEqual(b.clip_bounds_ms, jb.clip_bounds_ms)
        self.assertEqual(b.transcription, jb.transcription)
