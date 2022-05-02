# This is obsolete code, but am keeping it (for now) for interest's
# sake.
#
# Originally in this project, mp3 playback was handled by pygame, but
# I had problems with pygame not having accurate time when it comes to
# mp3s.  Per
# https://www.pygame.org/docs/ref/music.html#pygame.mixer.music.play :
#
# "For MP3 files the start time position selected may not be accurate
# as things like variable bit rate encoding and ID3 tags can throw off
# the timing calculations."
#
# This time skew was very pronounced in some files.
#
# Switched to vlc.

from pygame import mixer

mixer.init()

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
