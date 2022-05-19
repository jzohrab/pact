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

        clipstart = (5 * 60 + 7) * 1000 + 666
        b.clip_bounds_ms = [clipstart, None]
        self.assertEqual('Bookmark 05:14.9', b.display())

        b.clip_bounds_ms = [clipstart, clipstart + 1000]
        bounds_as_text = '05:07.7 - 05:08.7'
        self.assertEqual(bounds_as_text, b.display())

        b.transcription = ''
        self.assertEqual(bounds_as_text, b.display())

        s = 'long string of stuff'
        b.transcription = s
        self.assertEqual(f'{bounds_as_text}  "{s}"', b.display(100))

        b.exported = True
        checkmark = '\u2713'
        self.assertEqual(f'{checkmark} {bounds_as_text}  "{s}"', b.display(100))


    def test_square_bracketed_text_is_omitted(self):
        """
        textmatch.py sometimes adds context in square brackets before and
        after a clip, but when listing the bookmarks don't bother
        showing that, just show what the clip text actually was.
        """
        time = (5 * 60 + 14) * 1000 + 870
        b = Bookmark(time)
        b.clip_bounds_ms = [time, time + 1000]
        b.transcription = "[Some text] ... and things ... [ok]"
        self.assertEqual(f'05:14.9 - 05:15.9  "... and things ..."', b.display(100))

        self.assertEqual(f'05:14.9 - 05:15.9  "... and th ..."', b.display(10))

class TestBookmark_slider_pos_ms(unittest.TestCase):

    def test_slider_pos_depends_on_bounds(self):
        time = 100
        b = Bookmark(time)
        self.assertEqual(b.effective_pos_ms, time, 'time')

        b.clip_bounds_ms = [42, None]
        self.assertEqual(b.effective_pos_ms, time, 'incomplete clip def')

        b.clip_bounds_ms = [42, 52]
        self.assertEqual(b.effective_pos_ms, 42, 'now at clip start')

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
        self.assertFalse(jb.exported, 'backwards-compat check')

    def test_to_from_dict_exported_set(self):
        b = Bookmark(42.0)
        b.clip_bounds_ms = [55.0, 66.0]
        b.transcription = '"Here is some transcription with \n\n things."'
        b.exported = True
        jb = Bookmark.from_dict(b.to_dict())
        self.assertTrue(jb.exported)

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
