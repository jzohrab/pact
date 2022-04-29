from pygame import mixer
from enum import Enum

from utils import TimeUtils


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
