from pygame import mixer
from enum import Enum

from pact.utils import TimeUtils


class PlayerState(Enum):
    NEW = 0
    LOADED = 1
    PLAYING = 2
    PAUSED = 3


class MusicPlayer:
    """Actually plays music, with slider."""

    class PygameMixerPlayer:
        """Play music with pygame mixer."""
        def __init__(self):
            pass

        def load(self, f):
            mixer.music.load(f)

        def play(self, start_ms = 0):
            mixer.music.play(loops = 0, start = (start_ms / 1000.0))

        def pause(self):
            mixer.music.pause()

        def unpause(self):
            mixer.music.unpause()

        def stop(self):
            mixer.music.stop()

        def get_pos(self):
            return mixer.music.get_pos()


    def __init__(self, slider, state_change_callback = None):
        self.slider = slider
        self.state_change_callback = state_change_callback

        self.player = MusicPlayer.PygameMixerPlayer()

        self.state = PlayerState.NEW
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
        self.player.play(v)
        if self.state is not PlayerState.PLAYING:
            self.player.pause()
        self.update_slider()

    def cancel_slider_updates(self):
        if self.slider_update_id:
            self.slider.after_cancel(self.slider_update_id)

    def update_slider(self):
        current_pos_ms = self.player.get_pos()
        slider_pos = self.start_pos_ms + current_pos_ms
        if (current_pos_ms == -1 or slider_pos > self.song_length_ms):
            # Mixer.music goes to -1 when it reaches the end of the file.
            slider_pos = self.song_length_ms

        self.slider.set(slider_pos)

        if self.state is PlayerState.PLAYING:
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
        self.player.load(f)
        self.start_pos_ms = 0.0
        self.state = PlayerState.LOADED

    def play_pause(self):
        self.cancel_slider_updates()
        if self.music_file is None:
            return

        if self.state is PlayerState.LOADED:
            # First play, load and start.
            self.player.play(self.start_pos_ms)
            self.state = PlayerState.PLAYING
            # self.start_pos_ms = 0
            self.update_slider()

        elif self.state is PlayerState.PLAYING:
            self._pause()

        elif self.state is PlayerState.PAUSED:
            self.player.unpause()
            self.state = PlayerState.PLAYING
            self.update_slider()

        else:
            # Should never get here, but in case I missed something ...
            raise RuntimeError(f'??? weird state {self.state}?')

    def _pause(self):
        self.player.pause()
        self.cancel_slider_updates()
        self.state = PlayerState.PAUSED

    def stop(self):
        self.state = PlayerState.LOADED
        self.player.stop()
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
