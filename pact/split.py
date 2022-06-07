# Can run this from root dir like:
# python -m pact.split

# Initial ideas taken from
# https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/examples/split_silence.py


import argparse
import ffmpeg
import logging
import os
import re
import subprocess
import sys

import pact.utils
from pact.utils import Profile
import pact.music
import pact.textmatch
from pact.plugins.transcription import vosktranscription, unknown

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)


# Duration for splits.
DEFAULT_DURATION = 0.3

# dB threshold for splits.
DEFAULT_THRESHOLD = -10


def raw_start_times(in_filename, silence_threshold, silence_duration, start_ms = 0, end_ms = 200 * 1000):
    """Given an in_filename, find possible split points (phrase start
    times) using ffmpeg.

    Note that potential phrase start times are actually when any
    silence in the clip *ends*.
    """

    timematch = r'(?P<deltafromstart>[0-9]+(\.?[0-9]*))'
    end_re = re.compile(f'silence_end: {timematch} ')

    # The time returned is the deltafromstart; i.e., the actual
    # time is the start_ms + the delta.
    def time_ms(m):
        return start_ms + round(float(m.group('deltafromstart')) * 1000)

    # ffmpeg outputs e.g. "silence_end: 123.234" to stderr.
    def add_if_matches_end_re(line, arr):
        s = line.decode('utf-8').strip()
        end_match = end_re.search(s)
        if end_match:
            arr.append(time_ms(end_match))

    ffmpegcmd = (
        ffmpeg
        .input(in_filename, ss=(start_ms/1000.0), t=(end_ms-start_ms)/1000.0)
        .filter('silencedetect', n='{}dB'.format(silence_threshold), d=silence_duration)
        .output('-', format='null')
        .compile()
    ) + ['-nostats']  # FIXME: use .nostats() once it's implemented in ffmpeg-python.
    logger.debug(f'Running command: {subprocess.list2cmdline(ffmpegcmd)}')

    ppopen = Profile('split.subprocess')
    chunk_starts = [start_ms]
    with subprocess.Popen(
            ffmpegcmd,
            stderr=subprocess.PIPE,
            stdout = subprocess.PIPE) as p:
        for line in p.stderr:
            add_if_matches_end_re(line, chunk_starts)
    ppopen.stop()
    return chunk_starts


def sensible_start_times(start_times, min_duration):
    """Splitting an mp3 with ffmpeg can result in very short clips; too
    short to be practical.  For example, you might end up with clips
    with the following start times (seconds):

    0
    0.1
    0.5
    2.1
    2.2
    5

    This routine would return only those start times that result in
    clips of sensible lengths; e.g. with min_duration = 0.5:

    0
    # 0.1 - skipped, included in the clip starting at 0
    0.5
    2.1
    # 2.2 - skipped, included in clip starting at 2.1
    5

    """

    start_times.sort()
    ret = [start_times[0]]
    for candidate_start in start_times[1:]:
        curr_len = candidate_start - ret[-1]
        if curr_len >= min_duration:
            ret.append(candidate_start)
    return ret


def correct_raw(segstarts, min_duration_ms = 5000.0, shift_ms = 200):

    # On my system at least, ffmpeg appears to find the start times a
    # shade too late (i.e., the sound is clipped at the start if I
    # start playing exactly where it ends).  I can't sort out why
    # given what I currently know, so arbitrarily shift the start
    # times back a few hundred ms.  It will give a small bit of noise,
    # but that's fine.

    if len(segstarts) < 2:
        # Nothing to correct: either no start times, or just one which
        # can't be shifted/combined.
        return segstarts

    first = segstarts[0]
    ret = [
        max(c - shift_ms, first)   # May result in many set to first
        for c
        in segstarts
    ]

    # Remove duplicates (likely unnecessary)
    ret = list(set(ret))
    ret.sort()  # !!! Have to sort again for sensible_start_times!

    ret = sensible_start_times(ret, min_duration_ms)

    return ret


def segment_start_times(
        in_filename,
        silence_threshold = DEFAULT_THRESHOLD,
        silence_duration = DEFAULT_DURATION,
        min_duration_ms = 5000.0,
        start_ms = 0,
        end_ms = 200 * 1000,
        shift_ms = 200):
    chunk_starts = raw_start_times(
        in_filename,
        silence_threshold,
        silence_duration,
        start_ms = start_ms,
        end_ms = end_ms)
    return correct_raw(chunk_starts, min_duration_ms, shift_ms)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Get start times for clips')
    parser.add_argument('in_filename', help='Input filename')
    parser.add_argument('--silence-threshold', default=DEFAULT_THRESHOLD, type=int, help='Silence threshold (in dB)')
    parser.add_argument('--silence-duration', default=DEFAULT_DURATION, type=float, help='Silence duration')
    parser.add_argument('--startms', default=0, type=int, help='Start ms')
    parser.add_argument('--endms', default=120000, type=int, help='End ms')
    parser.add_argument('-v', dest='verbose', action='store_true', help='Verbose mode')

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(levels): %(message)s')
        logger.setLevel(logging.DEBUG)

    ct = segment_start_times(
        in_filename = args.in_filename,
        silence_threshold = args.silence_threshold,
        silence_duration = args.silence_duration,
        min_duration_ms = 5000.0,
        start_ms = args.startms,
        end_ms = args.endms
    )
    durations = [
        ct[i + 1] - ct[i]
        for i in range(0, len(ct) - 1)
    ]

    print(f'count of chunks: {len(ct)}')
    print(f'min duration: {min(durations)}')
    print('First 10:')
    for c in ct[0:10]:
        print(pact.utils.TimeUtils.time_string(c))
