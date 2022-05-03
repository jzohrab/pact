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
from pydub import AudioSegment, playback
from tempfile import NamedTemporaryFile
from tkinter import *
from tkinter import filedialog
from tkinter import messagebox

import pact.voskutils
import pact.music
from pact.utils import TimeUtils, anki_card_export, StoppableThread


class SliderMarkersWidget:

    @staticmethod
    def coordinates_for_value(val, minval, maxval, length, coords):

        def chunks(l, n):
            n = max(1, n)
            return (l[i:i+n] for i in range(0, len(l), n))
        coordpairs = list(chunks(coords, 2))
        xcoords = [el[0] for el in coordpairs]

        width = max(xcoords) - min(xcoords)
        middle = width / 2.0
        shiftleft = min(xcoords) + middle


        # shift everything so that the middle is at zero
        middleatzero = [(c[0] - shiftleft, c[1]) for c in coordpairs]

        # Where there middle is actually supposed to go.
        placement = int(length * (val - minval) / (maxval - minval))

        # Shift the middle so that it's at placement
        final = [(c[0] + placement, c[1]) for c in middleatzero]

        # print(xcoords)
        # print(f'shifting by shiftleft = {shiftleft}')
        # print(f'shifted = {middleatzero}')
        # print(f'final = {final}')

        # This python flattening is mental.
        flattened = [item for sublist in final for item in sublist]
        return tuple(flattened)

    def __init__(self, canvas, width, minvalue, maxvalue):
        self.canvas = canvas
        self.width = width
        self.polygons = []
        self.minvalue = minvalue
        self.maxvalue = maxvalue

    def add_marker(self, value, polygon_coords, fill = "red"):
        adjusted_coords = SliderMarkersWidget.coordinates_for_value(
            value, self.minvalue, self.maxvalue, self.width, polygon_coords)
        p = self.canvas.create_polygon(adjusted_coords, fill=fill)
        self.polygons.append(p)

    def clear(self):
        for p in self.polygons:
            self.canvas.delete(p)
        self.polygons = []


class MainWindow:

    class FullTrackBookmark(pact.music.Bookmark):
        def __init__(self):
            super().__init__(0)
        def display(self):
            return "<Full Track>"


    def __init__(self, window):
        window.title('MP3 Player')
        window.geometry('600x400')
        self.window = window
        self.music_file = None
        self.song_length_ms = 0

        menubar = Menu(self.window)
        self.window['menu'] = menubar
        menu_file = Menu(menubar)
        menubar.add_cascade(menu=menu_file, label='File')
        menu_file.add_command(label='Open mp3', command=self.load)
        menu_file.add_separator()
        menu_file.add_command(label='Save current session', command=self.save_app_state)
        menu_file.add_command(label='Reload session', command=self.load_app_state)
        menu_file.add_separator()
        menu_file.add_command(label='Close', command=self.quit)

        # Layout
        master_frame = Frame(window)
        master_frame.grid(row=0, column=0, padx=50, pady=50)

        bk_frame = Frame(master_frame)
        bk_frame.grid(row=2, column=0, pady=10)

        # The bookmarks saved during play.
        self.bookmarks = []
        self.bookmarks_lst = Listbox(
            bk_frame,
            width=50,
            selectbackground="yellow",
            selectforeground="black")
        self.bookmarks_lst.grid(row=0, column=1)
        self.bookmarks_lst.bind('<<ListboxSelect>>', self.on_bookmark_select)

        scrollbar = ttk.Scrollbar(bk_frame, orient= 'vertical')
        scrollbar.grid(row=0, column=2, sticky='NS')
        self.bookmarks_lst.config(yscrollcommand= scrollbar.set)
        scrollbar.config(command= self.bookmarks_lst.yview)

        ctl_frame = Frame(master_frame)
        ctl_frame.grid(row=1, column=0, pady=10)

        def _make_button(text, column, command):
            b = Button(ctl_frame, text=text, width=8, command=command)
            b.grid(row=0, column=column, padx=5)
            return b

        self.play_btn = _make_button('Play', 1, self.play_pause)
        _make_button('Bookmark', 2, self.add_bookmark)
        _make_button('Delete', 3, self.delete_selected_bookmark)
        _make_button('Clip', 4, self.popup_clip_window)

        slider_frame = Frame(master_frame)
        slider_frame.grid(row=0, column=0, pady=5)

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
        def update_slider_label(a, b, c):
            self.slider_lbl.configure(text=TimeUtils.time_string(self.slider_var.get()))
        self.slider_var.trace('w', update_slider_label)

        self.music_player = pact.music.MusicPlayer(self.slider, self.update_play_button_text)

        # Previously, I had 'space' handle start/stop, but that
        # also triggers a re-selection of the currently selected
        # bookmark.
        window.bind('<Command-p>', lambda e: self.play_pause())
        window.bind('<Right>', lambda e: self.music_player.increment(100))
        window.bind('<Left>', lambda e: self.music_player.increment(-100))
        window.bind('<Command-Right>', lambda e: self.music_player.increment(1000))
        window.bind('<Command-Left>', lambda e: self.music_player.increment(-1000))
        window.bind('<m>', lambda e: self.add_bookmark(float(self.slider.get())))
        window.bind('<u>', lambda e: self.update_selected_bookmark(float(self.slider.get())))
        window.bind('<d>', lambda e: self.delete_selected_bookmark())
        window.bind('<Return>', lambda e: self.popup_clip_window())

        self.init_dev()


    def init_dev(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        if not config.has_section('Dev'):
            return
        print('Doing dev configuration')
        devsettings = config['Dev']
        f = devsettings['LoadFile']
        self._load_song_details(f)


    def popup_clip_window(self):
        i = self._selected_bookmark_index()
        if not i:
            return
        b = self.bookmarks[i]

        d = BookmarkWindow(self.window, b, self.music_file, self.song_length_ms)
        self.window.wait_window(d.root)
        d.root.grab_release()
        # Re-select, b/c switching to the pop-up deselects the current.
        self.bookmarks_lst.activate(i)
        self.bookmarks_lst.select_set(i)
        self.reload_bookmark_list()
        self.bookmarks_lst.see(i)
        self.move_to_bookmark(b)


    def reload_bookmark_list(self):
        selected_index = self._selected_bookmark_index()
        self.bookmarks_lst.delete(0, END)
        for b in self.bookmarks:
            self.bookmarks_lst.insert(END, b.display())
        if selected_index:
            self.bookmarks_lst.activate(selected_index)
            self.bookmarks_lst.select_set(selected_index)


    def add_bookmark(self, m = None):
        v = m
        if v is None:
            v = float(self.slider.get())
        b = pact.music.Bookmark(v)
        self.bookmarks.append(b)
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


    def on_bookmark_select(self, event):
        index = self._selected_bookmark_index()
        if not index:
            return
        self.move_to_bookmark(self.bookmarks[index])


    def move_to_bookmark(self, b):
        self.music_player.reposition(b.position_ms)


    def load(self):
        f = filedialog.askopenfilename()
        if f:
            self._load_song_details(f)
        else:
            print("no file?")


    def _load_song_details(self, f):
        song_mut = MP3(f)
        self.song_length_ms = song_mut.info.length * 1000  # length is in seconds
        self.slider.config(to = self.song_length_ms, value=0)
        self.slider_lbl.configure(text=TimeUtils.time_string(self.song_length_ms))
        self.music_file = f
        self.music_player.load_song(f, self.song_length_ms)
        self.bookmarks = [ MainWindow.FullTrackBookmark() ]
        self.reload_bookmark_list()


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
            pass

        @staticmethod
        def from_app(mainwindow):
            s = MainWindow.ApplicationState()
            s.music_file = mainwindow.music_file
            s.music_player_pos = mainwindow.music_player.get_pos()
            s.bookmarks = mainwindow.bookmarks
            return s


    def save_app_state(self):
        """Pickle app state for later reload."""
        suggested = os.path.basename(self.music_file)
        fname, ext = os.path.splitext(suggested)
        f = filedialog.asksaveasfilename(initialfile = f'{fname}.clips', filetypes = (("Clips file", "*.clips"),))
        if f is None or f ==  '':
            print("Cancelled")
            return

        appstate = MainWindow.ApplicationState.from_app(self)
        with open(f, "wb") as dest:
            pickle.dump(appstate, dest, protocol=0)


    def load_app_state(self):
        """Load previously pickled state."""
        f = filedialog.askopenfilename(filetypes = (("Clips file", "*.clips"),))
        if f is None or f == '':
            print("Cancelled")
            return

        appstate = None
        with open(f, "rb") as src:
            appstate = pickle.load(src)
        self._load_song_details(appstate.music_file)
        self.music_player.reposition(appstate.music_player_pos)
        self.bookmarks = appstate.bookmarks
        self.reload_bookmark_list()


class BookmarkWindow(object):
    """Bookmark / clip editing window."""

    def __init__(self, parent, bookmark, music_file, song_length_ms):
        self.bookmark = bookmark
        self.music_file = music_file
        self.song_length_ms = song_length_ms

        self.parent = parent
        self.root=Toplevel(parent)
        self.root.protocol('WM_DELETE_WINDOW', self.ok)
        self.root.geometry('550x450')

        self.from_val, self.to_val = self.get_slider_from_to(bookmark)

        # Pre-calc graphing data.  If from_val or to_val change, must recalc.
        self.signal_plot_data = self.get_signal_plot_data(self.from_val, self.to_val)

        # Transcription happens on a thread and can be stopped.
        self.transcription_thread = None
        self.transcription_callback = None

        # Start the clip at the bookmark value for now, good enough.
        clip_bounds = bookmark.clip_bounds_ms
        if not bookmark.clip_bounds_ms:
            clip_bounds = (bookmark.position_ms, bookmark.position_ms)

        # TODO: can likely change these to regular floats, as they're
        # not controlling anything.
        self.entry_var = DoubleVar(value = bookmark.position_ms)
        self.start_var = DoubleVar(value = clip_bounds[0])
        self.end_var = DoubleVar(value = clip_bounds[1])

        self.slider_var = DoubleVar()

        slider_frame = Frame(self.root)
        slider_frame.grid(row=1, column=0, pady=10)

        w = self.plot(slider_frame, 7)
        w.grid(row=0, column=0, pady=10)

        # Had to guess the best slider length, as I couldn't figure
        # out how to calculate it exactly using the matplotlib figure
        # dimensions.
        length_eyeballed = 7 * 55

        # Slider markers indicating clip start/end.
        c = Canvas(slider_frame, width=length_eyeballed, height = 10)
        c.grid(row = 1, column = 0, pady=0)
        self.clip_markers = SliderMarkersWidget(c, length_eyeballed, self.from_val, self.to_val)
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
        ctl_frame.grid(row=2, column=0, pady=10)

        self.play_btn = Button(ctl_frame, text='Play', width = 8, command=self.play_pause)
        self.play_btn.grid(row=0, column=0, padx=2)

        buttons = [
            [ 'Set start', lambda: self.start_var.set(self.slider_var.get()) ],
            [ 'Set end', lambda: self.end_var.set(self.slider_var.get()) ],
            [ 'Play clip', self.play_clip ],
            [ 'Transcribe', self.transcribe ]
        ]
        for index, arr in enumerate(buttons, start=2):
            text, comm = arr
            b = Button(ctl_frame, text = text, width = 8, command = comm)
            b.grid(row=0, column = index, padx=2)

        clip_details_frame = Frame(self.root, borderwidth=1, relief='groove')
        clip_details_frame.grid(row=3, column=0, pady=10)

        clip_interval_lbl = Label(clip_details_frame, text='-')

        def update_clip_interval_lbl():
            s = self.start_var.get()
            e = self.end_var.get()
            text = TimeUtils.interval_string(s, e, 'n/a')
            clip_interval_lbl.configure(text = f'Clip: {text}')
            self.set_clip_bounds_markers()

        self.start_var.trace('w', lambda a,b,c: update_clip_interval_lbl())
        self.end_var.trace('w', lambda a,b,c: update_clip_interval_lbl())
        update_clip_interval_lbl()
        self.set_clip_bounds_markers()

        self.transcription_textbox = Text(
            clip_details_frame,
            height = 5, width = 60, wrap=WORD, borderwidth=1) # relief='solid'
        if (self.bookmark.transcription):
            self.transcription_textbox.insert(1.0, self.bookmark.transcription)
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

        exit_frame = Frame(self.root)
        exit_frame.grid(row=5, column=0, pady=20)
        buttons = [
            [ 'Export', self.export ],
            [ 'OK', self.ok ]
        ]
        for index, arr in enumerate(buttons, start=1):
            text, comm = arr
            b = Button(exit_frame, text = text, width = 10, command = comm)
            b.grid(row=0, column = index, padx=5)


        self.music_player = pact.music.MusicPlayer(self.slider, self.update_play_button_text)
        self.music_player.load_song(music_file, song_length_ms)
        self.music_player.reposition(clip_bounds[0])
        # print(f'VALS: from={from_val}, to={to_val}, val={bookmark.position_ms}')

        # Hotkeys.  Note: I tried to bind the hotkeys in the "for
        # index, arr" loops above (since I'm just repeating the
        # commands already given in the arrays), but when I did so the
        # lambdas did not work ... they just closed the form.  Code in
        # loop was"self.root.bind(f'<{hotkey}>', lambda e: comm())".
        self.root.bind('<Command-p>', lambda e: self.play_pause())
        self.root.bind('<Right>', lambda e: self.music_player.increment(100))
        self.root.bind('<Left>', lambda e: self.music_player.increment(-100))
        self.root.bind('<Command-Right>', lambda e: self.music_player.increment(1000))
        self.root.bind('<Command-Left>', lambda e: self.music_player.increment(-1000))
        self.root.bind('<Command-r>', lambda e: self.music_player.reposition(self.from_val))
        self.root.bind('<Command-s>', lambda e: self.start_var.set(self.slider_var.get()))
        self.root.bind('<Command-e>', lambda e: self.end_var.set(self.slider_var.get()))
        self.root.bind('<Command-c>', lambda e: self.play_clip())
        self.root.bind('<Command-t>', lambda e: self.transcribe())
        self.root.bind('<Command-x>', lambda e: self.export())
        self.root.bind('<Return>', lambda e: self.ok())

        # Modal window.
        # Wait for visibility or grab_set doesn't seem to work.
        self.root.wait_visibility()
        self.root.grab_set()
        self.root.transient(parent)


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


    def get_slider_from_to(self, bk):
        sl_min = sl_max = None
        padding = 5000

        if bk.clip_bounds_ms:
            sl_min = bk.clip_bounds_ms[0] - padding
            sl_max = bk.clip_bounds_ms[1] + padding
        else:
            # If the clip is not defined yet, assume that the user
            # clicked "bookmark" *after* hearing something interesting
            # and pad a bit more before than after.
            sl_min = bk.position_ms - 3 * padding
            sl_max = bk.position_ms + padding

        # Respect bounds.
        sl_min = int(max(0, sl_min))
        sl_max = int(min(self.song_length_ms, sl_max))

        return (sl_min, sl_max)


    def get_clip(self):
        cs = self.start_var.get()
        ce = self.end_var.get()
        if cs >= ce:
            return None

        sound = BookmarkWindow.getFullAudioSegment(self.music_file)
        return sound[cs : ce]
        

    def play_clip(self):
        c = self.get_clip()
        if c is None:
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
        playback.play(c)


    def transcribe(self):
        c = self.get_clip()
        if c is None:
            return

        self.stop_current_transcription()
        def do_transcription():
            cb = pact.voskutils.TextCallback(self.parent, self.transcription_textbox, self.transcription_progress)
            self.transcription_callback = cb
            pact.voskutils.transcribe_audiosegment(c, cb)
        self.transcription_thread = StoppableThread(target=do_transcription)
        self.transcription_thread.start()


    def stop_current_transcription(self):
        if not self.transcription_thread:
            return
        self.transcription_callback.stop()
        self.transcription_thread.stop()


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
                self.bookmark.clip_bounds_ms = (float(s), float(e))
        except:
            print(f'bad clip bounds? {(self.start_var.get(), self.end_var.get())}')


    def save_clip(self):
        self.bookmark.position_ms = float(self.entry_var.get())
        txt = self.transcription_textbox.get(1.0, END)
        if txt is not None and txt != '':
            self.bookmark.transcription = txt
        else:
            self.bookmark.transcription = None
        self.set_clip_bounds()


    def export(self):
        """Export the current clip and transcription to Anki using Ankiconnect."""

        self.save_clip()
        c = self.get_clip()
        if c is None:
            print('no clip')
            return

        r = anki_card_export(c, self.bookmark.transcription)
        e = r.json()['error']
        if e is not None:
            msg = f'Message from Anki/Ankiconnect: {e}'
            messagebox.showerror(title='Anki export failed', message=msg)
        else:
            self.ok()


    def play_pause(self):
        self.music_player.play_pause()


    def update_play_button_text(self, music_player_state):
        txt = 'Play'
        if music_player_state is pact.music.PlayerState.PLAYING:
            txt = 'Pause'
        self.play_btn.configure(text = txt)


    def ok(self):
        self.stop_current_transcription()
        self.save_clip()
        self.root.grab_release()
        self.root.destroy()


    _full_audio_segment = None
    _old_music_file = None


    @classmethod
    def getFullAudioSegment(cls, f):
        # Store the full segment, b/c it takes a while to make.
        if (BookmarkWindow._old_music_file != f or BookmarkWindow._full_audio_segment is None):
            print('loading full segment ...')
            BookmarkWindow._full_audio_segment = AudioSegment.from_mp3(f)
            BookmarkWindow._old_music_file = f
        else:
            print('using cached segment')
        return BookmarkWindow._full_audio_segment
            

    def get_signal_plot_data(self, from_val, to_val):
        sound = BookmarkWindow.getFullAudioSegment(self.music_file)
        sound = sound[from_val : to_val]
        sound = sound.set_channels(1)

        # Hack for plotting: export to a .wav file.  I can't
        # immediately figure out how to directly plot an mp3 (should
        # be possible, as I have all the data), but there are several
        # examples about plotting .wav files,
        # e.g. https://www.geeksforgeeks.org/plotting-various-sounds-on-graphs-using-python-and-matplotlib/
        signal = None
        with NamedTemporaryFile("w+b", suffix=".wav") as f:
            sound.export(f.name, format='wav')
            raw = wave.open(f.name, "r")
            f_rate = raw.getframerate()
            signal = raw.readframes(-1)
            signal = np.frombuffer(signal, dtype = 'int16')

        time = np.linspace(
            0, # start
            len(signal) / f_rate,
            num = len(signal)
        )
        return (time, signal)


    def plot(self, frame, width_inches):
        """Draws plot, returns widget for subsequent placement."""
        fig, plot1 = plt.subplots()
        fig.set_size_inches(width_inches, 1)

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
        plot1.plot(signal)
        
        canvas = FigureCanvasTkAgg(fig, master = frame)
        return canvas.get_tk_widget()
