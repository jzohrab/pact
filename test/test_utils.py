import unittest
import sys
import os

import pact.utils

class TestUtils_timeutils(unittest.TestCase):

    def assert_time_string(self, hrs, mins, secs, expected, case_name):
        ms = (hrs * 3600 + mins * 60 + secs) * 1000
        s = pact.utils.TimeUtils.time_string(ms)
        self.assertEqual(s, expected, case_name)

    def test_time_strings(self):
        self.assert_time_string(0, 16, 40, '16:40.0', 'basic')
        self.assert_time_string(0, 0, 0, '00:00.0', 'zero')
        self.assert_time_string(0, 10, 0, '10:00.0', 'ten')
        self.assert_time_string(0, 10, 0.1, '10:00.1', 'just after 0')
        self.assert_time_string(0, 9, 59.9999999999, '10:00.0', 'rounding')

        self.assert_time_string(1, 16, 40, '1:16:40.0', '1 hour')
        self.assert_time_string(10, 16, 40, '10:16:40.0', '10 hours')


class TestUtils_Recent(unittest.TestCase):

    def del_if_exists(self, f):
        if os.path.exists(f):
            os.remove(f)

    def setUp(self):
        self.size = 10
        self.filename = 'test/generated-ignored/.recent'
        self.del_if_exists(self.filename)
        self.recent = pact.utils.Recent(self.size, self.filename)

    def test_added_file_is_at_top_of_list(self):
        self.assertEqual(0, len(self.recent.entries), 'no entries')
        self.recent.add('a')
        self.assertEqual(['a'], self.recent.entries)
        self.recent.add('b')
        self.assertEqual(['b', 'a'], self.recent.entries)

    def test_adding_same_file_multiple_times_still_only_shown_once(self):
        self.assertEqual(0, len(self.recent.entries), 'no entries')
        self.recent.add('a')
        self.recent.add('a')
        self.recent.add('a')
        self.assertEqual(['a'], self.recent.entries)
        self.recent.add('b')
        self.recent.add('b')
        self.assertEqual(['b', 'a'], self.recent.entries)

    def test_adding_existing_file_just_moves_it_to_top_of_list(self):
        self.assertEqual(0, len(self.recent.entries), 'no entries')
        self.recent.add('a')
        self.assertEqual(['a'], self.recent.entries)
        self.recent.add('b')
        self.assertEqual(['b', 'a'], self.recent.entries)
        self.recent.add('a')
        self.assertEqual(['a', 'b'], self.recent.entries)

    def test_only_keep_the_latest_10_entries(self):
        for i in range(0, 10):
            self.recent.add(f'{i}')
        expected = [c for c in '9876543210']
        self.assertEqual(expected, self.recent.entries)
        self.recent.add('top')
        expected = ['top'] + [c for c in '987654321']  # no 0
        self.assertEqual(expected, self.recent.entries)

    def test_load_from_non_existent_file_ok(self):
        self.del_if_exists(self.filename)
        self.recent.load()
        self.assertEqual([], self.recent.entries, 'no entries')

    def test_save_and_reload_ok(self):
        self.recent.add('a')
        self.recent.add('b')
        self.recent.save()

        loaded = pact.utils.Recent(self.size, self.filename)
        self.assertEqual(loaded.entries, self.recent.entries, 'loaded')
