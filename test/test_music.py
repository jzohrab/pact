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
        self.assertEqual('05:14.9', b.display())

        clipstart = (5 * 60 + 7) * 1000 + 666
        start_as_text = '05:07.7'
        b.clip_bounds_ms = [clipstart, None]
        self.assertEqual(start_as_text, b.display())

        b.clip_bounds_ms = [clipstart, clipstart + 1000]
        self.assertEqual(start_as_text, b.display())

        b.transcription = ''
        self.assertEqual(start_as_text, b.display())

        pencil = '\u270E'
        b.transcription = 'long string of stuff'
        self.assertEqual(f'{start_as_text} {pencil}', b.display())

        b.exported = True
        checkmark = '\u2713'
        self.assertEqual(f'{checkmark} {start_as_text} {pencil}', b.display())


    def test_square_bracketed_text_is_ignored(self):
        time = (5 * 60 + 14) * 1000 + 870
        b = Bookmark(time)
        b.clip_bounds_ms = [time, time + 1000]
        b.transcription = "[Some text] ... and things ... [ok]"

        pencil = '\u270E'
        self.assertEqual(f'05:14.9 {pencil}', b.display())
        self.assertEqual(f'05:14.9 {pencil}', b.display())


    def test_note_with_angle_bracket_showed_in_display(self):
        time = (5 * 60 + 14) * 1000 + 870
        b = Bookmark(time)
        b.clip_bounds_ms = [time, time + 1000]
        self.assertEqual('05:14.9', b.display())

        b.notes = 'nobracket'
        self.assertEqual('05:14.9', b.display())

        b.notes = '<something>'
        self.assertEqual('something', b.display())


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
        self.assertEqual(b.notes, jb.notes)
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
        b.notes = "And here are some extra notes!\n* bullet\n*bullet 2"
        b_json = json.dumps(b.to_dict())
        # print(b_json)
        jb = Bookmark.from_dict(json.loads(b_json))
        self.assertEqual(b.position_ms, jb.position_ms)
        self.assertEqual(b.clip_bounds_ms, jb.clip_bounds_ms)
        self.assertEqual(b.transcription, jb.transcription, 'txn')
        self.assertEqual(b.notes, jb.notes, 'notes')
