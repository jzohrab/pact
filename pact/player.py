#####
# Clip player
###

import numpy as np
import tkinter.ttk as ttk
import wave
import os

from datetime import datetime
import shutil
from enum import Enum
from matplotlib import pyplot
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from mutagen.mp3 import MP3
from pydub import AudioSegment, playback
from pygame import mixer
import requests
from tempfile import NamedTemporaryFile
from tkinter import *
from tkinter import filedialog
from tkinter import messagebox

import voskutils
import json
import configparser

class TimeUtils:

    @staticmethod
    def time_string(ms):
        total_seconds = ms / 1000.0
        mins = int(total_seconds) // 60
        secs = total_seconds % 60
        return '{:02d}:{:04.1f}'.format(mins, secs)

    @staticmethod
    def interval_string(s, e, ifInvalid = 'n/a'):
        if (s >= e):
            return ifInvalid
        ss = TimeUtils.time_string(s)
        es = TimeUtils.time_string(e)
        return f'{ss} - {es}'


class MusicPlayer:
    """Actually plays music, with slider."""

    class State(Enum):
        NEW = 0
        LOADED = 1
        PLAYING = 2
        PAUSED = 3

    def __init__(self, slider, state_change_callback = None):
        self.slider = slider
        self.state_change_callback = state_change_callback

        self.state = MusicPlayer.State.NEW
        self.music_file = None
        self.song_length_ms = 0

        # start_pos_ms is set when the slider is manually
        # repositioned.
        self.start_pos_ms = 0

        self.slider_update_id = None

        self.slider.bind('<Button-1>', self.slider_click)
        self.slider.bind('<ButtonRelease-1>', self.slider_unclick)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, s):
        self._state = s
        if self.state_change_callback:
            self.state_change_callback(s)

    def increment(self, i):
        self.reposition(float(self.slider.get()) + i)

    def slider_click(self, event):
        """User is dragging the slider now, so don't update it."""
        # print('got a slider click')
        self.cancel_slider_updates()

    def slider_unclick(self, event):
        # print('got a slider UNclick')
        value_ms_f = float(self.slider.get())
        self.reposition(value_ms_f)

    def reposition(self, value_ms_f):
        v = value_ms_f
        if (v < 0):
            v = 0
        elif (v > self.song_length_ms):
            v = self.song_length_ms

        self.start_pos_ms = v

        mixer.music.play(loops = 0, start = (v / 1000.0))
        if self.state is not MusicPlayer.State.PLAYING:
            mixer.music.pause()
        self.update_slider()

    def cancel_slider_updates(self):
        if self.slider_update_id:
            self.slider.after_cancel(self.slider_update_id)

    def update_slider(self):
        current_pos_ms = mixer.music.get_pos()
        slider_pos = self.start_pos_ms + current_pos_ms
        if (current_pos_ms == -1 or slider_pos > self.song_length_ms):
            # Mixer.music goes to -1 when it reaches the end of the file.
            slider_pos = self.song_length_ms

        self.slider.set(slider_pos)

        if self.state is MusicPlayer.State.PLAYING:
            if slider_pos < self.slider.cget('to'):
                old_update_id = self.slider_update_id
                self.slider_update_id = self.slider.after(50, self.update_slider)
            else:
                # Reached the end of the slider, stop updating.
                self._pause()

    def load_song(self, f, sl):
        self.stop()
        self.music_file = f
        self.song_length_ms = sl
        mixer.music.load(f)
        self.start_pos_ms = 0.0
        self.state = MusicPlayer.State.LOADED

    def play_pause(self):
        self.cancel_slider_updates()
        if self.music_file is None:
            return

        if self.state is MusicPlayer.State.LOADED:
            # First play, load and start.
            mixer.music.play(loops = 0, start = (self.start_pos_ms / 1000.0))
            self.state = MusicPlayer.State.PLAYING
            # self.start_pos_ms = 0
            self.update_slider()

        elif self.state is MusicPlayer.State.PLAYING:
            self._pause()

        elif self.state is MusicPlayer.State.PAUSED:
            mixer.music.unpause()
            self.state = MusicPlayer.State.PLAYING
            self.update_slider()

        else:
            # Should never get here, but in case I missed something ...
            raise RuntimeError(f'??? weird state {self.state}?')

    def _pause(self):
        mixer.music.pause()
        self.cancel_slider_updates()
        self.state = MusicPlayer.State.PAUSED

    def stop(self):
        self.state = MusicPlayer.State.LOADED
        mixer.music.stop()
        self.cancel_slider_updates()


class BookmarkWindow(object):
    """The Bookmark/Clip editor window.

    Future improvements
    ===================

    Styling
    -------

    I tried using ttk.scale for better styling, but it was garbage.
    The slider handle kept jumping out of the scale, and not
    respecting the from_ and to values of the scale (e.g., for
    from_=2500 and to=4500, a value of 3500 (right in the middle)
    would be shown about 75% along the scale, and for higher values it
    would disappear completely).

    ref https://stackoverflow.com/questions/71994893/
    tkinter-ttk-scale-seems-broken-if-from-is-not-zero-mac-python-3-8-2-tcl-tk

    UI for clip selection
    ---------------------

    The current design is good enough -- I can define clips reasonably
    quickly and easily.

    I had tried to use a separate slider to define the "start and end"
    of the clip, but it was a hassle.  The matplotlib chart of the
    waveform didn't line up accurately with the slider position, and
    it just felt inaccurate.  Using buttons and going by feel was
    better.

    Ideally, the design/UI for this would be something like Audacity's
    "clip selection", where the user clicks and drags a range on a
    plotted chart of the audio waveform.  I tried various versions of
    this, but couldn't get it to work reasonably:

    Attempt 1: using axvspans on the chart.

    In the plot() method, you can convert the bookmark clip bounds to
    the corresponding axis positions on the chart, and then use
    axvspans:

        # To shade a time span, we have to translate the time into the
        # corresponding index in the signal array.
        def signal_array_index(t_ms):
            span = self.to_val - self.from_val
            pct = (t_ms - self.from_val) / span
            return len(self.signal_plot_data) * pct

        cs, ce = self.bookmark.clip_bounds_ms
        if (cs is not None and ce is not None):
            shade_start = signal_array_index(cs)
            shade_end = signal_array_index(ce)
            self.axv = plot1.axvspan(shade_start, shade_end, alpha=0.25, color='blue')

    I was hoping to use this to do on-the-fly updates of the chart as
    the user dragged a slider bar, but the performance was terrible.

    Attempt 2: using matplotlib.widgets.SpanSelector

    Per https://stackoverflow.com/questions/40325321/
    python-embed-a-matplotlib-plot-with-slider-in-tkinter-properly, it
    appears that we can use the spanselector in tkinter, but when I
    tried using the bare minimum code in this app's windows, it didn't
    work ... the spanslider couldn't be selected.  Perhaps this is due
    to grid being used, rather than pack ... not sure, didn't bother
    looking further.

    """

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
        self.slider = Scale(
            slider_frame, orient = HORIZONTAL,
            length = length_eyeballed, sliderlength = 10,
            from_ = self.from_val, to = self.to_val, showvalue = 0,
            variable = self.slider_var)
        self.slider.grid(row=1, column=0, pady=5)

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
        self.start_var.trace('w', lambda a,b,c: update_clip_interval_lbl())
        self.end_var.trace('w', lambda a,b,c: update_clip_interval_lbl())
        update_clip_interval_lbl()

        self.transcription_textbox = Text(
            clip_details_frame,
            height = 5, width = 60, wrap=WORD, borderwidth=1) # relief='solid'
        if (self.bookmark.transcription):
            self.transcription_textbox.insert(1.0, self.bookmark.transcription)

        clip_interval_lbl.grid(row=0, column=1, pady=2, sticky = W)
        self.transcription_textbox.grid(row=1, column = 1)

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


        self.music_player = MusicPlayer(self.slider, self.update_play_button_text)
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
        playback.play(c)


    def transcribe(self):
        c = self.get_clip()
        if c is None:
            return
        cb = voskutils.TextCallback(self.parent, self.transcription_textbox)
        voskutils.transcribe_audiosegment(c, cb)


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
        self.bookmark.transcription = self.transcription_textbox.get(1.0, END)
        self.set_clip_bounds()

    def export(self):
        """Export the current clip and transcription to Anki using Ankiconnect."""

        self.save_clip()

        print('export')
        c = self.get_clip()
        if c is None:
            print('no clip')
            return

        config = configparser.ConfigParser()
        config.read('config.ini')
        # print(config)
        config.write(sys.stdout)

        destdir = config['Anki']['MediaFolder']

        now = datetime.now() # current date and time
        date_time = now.strftime("%Y%m%d_%H%M%S")
        filename = f'clip_{date_time}_{id(c)}.mp3'
        destname = os.path.join(destdir, filename)

        with NamedTemporaryFile(suffix='.mp3') as temp:
            c.export(temp.name, format="mp3")
            shutil.copyfile(temp.name, destname)
            # print('Generated temp clip:')
            # print(temp.name)
            # print('Copied clip to:')
            # print(destname)

        a = config['AnkiCard']

        fields = {
            a['AudioField']: f'[sound:{filename}]'
        }

        t = self.bookmark.transcription
        if t is not None and t != '':
            fields[ a['TranscriptionField'] ] = t

        postjson = {
            "action": "addNote",
            "version": 6,
            "params": {
                "note": {
                    "deckName": a['Deck'],
                    "modelName": a['NoteType'],
                    "fields": fields
                }
            }
        }

        print(postjson)
        print('posting')
        url = config['Anki']['Ankiconnect']
        r = requests.post(url, json = postjson)
        print('posted')
        print(r.json())
        e = r.json()['error']
        if e is not None:
            msg = f'Message from Anki/Ankiconnect: {e}'
            messagebox.showerror(title='Anki export failed', message=msg)

    def play_pause(self):
        self.music_player.play_pause()

    def update_play_button_text(self, music_player_state):
        txt = 'Play'
        if music_player_state is MusicPlayer.State.PLAYING:
            txt = 'Pause'
        self.play_btn.configure(text = txt)

    def ok(self):
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

        # https://stackoverflow.com/questions/40325321/
        #  python-embed-a-matplotlib-plot-with-slider-in-tkinter-properly
        canvas = FigureCanvasTkAgg(fig, master = frame)

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
        # Note we can also do lot1.plot(time, signal), but that
        # doesn't work well with axvspans, as far as I can tell.
        
        # To shade a time span, we have to translate the time into the
        # corresponding index in the signal array.
        def signal_array_index(t_ms):
            span = self.to_val - self.from_val
            pct = (t_ms - self.from_val) / span
            return len(self.signal_plot_data) * pct

        ## Deactivating shading code for now.
        ### cs, ce = self.bookmark.clip_bounds_ms
        ### if (cs is not None and ce is not None):
        ###     shade_start = signal_array_index(cs)
        ###     shade_end = signal_array_index(ce)
        ###     self.axv = plot1.axvspan(shade_start, shade_end, alpha=0.25, color='blue')

        return canvas.get_tk_widget()

        # canvas.draw()


    ### Dead code, previously in __init__. Attempt to define clips
    ### using a slider.  Keeping this in case it's useful in the
    ### future.
    #
    ### self.clip_slider = Scale(
    ###     slider_frame,
    ###     from_=self.from_val,
    ###     to=self.to_val,
    ###     orient=HORIZONTAL,
    ###     length= sllen)
    ### self.clip_slider.grid(row=4, column=0, pady=10)
    ### self.clip_slider.bind('<Button-1>', self.clip_slider_click)
    ### self.clip_slider.bind('<ButtonRelease-1>', self.clip_slider_unclick)
    ### self.clip_down_ms = None
    ### self.clip_up_ms = None
    ### self.clip_after_id = None
    ### self.clip_bounds_ms = (None, None)

    ### Dead code. Attempt to define clips using a slider.
    ### Keeping this in case it's useful in the future.
    ### def clip_slider_click(self, event):
    ###     self.clip_down_ms = self.clip_slider.get()
    ###     self.clip_up_ms = None
    ###     self.cancel_clip_slider_updates()
    ###     self.clip_slider_update()

    ### def clip_slider_unclick(self, event):
    ###     self.clip_up_ms = self.clip_slider.get()
    ###     self.cancel_clip_slider_updates()
    ###     self.save_clip()
    ###     self.plot()

    ### def cancel_clip_slider_updates(self):
    ###     print(f'cancelling updates, current = {self.clip_after_id}')
    ###     if self.clip_after_id is not None:
    ###         self.clip_slider.after_cancel(self.clip_after_id)
    ###     self.clip_after_id = None

    ### def clip_slider_update(self):
    ###     print(f'  UPDATE, clip = {(self.clip_down_ms, self.clip_up_ms)}')
    ###     self.clip_up_ms = self.clip_slider.get()
    ###     self.save_clip()
    ###     self.clip_after_id = self.clip_slider.after(500, self.clip_slider_update)

    ### def save_clip(self):
    ###     if (self.clip_down_ms is None or
    ###         self.clip_up_ms is None or
    ###         self.clip_up_ms < self.clip_down_ms):
    ###         return
    ###     self.clip_bounds_ms = (self.clip_down_ms, self.clip_up_ms)
    ###     print(f'clip bounds: {self.clip_bounds_ms}')
    ###     self.bookmark.clip_bounds_ms = self.clip_bounds_ms


class MainWindow:

    class Bookmark:
        """A bookmark or clip item, stored in bookmarks listbox"""
        def __init__(self, pos_ms):
            self._pos_ms = pos_ms
            self._clip_start_ms = None
            self._clip_end_ms = None
            self.transcription = None

        def clipdisplay(self):
            s, e = (self._clip_start_ms, self._clip_end_ms)
            if s is None or e is None:
                return None
            s = TimeUtils.time_string(s)
            e = TimeUtils.time_string(e)
            ret = f"{s} - {e}"

            t = self.transcription
            if t is not None and t != '':
                clipped = t[:50]
                if clipped != t:
                    clipped += ' ...'
                ret = f"{ret}  \"{clipped}\""
            return ret

        def display(self):
            """String description of this for display in list boxes."""
            cd = self.clipdisplay()
            if cd is not None:
                return cd
            return f"Bookmark {TimeUtils.time_string(self._pos_ms)}"

        @property
        def position_ms(self):
            """Bookmark position."""
            return self._pos_ms

        @position_ms.setter
        def position_ms(self, v):
            self._pos_ms = v

        @property
        def clip_bounds_ms(self):
            if self._clip_start_ms is None:
                return None
            return (self._clip_start_ms, self._clip_end_ms)

        @clip_bounds_ms.setter
        def clip_bounds_ms(self, v):
            self._clip_start_ms, self._clip_end_ms = v


    class FullTrackBookmark(Bookmark):
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

        # start_pos_ms is set when the slider is manually
        # repositioned.
        self.start_pos_ms = 0

        self.slider_update_id = None

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

        _make_button('Load', 1, self.load)
        self.play_btn = _make_button('Play', 2, self.play_pause)
        _make_button('Bookmark', 3, self.add_bookmark)
        _make_button('Delete', 4, self.delete_selected_bookmark)
        _make_button('Clip', 5, self.popup_clip_window)

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

        self.music_player = MusicPlayer(self.slider, self.update_play_button_text)

        # Previously, I had 'space' handle start/stop, but that
        # also triggers a re-selection of the currently selected
        # bookmark.
        window.bind('<Command-p>', lambda e: self.play_pause())
        window.bind('<Right>', lambda e: self.music_player.increment(100))
        window.bind('<Left>', lambda e: self.music_player.increment(-100))
        window.bind('<m>', lambda e: self.add_bookmark(float(self.slider.get())))
        window.bind('<u>', lambda e: self.update_selected_bookmark(float(self.slider.get())))
        window.bind('<d>', lambda e: self.delete_selected_bookmark())
        window.bind('<Return>', lambda e: self.popup_clip_window())

        # self.hack_dev()

    def hack_dev(self):
        """During dev."""
        print("Hack load song and bookmark")
        self._load_song_details('/Users/jeff/Documents/Projects/pytubedl/sample/ten_seconds.mp3')
        self.add_bookmark(3200)
        self.bookmarks_lst.activate(1)
        self.bookmarks_lst.select_set(1)
        self.popup_clip_window()

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
        b = MainWindow.Bookmark(v)
        self.bookmarks.append(b)
        self.bookmarks_lst.insert(END, b.display())

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
        if music_player_state is MusicPlayer.State.PLAYING:
            txt = 'Pause'
        self.play_btn.configure(text = txt)

    def quit(self):
        self.music_player.stop()
        self.window.destroy()


root = Tk()
mixer.init()
app = MainWindow(root)
root.mainloop()
