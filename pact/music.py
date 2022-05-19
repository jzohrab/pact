import vlc
from enum import Enum
from pact.utils import TimeUtils
import re


class PlayerState(Enum):
    NEW = 0
    LOADED = 1
    PLAYING = 2
    PAUSED = 3
    STOPPED = 4


class VlcPlayer:
    """Simple wrapper/adaptor around VLC player so it can be used by the
    MusicPlayer class below.  ref
    https://github.com/oaubert/python-vlc/blob/master/examples/tkvlc.py
    """

    def __init__(self):
        args = []
        self.instance = vlc.Instance(args)
        self.player = self.instance.media_player_new()
        self.play_pos_ms = 0
        self.is_stopped = True


    def load(self, f):
        m = self.instance.media_new(str(f))  # Path, unicode
        self.player.set_media(m)


    def set_position(self, ms):
        # print(f'called reposition, self.play_pos_ms = {ms}')
        self.play_pos_ms = ms


    def play(self):
        # print('called play')
        # print(f'playing at start = {self.play_pos_ms}')
        self.player.play()
        self.player.set_time(int(self.play_pos_ms))
        self.is_stopped = False


    def pause(self):
        # print('called pause')
        if not self.player.is_playing():
            # print('already paused')
            return
        # print(f'pausing')
        self.player.pause() # toggles


    def unpause(self):
        # print('called unpause')
        if self.player.is_playing():
            # print('already playing')
            return
        # print(f'UN pausing')
        self.player.pause() # toggles


    def stop(self):
        # print('called stop')
        # print(f'stopping')
        self.player.stop()
        self.is_stopped = True


    def get_pos(self):
        # print('called get_pos')
        t = self.play_pos_ms
        # print(f'  have t at play_pos_ms = {t}')
        if not self.is_stopped:
            # print('  not stopped')
            t = self.player.get_time()
            if t == 0:
                # Hack: the self.player.get_time() seems to lag a
                # bit, and returns 0 for a few cycles after the
                # player has started playing from a given
                # play_pos_ms.  So, return the play position, just
                # in case.
                # print(f'  fall back to {self.play_pos_ms}')
                t = self.play_pos_ms
        # print(f'  final get pos = {t}')
        return t


class MusicPlayer:
    """Actually plays music, with slider."""

    def __init__(self, slider, state_change_callback = None):
        self.slider = slider
        self.slider_max = self.slider.cget('to')
        self.state_change_callback = state_change_callback

        self.player = VlcPlayer()

        self.state = PlayerState.NEW
        self.music_file = None
        self.song_length_ms = 0

        # Allow "early stop".  If set, only play to this position.
        self.stop_at_ms = None

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

        # No longer stopping at specified place.
        self.stop_at_ms = None

        curr_state = self.state
        self.player.stop()
        self.state = PlayerState.STOPPED
        self.player.set_position(v)
        if curr_state is PlayerState.PLAYING:
            self.player.play()
        self.update_slider()

    def cancel_slider_updates(self):
        if self.slider_update_id:
            self.slider.after_cancel(self.slider_update_id)

    def get_pos(self):
        """For serialization."""
        return self.player.get_pos()

    def update_slider(self):
        slider_pos = self.player.get_pos()
        if (slider_pos > self.song_length_ms):
            slider_pos = self.song_length_ms

        self.slider.set(slider_pos)

        if self.state is PlayerState.PLAYING:
            end_pos = self.slider_max
            if self.stop_at_ms is not None:
                end_pos = self.stop_at_ms
            if slider_pos >= end_pos:
                self.stop_at_ms = None
                self.pause()
            else:
                self.slider_update_id = self.slider.after(50, self.update_slider)

    def load_song(self, f, sl):
        self.stop()
        self.music_file = f
        self.song_length_ms = sl
        self.player.load(f)
        self.slider_max = sl
        self.state = PlayerState.LOADED

    def play(self):
        self.cancel_slider_updates()
        if self.music_file is None:
            return
        self.player.play()
        self.state = PlayerState.PLAYING
        self.update_slider()

    def play_pause(self):
        self.cancel_slider_updates()
        if self.music_file is None:
            return

        if self.state is PlayerState.LOADED or self.state is PlayerState.STOPPED:
            self.play()

        elif self.state is PlayerState.PLAYING:
            self.pause()

        elif self.state is PlayerState.PAUSED:
            self.player.unpause()
            self.state = PlayerState.PLAYING
            self.update_slider()

        else:
            # Should never get here, but in case I missed something ...
            raise RuntimeError(f'??? weird state {self.state}?')

    def pause(self):
        if self.state is not PlayerState.PLAYING:
            return
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
        self.position_ms = pos_ms
        self.clip_bounds_ms = None
        self.transcription = None
        self.notes = None
        self.exported = False

    @property
    def effective_pos_ms(self):
        """Use the effective_pos_ms to position the slider."""
        cb = self.clip_bounds_ms
        if cb and cb[1]:
            return cb[0]
        return self.position_ms


    def to_dict(self):
        """For serialization"""
        return self.__dict__

    @staticmethod
    def from_dict(d):
        """For deserialization."""
        # print(f'dict: {d}')
        p = d['position_ms']
        b = Bookmark(p)
        b.clip_bounds_ms = d['clip_bounds_ms']
        b.transcription = d['transcription']
        b.exported = d.get('exported', False)
        b.notes = d.get('notes', None)
        return b

    def __transcription_display(self, clip_at):
        t = self.transcription
        if t is None or t.strip() == '':
            return None

        # Only use the first line, b/c that's all that can be
        # displayed anyway.
        t = t.split('\n')[0]

        t = re.sub("\[.*?\]", '', t).strip()

        ret = t[:clip_at]
        if ret != t:
            ret += ' ...'
        return ret

    def __line_display(self, clip_at):
        b = self.clip_bounds_ms
        if b is None:
            return None
        s, e = b
        if s is None or e is None:
            return None
        s = TimeUtils.time_string(s)
        e = TimeUtils.time_string(e)
        ret = f"{s} - {e}"

        t = self.__transcription_display(clip_at)
        if t:
            ret = f"{s}  \"{t}\""

        if self.exported:
            checkmark = '\u2713'
            ret = f"{checkmark} {ret}"

        return ret

    def display(self, clip_at = 50):
        """String description of this for display in list boxes."""
        cd = self.__line_display(clip_at)
        if cd is not None:
            return cd
        return f"Bookmark {TimeUtils.time_string(self.position_ms)}"
