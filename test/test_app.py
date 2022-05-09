import unittest
import tkinter
from tkinter import _tkinter
from tkinter import ttk
import os
import sys
from tkinter import Tk
import pact.app
import time



class TKinterTestCase(unittest.TestCase):

    def setUp(self):
        # print('doing main setup')
        self.was_quit = False
        self.root=tkinter.Tk()

        # print('doing child setup')
        config = pact.app.Config.from_file('test/assets/test-config.ini')
        self.app = pact.app.MainWindow(self.root, config)
        self.assertIsNone(self.app.music_file, 'Sanity check, nothing loaded at start')

        self.childSetUp()

    def childSetUp(self):
        pass

    def tearDown(self):
        self.childTearDown()

        if self.root and not self.was_quit:
            self.app.quit()
            self.pump_events()
        else:
            # print('Already quit')
            pass

    def childTearDown(self):
        pass

    def pump_events(self):
        while self.root.tk.dooneevent(_tkinter.ALL_EVENTS | _tkinter.DONT_WAIT):
            pass


class TestApp_smoke(TKinterTestCase):

    def test_open_and_close(self):
        self.app.quit()
        self.was_quit = True
        self.assertRaises(tkinter.TclError, lambda: self.app.window.winfo_viewable())


class TestApp_move_slider_hotkeys(TKinterTestCase):

    def test_smoke(self):
        self.app._load_song_details('test/assets/spanish_10_seconds.mp3')
        self.pump_events()

        def _assert_slider_details(expected_lbl_text, expected_slider_pos):
            self.pump_events()
            lbltxt = self.app.slider_lbl.cget('text')
            self.assertEqual(expected_lbl_text, lbltxt, 'Label updated')
            self.assertEqual(expected_slider_pos, self.app.slider.get(), 'slider value')

        sliderpos = 5600
        self.app.reposition(sliderpos)
        _assert_slider_details('00:05.6', sliderpos)

        self.app.window.event_generate('<Right>')
        _assert_slider_details('00:05.7', sliderpos + 100)

        self.app.window.event_generate('<Left>')
        _assert_slider_details('00:05.6', sliderpos)

        self.app.window.event_generate('<Command-Right>')
        _assert_slider_details('00:06.6', sliderpos + 1000)


class TestApp_add_bookmarks(TKinterTestCase):

    def test_load_file_add_bookmark(self):
        self.app._load_song_details('test/assets/spanish_10_seconds.mp3')
        self.pump_events()
        # time.sleep(1)
        self.assertEqual(len(self.app.bookmarks), 1, 'one entry, the song itself')

        sliderpos = 5600
        self.app.reposition(sliderpos)
        self.pump_events()

        # "Add bookmark" hotkey.
        self.app.window.event_generate('<m>')
        self.pump_events()

        self.assertEqual(len(self.app.bookmarks), 2, 'bookmark added')
        b = self.app.bookmarks[1]
        self.assertEqual(sliderpos, b.position_ms, 'position ok.')

class TestApp_clip_window(TKinterTestCase):

    def test_open_clip_window_for_bookmark(self):
        self.app._load_song_details('test/assets/spanish_10_seconds.mp3')
        self.pump_events()

        sliderpos = 5600
        self.app.reposition(sliderpos)
        self.pump_events()

        # "Add bookmark" hotkey.
        self.app.window.event_generate('<m>')
        self.pump_events()

        self.assertEqual(len(self.app.bookmarks), 2, 'sanity check')
        b = self.app.bookmarks[1]
        self.assertEqual(sliderpos, b.position_ms, 'position ok.')

        self.assertIsNone(self.app.bookmark_window, 'No popup yet.')

        self.app.popup_clip_window()
        self.pump_events()
        self.assertIsNotNone(self.app.bookmark_window, 'Now have popup')

        popup = self.app.bookmark_window
        self.assertTrue(popup.root.winfo_viewable(), 'popup visible')

        popup.ok()
        # pump popup events ????
        while popup.root.tk.dooneevent(_tkinter.ALL_EVENTS | _tkinter.DONT_WAIT):
            pass

        self.pump_events()

        self.assertRaises(tkinter.TclError, lambda: popup.root.winfo_viewable())

        self.assertIsNone(self.app.bookmark_window, 'Popup unset')


    def test_setting_clip_start_and_end_in_popup_changes_bookmark(self):
        self.app._load_song_details('test/assets/spanish_10_seconds.mp3')
        self.pump_events()

        sliderpos = 5600
        self.app.reposition(sliderpos)
        self.pump_events()

        # "Add bookmark" hotkey.
        self.app.window.event_generate('<m>')
        self.pump_events()

        self.assertEqual(len(self.app.bookmarks), 2, 'sanity check')

        self.app.popup_clip_window()
        self.pump_events()

        popup = self.app.bookmark_window
        self.assertIsNotNone(popup, 'sanity check, have popup')
        self.assertTrue(popup.root.winfo_viewable(), 'popup visible')

        popup.reposition(sliderpos - 1000)
        self.pump_events()
        popup.set_clip_start()
        self.pump_events()

        popup.reposition(sliderpos + 1000)
        self.pump_events()
        popup.set_clip_end()
        self.pump_events()

        popup.ok()
        self.pump_events()

        b = self.app.bookmarks[1]
        self.assertEqual(b.clip_bounds_ms, [ sliderpos - 1000, sliderpos + 1000 ], 'bounds set')





if __name__ == '__main__':
    import unittest
    unittest.main()
