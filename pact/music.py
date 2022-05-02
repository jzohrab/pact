from pygame import mixer
import vlc
from enum import Enum

from pact.utils import TimeUtils


class PlayerState(Enum):
    NEW = 0
    LOADED = 1
    PLAYING = 2
    PAUSED = 3
    STOPPED = 4


class MusicPlayer:
    """Actually plays music, with slider."""

    class PygameMixerPlayer:
        """Play music with pygame mixer."""
        def __init__(self):
            self.play_pos_ms = 0
            self.is_stopped = True

        def load(self, f):
            mixer.music.load(f)

        def set_position(self, ms):
            self.play_pos_ms = ms

        def play(self):
            play_s = self.play_pos_ms / 1000.0
            mixer.music.play(loops = 0, start = play_s)
            self.is_stopped = False

        def pause(self):
            mixer.music.pause()

        def unpause(self):
            mixer.music.unpause()

        def stop(self):            
            mixer.music.stop()
            self.is_stopped = True

        def get_pos(self):
            """Pygame mp3 player position is the sum of where it started
            playing plus its current pos. ref
            https://www.pygame.org/docs/ref/music.html
            """
            if self.is_stopped:
                return self.play_pos_ms
            else:
                return self.play_pos_ms + mixer.music.get_pos()


    class VlcPlayer:
        """Play music with vlc."""
        # ref https://github.com/oaubert/python-vlc/blob/master/examples/tkvlc.py

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


    def __init__(self, slider, state_change_callback = None):
        self.slider = slider
        self.state_change_callback = state_change_callback

        # self.player = MusicPlayer.PygameMixerPlayer()
        self.player = MusicPlayer.VlcPlayer()

        self.state = PlayerState.NEW
        self.music_file = None
        self.song_length_ms = 0

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

    def update_slider(self):
        slider_pos = self.player.get_pos()
        if (slider_pos > self.song_length_ms):
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
        self.state = PlayerState.LOADED

    def play_pause(self):
        self.cancel_slider_updates()
        if self.music_file is None:
            return

        if self.state is PlayerState.LOADED or self.state is PlayerState.STOPPED:
            # First play, load and start.
            self.player.play()
            self.state = PlayerState.PLAYING
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
