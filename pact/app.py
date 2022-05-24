# GUI

import configparser
import json
import matplotlib.pyplot as plt
import numpy as np
import os
import pickle
import tkinter.ttk as ttk
import wave

from matplotlib import pyplot
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from mutagen.mp3 import MP3
from pydub import AudioSegment
from tempfile import NamedTemporaryFile
from tkinter import *
from tkinter import filedialog
import tkinter.scrolledtext as scrolledtext
from tkinter import messagebox

import pact.music
import pact.utils
import pact.widgets
from pact.utils import TimeUtils
from pact._version import __version__
import pact.textmatch
from pact.plugins.transcription import vosktranscription, unknown
import pact.split

class Config(configparser.ConfigParser):

    def __init__(self):
        super().__init__()

        # Hook point for doing different kinds of transcription, eg for testing.
        self.transcription_strategy = None

        # Auto-save the session .pact file when a bookmark changes.
        self.autosave = True

        # Automatically play clips when the clip popup window opens.
        self.autoplayclips = True

    @staticmethod
    def from_file(filename):
        """Return configparser.config for config.ini, or the value in PACTCONFIG env var."""
        config = Config()
        config.read(filename)

        ts = unknown.NeedsConfiguration()
        voskmodel = config['Pact'].get('VoskModel', '')
        # print(f'got vosk model = {voskmodel}')
        if voskmodel != '':
            ts = vosktranscription.VoskTranscriptionStrategy(voskmodel)
        config.transcription_strategy = ts
        
        os.environ['PACT.Vosk.Model'] = 'DUMMY_HERE'
        return config


class MainWindow:

    class FullTrackBookmark(pact.music.Bookmark):
        def __init__(self):
            super().__init__(0)
        def display(self):
            return "<Full Track>"


    def __init__(self, window, config):
        window.title(f'Pact v{__version__}')
        window.geometry('600x450')
        self.window = window
        self.window.protocol('WM_DELETE_WINDOW', self.quit)

        self.config = config
        self.music_file = None
        self.song_length_ms = 0
        self.transcription_file = None

        # Storing the session filename for auto-saving, because it's a
        # hassle keeping track of dirty/not.  Just keep saving for
        # now.
        self.session_file = None

        self.set_title()

        # popup window for editing clips, storing as member for testing.
        self.bookmark_window = None

        menubar = Menu(self.window)
        self.menubar = menubar
        self.window['menu'] = menubar
        menu_file = Menu(menubar)
        menubar.add_cascade(menu=menu_file, label='File')
        menu_file.add_command(label='Open mp3', command=self.menu_load_mp3)
        menu_file.add_command(label='Open transcription', command=self.load_transcription)
        menu_file.add_separator()
        menu_file.add_command(label='Open session', command=self.menu_load_pact_file)
        menu_file.add_command(label='Save session', command=self.menu_save_pact_file)
        menu_file.add_separator()
        menu_file.add_command(label='Close', command=self.quit)

        # Layout
        master_frame = Frame(window)
        master_frame.grid(row=0, column=0, padx=30, pady=30)

        bk_frame = Frame(master_frame)
        bk_frame.grid(row=2, column=0, pady=20, sticky='W')

        # The bookmarks saved during play.
        listbox_frame = Frame(bk_frame)
        listbox_frame.grid(row = 0, column = 0, sticky='NW')
        self.bookmarks = []
        self.bookmarks_lst = Listbox(
            listbox_frame,
            width=10,
            height = 10,
            borderwidth=0, highlightthickness=0,
            selectbackground="yellow",
            selectforeground="black")
        self.bookmarks_lst.grid(row=0, column=2)
        self.bookmarks_lst.bind('<<ListboxSelect>>', self.on_bookmark_select)

        scrollbar = ttk.Scrollbar(listbox_frame, orient= 'vertical')
        scrollbar.grid(row=0, column=1, padx=5, sticky='NS')
        self.bookmarks_lst.config(yscrollcommand= scrollbar.set)
        scrollbar.config(command= self.bookmarks_lst.yview)

        deffont = font.nametofont("TkDefaultFont")
        self.bookmark_transcription_font = font.Font(font=deffont)
        size = deffont.actual()["size"]
        self.bookmark_transcription_font.configure(size=size+6)
        self.bookmark_notes_font = font.Font(font=self.bookmark_transcription_font)
        self.bookmark_notes_font.configure(slant='italic', size=size+2)

        self.bk_text = scrolledtext.ScrolledText(
            bk_frame,
            height = 10, width = 30,
            wrap=WORD, borderwidth=0,
            font = self.bookmark_transcription_font,
            spacing2 = 5,  # Line spacing
        )
        self.bk_text.configure(state="disabled")
        self.bk_text.grid(row=0, column=2, padx=20, sticky='NW')
        bk_frame.columnconfigure(3, weight=2)

        ctl_frame = Frame(master_frame)
        ctl_frame.grid(row=1, column=0, pady=10, sticky='W')

        def _make_button(text, column, command):
            b = Button(ctl_frame, text=text, width=8, command=command)
            b.grid(row=0, column=column, padx=5)
            return b

        self.play_btn = _make_button('Play', 1, self.play_pause)
        _make_button('Bookmark', 2, self.add_bookmark_at_current)
        _make_button('Delete', 3, self.delete_selected_bookmark)
        _make_button('Clip', 4, self.popup_clip_window)

        slider_frame = Frame(master_frame)
        slider_frame.grid(row=0, column=0, pady=5, sticky='W')

        self.slider_var = DoubleVar()

        self.slider = ttk.Scale(
            slider_frame,
            from_=0,
            to=100,
            orient=HORIZONTAL,
            variable = self.slider_var,
            length=360)
        self.slider.grid(row=0, column=1, pady=0)

        self.slider_lbl = Label(slider_frame, text='')
        self.slider_lbl.grid(row=1, column=1, pady=2)
        self.slider_var.trace('w', lambda a,b,c: self.on_slider_var_update())

        self.music_player = pact.music.MusicPlayer(self.slider, self.update_play_button_text)

        # Previously, I had 'space' handle start/stop, but that
        # also triggers a re-selection of the currently selected
        # bookmark.
        window.bind('<Command-p>', lambda e: self.play_pause())
        window.bind('<Right>', lambda e: self.increment(100))
        window.bind('<Left>', lambda e: self.increment(-100))
        window.bind('<Command-Right>', lambda e: self.increment(1000))
        window.bind('<Command-Left>', lambda e: self.increment(-1000))
        window.bind('<m>', lambda e: self.add_bookmark_at_current())
        window.bind('<u>', lambda e: self.update_selected_bookmark(float(self.slider.get())))
        window.bind('<d>', lambda e: self.delete_selected_bookmark())
        window.bind('<Return>', lambda e: self.popup_clip_window())


    def on_slider_var_update(self):
        v = self.slider_var.get()
        self.slider_lbl.configure(text=TimeUtils.time_string(v))

        def _time_within_bookmark_clip(b):
            if b.clip_bounds_ms is None:
                return False
            s, e = b.clip_bounds_ms
            return v >= s and v <= e

        # Possible for clips to overlap ...  Seach for the bookmarks
        # in reverse order, and pick the last one.
        found = None
        for i in range(len(self.bookmarks) - 1, -1, -1):
            if _time_within_bookmark_clip(self.bookmarks[i]):
                found = i
                break

        if found is None:
            lst = self.bookmarks_lst
            lst.selection_clear(0, END)
            self.display_bookmark_transcription(None)
            return

        if found != self._selected_bookmark_index():
            print(f'found != curr which is {self._selected_bookmark_index()}')
            lst = self.bookmarks_lst
            lst.selection_clear(0, END)
            lst.activate(found)
            lst.select_set(found)
            lst.see(found)
            b = self.bookmarks[found]
            self.display_bookmark_transcription(b)


    def init_dev(self):
        if not self.config.has_section('Dev'):
            return
        devsettings = self.config['Dev']

        f = devsettings.get('SessionFile', None)
        if f:
            self.load_pact_file(f)

            i = devsettings.get('LoadBookmark', None)
            if i and i != 0:
                self.popup_clip_window(int(i))
            return

        f = devsettings.get('LoadFile', None)
        if f:
            self.load_mp3(f)
            return

    def popup_clip_window(self, bookmark_index = None):
        i = bookmark_index
        if i is None:
            i = self._selected_bookmark_index()
        if i is None or i == 0:
            return
        b = self.bookmarks[i]

        self.music_player.pause()
        self.menubar.entryconfig(1, state = 'disabled')
        popup = BookmarkWindow(
            parent = self.window,
            config = self.config,
            bookmark = b,
            allbookmarks = self.bookmarks,
            music_file = self.music_file,
            song_length_ms = self.song_length_ms,
            transcription_file = self.transcription_file,
            on_close = lambda: self.popup_clip_window_closed(i)
        )
        self.bookmark_window = popup

        # Note: previously, this method used
        # "self.window.wait_window(popup.root)", but this was
        # problematic during unit testing as the code would block
        # until the popup closed.  Using an 'on_close' callback
        # results in the same effect (modal popup), and doesn't block
        # the main thread.


    def popup_clip_window_closed(self, i):
        if self.config.autosave:
            self.save_pact_file()

        self.bookmark_window.root.grab_release()
        self.bookmark_window = None

        self.menubar.entryconfig(1, state = 'normal')
        # Re-select, b/c switching to the pop-up deselects the current.
        self.bookmarks_lst.activate(i)
        self.bookmarks_lst.select_set(i)
        self.reload_bookmark_list()
        self.bookmarks_lst.see(i)
        b = self.bookmarks[i]
        self.move_to_bookmark(b)
        self.display_bookmark_transcription(b)


    def reload_bookmark_list(self):
        selected_index = self._selected_bookmark_index()
        self.bookmarks_lst.delete(0, END)
        for b in self.bookmarks:
            self.bookmarks_lst.insert(END, b.display())
        if selected_index:
            self.bookmarks_lst.activate(selected_index)
            self.bookmarks_lst.select_set(selected_index)


    def add_bookmark_at_current(self, m = None):
        v = m
        if v is None:
            v = float(self.slider.get())
        b = pact.music.Bookmark(v)
        self.add_bookmark(b)


    def add_bookmark(self, b):
        if self.music_file is None:
            return
        self.bookmarks.append(b)

        if self.config.autosave:
            self.save_pact_file()

        i = len(self.bookmarks) - 1
        lst = self.bookmarks_lst
        lst.selection_clear(0, END)
        lst.insert(END, b.display())
        lst.activate(i)
        lst.select_set(i)
        lst.see(i)


    def _selected_bookmark_index(self):
        s = self.bookmarks_lst.curselection()
        if len(s) == 0:
            return None
        return int(s[0])


    def update_selected_bookmark(self, new_value_ms):
        i = self._selected_bookmark_index()
        if not i:
            return
        b = self.bookmarks[i]
        if (b.position_ms == new_value_ms):
            return
        b.position_ms = new_value_ms
        self.reload_bookmark_list()


    def delete_selected_bookmark(self):
        index = self._selected_bookmark_index()
        if not index or index == 0:
            return
        del self.bookmarks[index]
        self.reload_bookmark_list()


    def display_bookmark_transcription(self, b):
        t = self.bk_text
        t.tag_delete('italic')
        t.configure(state="normal")
        t.delete(1.0, END)

        if b is None:
            return

        if b.transcription and b.transcription.strip() != '':
            t.insert(1.0, b.transcription)

        if b.notes and b.notes.strip() != '':
            curr_end = t.index(END)
            t.insert(END, '\n\n')
            t.insert(END, b.notes)
            t.tag_add('italic', curr_end, END)
            t.tag_configure('italic', font=self.bookmark_notes_font)

        t.configure(state="disabled")

    def on_bookmark_select(self, event):
        index = self._selected_bookmark_index()
        if not index:
            return
        b = self.bookmarks[index]
        self.move_to_bookmark(b)
        self.display_bookmark_transcription(b)


    def move_to_bookmark(self, b):
        self.music_player.reposition(b.effective_pos_ms)


    def reposition(self, value_ms_f):
        """Reposition for automation."""
        self.music_player.reposition(value_ms_f)

    def increment(self, delta):
        self.music_player.increment(delta)


    def menu_load_mp3(self):
        f = filedialog.askopenfilename(filetypes = (("mp3", "*.mp3"),))
        if f:
            # No longer using existing session.
            self.session_file = None
            self.load_mp3(f)
        else:
            print("no file?")


    def load_mp3(self, f):
        song_mut = MP3(f)
        self.song_length_ms = song_mut.info.length * 1000  # length is in seconds
        self.reposition(0)
        self.slider.config(to = self.song_length_ms, value=0)
        self.slider_lbl.configure(text=TimeUtils.time_string(self.song_length_ms))

        self.music_file = f
        self.set_title()

        self.music_player.load_song(f, self.song_length_ms)
        self.bookmarks = [ MainWindow.FullTrackBookmark() ]
        self.reload_bookmark_list()

        if self.session_file is None:
            self.session_file = f"{self.music_file}.temp.pact"
            self.save_pact_file()


    def load_transcription(self):
        initialdir = '.'
        if self.music_file:
            initialdir = os.path.dirname(self.music_file)
        f = filedialog.askopenfilename(
            initialdir = initialdir,
            filetypes = (("Text file", "*.txt"),))
        if f:
            self._load_transcription(f)
        else:
            print("no transcription file")


    def _load_transcription(self, f):
        self.transcription_file = f
        self.set_title()


    def set_title(self):
        parts = [ self.music_file, self.transcription_file ]
        parts = [ os.path.basename(x) for x in parts if x ]
        header = ' / '.join(parts)
        pv = f"Pact v{__version__}"
        t = ': '.join([ s for s in [ pv, header ] if s ])
        self.window.title(t)


    def play_pause(self):
        self.music_player.play_pause()


    def update_play_button_text(self, music_player_state):
        txt = 'Play'
        if music_player_state is pact.music.PlayerState.PLAYING:
            txt = 'Pause'
        self.play_btn.configure(text = txt)


    def quit(self):
        self.music_player.stop()
        self.window.destroy()


    class ApplicationState:

        def __init__(self):
            self.music_file = None
            self.transcription_file = None
            self.music_player_pos = None
            self.bookmarks = []

        @staticmethod
        def from_app(mainwindow):
            s = MainWindow.ApplicationState()
            s.music_file = mainwindow.music_file
            s.transcription_file = mainwindow.transcription_file
            s.music_player_pos = mainwindow.music_player.get_pos()
            s.bookmarks = mainwindow.bookmarks
            return s

        def print(self):
            print(self.to_dict())

        def to_dict(self):
            """For serialization."""
            return {
                'music_file': self.music_file,
                'transcription_file': self.transcription_file,
                'music_player_pos': self.music_player_pos,
                'bookmarks': [ b.to_dict() for b in self.bookmarks ]
            }

        @staticmethod
        def from_dict(d):
            s = MainWindow.ApplicationState()
            s.music_file = d['music_file']
            s.transcription_file = d['transcription_file']
            s.music_player_pos = d['music_player_pos']
            s.bookmarks = [ pact.music.Bookmark.from_dict(bd) for bd in d['bookmarks'] ]
            return s


    def menu_save_pact_file(self):
        """Save app state for later reload."""
        initialdir = os.path.dirname(self.music_file)
        fname, ext = os.path.splitext(os.path.basename(self.music_file))
        initialfile = f'{fname}.pact'

        # Use existing session file, if that's set.
        if (self.session_file):
            initialdir = os.path.dirname(self.session_file)
            initialfile = os.path.basename(self.session_file)

        f = filedialog.asksaveasfilename(
            initialdir = initialdir,
            initialfile = initialfile,
            filetypes = (("Pact clips file", "*.pact"),))
        if f is None or f ==  '':
            print("Cancelled")
            return

        self.session_file = f
        self.save_pact_file()


    def save_pact_file(self):
        """Save session, either explicitly from user or on bookmark changed."""
        if self.session_file is None:
            # print('No session file, not saving.')
            return

        appstate = MainWindow.ApplicationState.from_app(self)
        j = json.dumps(appstate.to_dict(), indent = 2)
        with open(self.session_file, "w") as dest:
            dest.write(j)

    def menu_load_pact_file(self):
        """Load previously pickled state."""
        f = filedialog.askopenfilename(filetypes = (("Pact clips file", "*.pact"),))
        self.load_pact_file(f)


    def load_pact_file(self, sessionfile):
        if sessionfile is None or sessionfile == '':
            print("Cancelled")
            return
        appstate = None

        j = None
        with open(sessionfile, "r") as src:
            j = json.loads(src.read())

        appstate = MainWindow.ApplicationState.from_dict(j)
        # appstate.print()

        def _is_present(fieldname, filename):
            if filename is not None and os.path.exists(filename):
                return True

            msg = f"""Missing {fieldname}: {filename}

Session file: {sessionfile}

Update '{fieldname}' in the session file and try again."""
            messagebox.showerror(title = f'Missing {fieldname}', message=msg)
            return False

        if not _is_present('music_file', appstate.music_file):
            return
        if appstate.transcription_file is not None and not _is_present('transcription_file', appstate.transcription_file):
            return

        self.session_file = sessionfile

        self.load_mp3(appstate.music_file)

        self._load_transcription(appstate.transcription_file)
        self.music_player.reposition(appstate.music_player_pos)
        self.bookmarks = appstate.bookmarks

        # First bookmark is really a fake bookmark.
        self.bookmarks[0] = MainWindow.FullTrackBookmark()

        self.reload_bookmark_list()


class BookmarkWindow(object):
    """Bookmark / clip editing window."""

    def __init__(self, parent, config, bookmark, allbookmarks, music_file, song_length_ms, transcription_file, on_close):
        self.config = config
        self.bookmark = bookmark
        self.music_file = music_file
        self.song_length_ms = song_length_ms
        self.transcription_file = transcription_file
        self.on_close = on_close

        self.parent = parent
        self.root=Toplevel(parent)
        self.root.protocol('WM_DELETE_WINDOW', self.ok)
        self.root.geometry('550x450')
        self.reposition_popup(parent, 50, 50)

        self.from_val, self.to_val = self.get_slider_from_to(bookmark, allbookmarks)

        # List of potential "clip start times" within the range.
        self.candidate_break_times = pact.split.segment_start_times(
            in_filename = music_file,
            start_ms = self.from_val,
            end_ms = self.to_val,
            min_duration_ms = 2000.0,
            shift_ms = 200.0
        )

        # Pre-calc graphing data.  If from_val or to_val change, must recalc.
        self.signal_plot_data = self.get_signal_plot_data(self.from_val, self.to_val)

        # Start the clip at the bookmark value for now, good enough.
        clip_bounds = bookmark.clip_bounds_ms
        if not bookmark.clip_bounds_ms:
            clip_bounds = [ bookmark.position_ms, bookmark.position_ms ]

        # TODO: can likely change these to regular floats, as they're
        # not controlling anything.
        self.entry_var = DoubleVar(value = bookmark.position_ms)
        self.start_var = DoubleVar(value = clip_bounds[0])
        self.end_var = DoubleVar(value = clip_bounds[1])

        self.slider_var = DoubleVar()

        slider_frame = Frame(self.root)
        slider_frame.grid(row=1, column=0, pady=5)

        w, fig = self.plot(slider_frame, 7)
        w.grid(row=0, column=0, pady=5)

        # Keep a handle on fig, so can close it when the window
        # closes; otherwise, this eventually gets a warning.
        # ref https://heitorpb.github.io/bla/2020/03/18/close-matplotlib-figures/
        self.fig = fig

        # Had to guess the best slider length, as I couldn't figure
        # out how to calculate it exactly using the matplotlib figure
        # dimensions.
        length_eyeballed = 7 * 55

        # Slider markers indicating clip start/end.
        c = Canvas(slider_frame, width=length_eyeballed, height = 10)
        c.grid(row = 1, column = 0, pady=0)
        self.clip_markers = pact.widgets.SliderMarkersWidget(c, length_eyeballed, self.from_val, self.to_val)
        self.clip_markers.add_marker(self.bookmark.position_ms, (0, 0, 10, 0, 5, 10), "blue")

        self.slider = Scale(
            slider_frame, orient = HORIZONTAL,
            length = length_eyeballed, sliderlength = 10,
            from_ = self.from_val, to = self.to_val, showvalue = 0,
            variable = self.slider_var)
        self.slider.grid(row=2, column=0, pady=5)

        self.slider_lbl = Label(slider_frame, text='')
        self.slider_lbl.grid(row=3, column=0, pady=2)
        def update_slider_label(a, b, c):
            self.slider_lbl.configure(text=TimeUtils.time_string(self.slider_var.get()))
        self.slider_var.trace('w', update_slider_label)

        ctl_frame = Frame(self.root)
        ctl_frame.grid(row=2, column=0, pady=2)

        self.play_btn = Button(ctl_frame, text='Play', width = 8, command=self.play_pause)
        self.play_btn.grid(row=0, column=0, padx=2)

        buttons = [
            [ 'Set start', self.set_clip_start ],
            [ 'Set end', self.set_clip_end ],
            [ 'Play clip', self.play_clip ],
            [ 'Transcribe', self.transcribe ]
        ]
        for index, arr in enumerate(buttons, start=2):
            text, comm = arr
            b = Button(ctl_frame, text = text, width = 8, command = comm)
            b.grid(row=0, column = index, padx=2)

        clip_details_frame = Frame(self.root) # , borderwidth=1, relief='groove')
        clip_details_frame.grid(row=3, column=0, pady=5)

        clip_interval_lbl = Label(clip_details_frame, text='-')

        def update_clip_interval_lbl():
            s = self.start_var.get()
            e = self.end_var.get()
            text = TimeUtils.interval_string(s, e, 'n/a')
            clip_interval_lbl.configure(text = f'{text} :')
            self.set_clip_bounds_markers()

        self.start_var.trace('w', lambda a,b,c: update_clip_interval_lbl())
        self.end_var.trace('w', lambda a,b,c: update_clip_interval_lbl())
        update_clip_interval_lbl()
        self.set_clip_bounds_markers()

        deffont = font.nametofont("TkDefaultFont")
        self.transcription_textbox = scrolledtext.ScrolledText(
            clip_details_frame,
            height = 4, width = 50, wrap=WORD, borderwidth=1,
            font = deffont,
            relief = 'solid'
        )
        if (self.bookmark.transcription):
            self.transcription_textbox.insert(1.0, self.bookmark.transcription.strip())

        clip_interval_lbl.grid(row=0, column=1, pady=2, sticky = W)
        self.transcription_textbox.grid(row=1, column = 1)

        self.transcription_progress = ttk.Progressbar(
            clip_details_frame,
            orient='horizontal',
            mode='determinate',
            length=280
        )
        self.transcription_progress['value'] = 0
        self.transcription_progress.grid(row=2, column = 1)

        notes_lbl = Label(clip_details_frame, text='Notes:')
        self.notes_textbox = scrolledtext.ScrolledText(
            clip_details_frame,
            height = 4, width = 50, wrap=WORD, borderwidth=1,
            font = deffont,
            relief = 'solid'
        )
        if (self.bookmark.notes):
            self.notes_textbox.insert(1.0, self.bookmark.notes.strip())

        notes_lbl.grid(row=3, column = 1, sticky = W)
        self.notes_textbox.grid(row=4, column = 1)

        exit_frame = Frame(self.root)
        exit_frame.grid(row=5, column=0, pady=5)
        buttons = [
            [ 'Lookup', self.lookup ],
            [ 'Export', self.export ],
            [ 'OK', self.ok ]
        ]
        for index, arr in enumerate(buttons, start=1):
            text, comm = arr
            b = Button(exit_frame, text = text, width = 10, command = comm)
            b.grid(row=0, column = index, padx=5)


        self.music_player = pact.music.MusicPlayer(self.slider, self.update_play_button_text)
        self.music_player.load_song(music_file, self.to_val)
        self.music_player.reposition(clip_bounds[0])
        # print(f'VALS: from={from_val}, to={to_val}, val={bookmark.position_ms}')

        # Hotkeys.  Note: I tried to bind the hotkeys in the "for
        # index, arr" loops above (since I'm just repeating the
        # commands already given in the arrays), but when I did so the
        # lambdas did not work ... they just closed the form.  Code in
        # loop was"self.root.bind(f'<{hotkey}>', lambda e: comm())".
        self.root.bind('<Command-p>', lambda e: self.play_pause())

        mp = self.music_player
        self.root.bind('<Right>', lambda e: mp.increment(100))
        self.root.bind('<Left>', lambda e: mp.increment(-100))
        self.root.bind('<Shift-Right>', lambda e: mp.increment(1000))
        self.root.bind('<Shift-Left>', lambda e: mp.increment(-1000))
        self.root.bind('<Command-Right>', lambda e: mp.reposition(self.next_start()))
        self.root.bind('<Command-Left>', lambda e: mp.reposition(self.previous_start()))
        self.root.bind('<Command-r>', lambda e: mp.reposition(self.from_val))

        self.root.bind('<Command-s>', lambda e: self.set_clip_start())
        self.root.bind('<Command-e>', lambda e: self.set_clip_end())
        self.root.bind('<Command-Shift-s>', lambda e: mp.reposition(self.start_var.get()))
        self.root.bind('<Command-Shift-e>', lambda e: mp.reposition(self.end_var.get()))

        self.root.bind('<Command-l>', lambda e: self.play_clip())
        self.root.bind('<Command-t>', lambda e: self.transcribe())
        self.root.bind('<Command-x>', lambda e: self.export())
        self.root.bind('<Command-u>', lambda e: self.lookup())
        self.root.bind('<Command-k>', lambda e: self.ok())

        # Modal window.
        # Wait for visibility or grab_set doesn't seem to work.
        self.root.wait_visibility()
        self.root.grab_set()
        self.root.transient(parent)

        if self.config.autoplayclips:
            self.play_clip()


    def reposition_popup(self, parent, delta_x, delta_y):
        win_x = parent.winfo_rootx() + delta_x
        win_y = parent.winfo_rooty() + delta_y
        self.root.geometry(f'+{win_x}+{win_y}')


    def set_clip_bounds_markers(self):
        def set_marker(var, fill="red"):
            arrow_poly_coords = (0, 0, 10, 0, 5, 10)
            self.clip_markers.add_marker(var, arrow_poly_coords, fill)

        self.clip_markers.clear()
        s = self.start_var.get()
        e = self.end_var.get()
        set_marker(s)
        if e > s:
            set_marker(e)


    def get_slider_from_to(self, bk, allbookmarks):
        sl_min = sl_max = None
        padding = 5000  # Arbitrary.

        def _last_end_bound_before_bk_position():
            ends_before = [
                b.clip_bounds_ms[1]
                for b in allbookmarks
                if b.clip_bounds_ms and b.clip_bounds_ms[1] < bk.position_ms
            ]
            # print(f'for position {bk.position_ms}, got clip ends before = {ends_before}')
            if len(ends_before) == 0:
                return 0
            # print(f'max is {max(ends_before)}')
            return max(ends_before)

        if bk.clip_bounds_ms:
            sl_min = bk.clip_bounds_ms[0] - padding
            sl_max = bk.clip_bounds_ms[1] + padding
        else:
            # If the clip is not defined yet, assume that the user
            # clicked "bookmark" *after* hearing something interesting
            # and pad a bit more before than after.
            sl_min = bk.position_ms - 5 * padding

            # Don't bother showing the user *much* time before
            # already-defined clip ends that fall before
            # bk.position_ms, because the user has already spent time
            # listening and defining the end point.
            last_end = _last_end_bound_before_bk_position()
            if sl_min < last_end:
                # print(f'min {sl_min} falls before last_end = {last_end}, so changing it')
                sl_min = last_end - (padding / 2)
                # print(f'min {sl_min}, updated')

            sl_max = bk.position_ms + 3 * padding

        # Respect bounds.
        sl_min = int(max(0, sl_min))
        sl_max = int(min(self.song_length_ms, sl_max))

        return (sl_min, sl_max)


    def reposition(self, value_ms_f):
        """Reposition for automation."""
        self.music_player.reposition(value_ms_f)

    def set_clip_start(self):
        self.start_var.set(self.slider_var.get())

    def set_clip_end(self):
        self.end_var.set(self.slider_var.get())

    def get_clip_bounds(self):
        cs = self.start_var.get()
        ce = self.end_var.get()
        if cs >= ce:
            return None
        return (cs, ce)


    def get_clip(self):
        bounds = self.get_clip_bounds()
        if not bounds:
            return None
        return pact.utils.audiosegment_from_mp3_time_range(self.music_file, bounds[0], bounds[1])
        

    def play_clip(self):
        bounds = self.get_clip_bounds()
        if not bounds:
            # print('No clip bounds, not playing.')
            return

        txt = self.transcription_textbox.get(1.0, END)
        if txt is None:  # Safeguard
            txt = ''
        txt = txt.replace("\n", '')
        if txt == '':
            print('transcribing')
            self.transcribe()
        else:
            print('Not transcribing')

        self.music_player.reposition(bounds[0])
        self.music_player.stop_at_ms = bounds[1]
        self.music_player.play()


    def previous_start(self):
        curr_pos = self.slider_var.get()
        c = [p for p in self.candidate_break_times if p < curr_pos]
        if len(c) == 0:
            return curr_pos
        return max(c)

    def next_start(self):
        curr_pos = self.slider_var.get()
        c = [p for p in self.candidate_break_times if p > curr_pos]
        if len(c) == 0:
            return curr_pos
        return min(c)

    def transcribe(self):
        c = self.get_clip()
        if c is None:
            return

        def __set_transcription(transcription):
            t = self.transcription_textbox
            # Weird that it's 1.0 ... ref stackoverflow question 27966626.
            t.delete(1.0, END)
            t.insert(1.0, transcription)

        def __update_progressbar(n):
            self.transcription_progress['value'] = n

        def __search_transcription(sought, transcription_file):
            if transcription_file is None:
                return sought

            fuzzy_text_match_accuracy = 80
            result = pact.textmatch.search_transcription(
                sought, transcription_file, fuzzy_text_match_accuracy)

            if result is None:
                cream = '#FFFDD0'
                self.transcription_textbox.config(bg=cream)
                return sought
            else:
                return '\n\n'.join(result).strip()

        def __try_transcription_search(sought):
            sought = __search_transcription(sought, self.transcription_file)
            __set_transcription(sought)

        self.stop_current_transcription()
        self.transcription_textbox.config(bg='white')
        self.config.transcription_strategy.start(
            audiosegment = c,
            on_update_transcription = lambda s: __set_transcription(s),
            on_update_progress = lambda n: __update_progressbar(n),
            on_finished = lambda s: __try_transcription_search(s)
        )


    def stop_current_transcription(self):
        self.config.transcription_strategy.stop()


    def set_clip_bounds(self):
        try:
            s = self.start_var.get()
            e = self.end_var.get()
            valid_clip = (
                s is not None and
                s != '' and
                e is not None and
                e != '' and
                float(s) < float(e))
            if valid_clip:
                self.bookmark.clip_bounds_ms = [float(s), float(e)]
        except:
            print(f'bad clip bounds? {[self.start_var.get(), self.end_var.get()]}')


    def save_clip(self):
        self.bookmark.position_ms = float(self.entry_var.get())
        self.set_clip_bounds()

        def _get(txtbox):
            txt = txtbox.get(1.0, END)
            if txt is not None and txt != '':
                return txt.strip()
            return None

        self.bookmark.transcription = _get(self.transcription_textbox)
        self.bookmark.notes = _get(self.notes_textbox)



    def lookup(self):
        """Lookup highlighted word, and open popup window."""

        def _get_selection(txt):
            ret = None
            if txt.tag_ranges(SEL):
                ret = txt.get(SEL_FIRST, SEL_LAST)
                if ret.strip() == '':
                    ret = None
                # Deselect anything selected.
                txt.tag_remove(SEL, 1.0, END)
            return ret

        term = _get_selection(self.transcription_textbox)
        if term is None:
            term = _get_selection(self.notes_textbox)

        if term is None:
            print('Nothing selected')
            return

        module_name = self.config['Pact']['LookupModule']
        print(f'doing lookup of "{term}" using {module_name}')
        result = ''
        try:
            result = pact.utils.lookup(term, module_name)
        except Exception as err:
            result = f'Error during lookup: {err}'

        d = LookupWindow(
            parent = self.root,
            term = term,
            content = result
        )
        self.root.wait_window(d.root)
        d.root.grab_release()


    def export(self):
        """Export the current clip and transcription to Anki using Ankiconnect."""

        self.save_clip()
        c = self.get_clip()
        if c is None:
            print('no clip')
            return

        tag = pact.utils.anki_tag_from_filename(self.music_file)
        try:
            r = pact.utils.anki_card_export(
                audiosegment = c,
                ankiconfig = self.config['Anki'],
                transcription = self.bookmark.transcription,
                notes = self.bookmark.notes,
                tag = tag
            )
            self.bookmark.exported = True
            self.ok()
        except Exception as e:
            messagebox.showerror(title='Anki export failed', message=e)


    def play_pause(self):
        self.music_player.play_pause()


    def update_play_button_text(self, music_player_state):
        txt = 'Play'
        if music_player_state is pact.music.PlayerState.PLAYING:
            txt = 'Pause'
        self.play_btn.configure(text = txt)


    def ok(self):
        self.music_player.stop()
        self.stop_current_transcription()
        self.save_clip()
        if self.fig:
            plt.close(self.fig)
        self.root.grab_release()
        self.root.destroy()

        # Callback.
        self.on_close()


    def get_signal_plot_data(self, from_val, to_val):
        sound = pact.utils.audiosegment_from_mp3_time_range(self.music_file, from_val, to_val)
        sound = sound.set_channels(1)

        # Hack for plotting: export to a .wav file.  I can't
        # immediately figure out how to directly plot an mp3 (should
        # be possible, as I have all the data), but there are several
        # examples about plotting .wav files,
        # e.g. https://www.geeksforgeeks.org/plotting-various-sounds-on-graphs-using-python-and-matplotlib/
        signal = None
        f_rate = 0
        with NamedTemporaryFile("w+b", suffix=".wav") as f:
            exported = sound.export(f.name, format='wav')
            exported.close()
            with wave.open(f.name, "r") as raw:
                f_rate = raw.getframerate()
                signal = raw.readframes(-1)
                signal = np.frombuffer(signal, dtype = 'int16')
                raw.close()

        time = np.linspace(
            from_val, # start
            to_val,
            num = len(signal)
        )
        return (time, signal)


    def plot(self, frame, width_inches):
        """Draws plot, returns widget for subsequent placement."""
        fig, plot1 = plt.subplots()
        fig.set_size_inches(width_inches, 0.4)

        # ref https://stackoverflow.com/questions/2176424/
        #   hiding-axis-text-in-matplotlib-plots
        for x in ['left', 'right', 'top', 'bottom']:
            plot1.spines[x].set_visible(False)
        plot1.set_xticklabels([])
        plot1.set_xticks([])
        plot1.set_yticklabels([])
        plot1.set_yticks([])
        plot1.axes.get_xaxis().set_visible(False)
        plot1.axes.get_yaxis().set_visible(False)

        time, signal = self.signal_plot_data

        plot1.plot(time, signal)

        for t in self.candidate_break_times:
            plot1.axvline(x=t, color='red')

        canvas = FigureCanvasTkAgg(fig, master = frame)

        return (canvas.get_tk_widget(), fig)


class LookupWindow(object):
    """Small popup to show lookup results."""

    def __init__(self, parent, term, content):
        self.parent = parent

        self.root=Toplevel(parent)
        self.root.title(term)
        self.root.protocol('WM_DELETE_WINDOW', self.ok)
        self.root.geometry('500x400')
        self.reposition_popup(parent, 50, 50)

        master_frame = Frame(self.root)
        master_frame.grid(row=0, column=0, padx=20, pady=20)

        txtframe = Frame(master_frame, borderwidth=1, relief='groove')
        txtframe.grid(row = 1, column = 0)
        deffont = font.nametofont("TkDefaultFont")
        self.lookup_textbox = scrolledtext.ScrolledText(
            txtframe,
            height = 20, width = 40, wrap=WORD, borderwidth=1,
            font = deffont) # relief='solid'
        self.lookup_textbox.grid(row=0, column = 0)
        self.lookup_textbox.insert(1.0, content)

        b = Button(master_frame, text = 'OK', width = 10, command = self.ok)
        b.grid(row=2, column = 0, pady = 5)

        self.root.bind('<Command-k>', lambda e: self.ok())

        # Modal window.
        # Wait for visibility or grab_set doesn't seem to work.
        self.root.wait_visibility()
        self.root.grab_set()
        self.root.transient(parent)


    def reposition_popup(self, parent, delta_x, delta_y):
        win_x = parent.winfo_rootx() + delta_x
        win_y = parent.winfo_rooty() + delta_y
        self.root.geometry(f'+{win_x}+{win_y}')


    def ok(self):
        self.root.grab_release()
        self.root.destroy()
