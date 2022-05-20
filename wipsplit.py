# work-in-progress, splitting a file.

#### import ffmpeg
#### ffmpeg_cmd = (
####     ffmpeg
####     .input(path_to_mp3)
####     .filter('silencedetect', d=0.25)
#### )
#### # print('args:')
#### # print(ffmpeg_cmd.get_args())
#### ffmpeg_cmd.run()


# MASSIVE steal from
# https://raw.githubusercontent.com/kkroening/ffmpeg-python/master/examples/split_silence.py

import argparse
import ffmpeg
import logging
import os
import re
import subprocess
import sys

import pact.utils
import pydub.playback


logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)

DEFAULT_DURATION = 0.3
DEFAULT_THRESHOLD = -10

parser = argparse.ArgumentParser(description='Split media into separate chunks wherever silence occurs')
parser.add_argument('--in_filename', default = 'samples/input.mp3', help='Input filename (`-` for stdin)')
parser.add_argument('--silence-threshold', default=DEFAULT_THRESHOLD, type=int, help='Silence threshold (in dB)')
parser.add_argument('--silence-duration', default=DEFAULT_DURATION, type=float, help='Silence duration')
parser.add_argument('-v', dest='verbose', action='store_true', help='Verbose mode')


def _logged_popen(cmd_line, *args, **kwargs):
    logger.debug('Running command: {}'.format(subprocess.list2cmdline(cmd_line)))
    return subprocess.Popen(cmd_line, *args, **kwargs)


# TODO: this belongs in utils
def get_chunk_times(in_filename, silence_threshold, silence_duration):
    p = _logged_popen(
        (ffmpeg
            .input(in_filename, ss = 0, t = 100)  # HACK SETTING TIME
            .filter('silencedetect', n='{}dB'.format(silence_threshold), d=silence_duration)
            .output('-', format='null')
            .compile()
        ) + ['-nostats'],  # FIXME: use .nostats() once it's implemented in ffmpeg-python.
        stderr=subprocess.PIPE,
        stdout = subprocess.PIPE
    )

    outlines = []
    while True:
        line = p.stderr.readline()
        if not line:
            break
        s = line.decode('utf-8').strip()
        outlines.append(s)
        print(s)
        sys.stdout.flush()

    ## TODO: combine the regex matching below with the data collection
    ## above?
    lines = outlines

    # Chunks start when silence ends, and chunks end when silence starts.
    timematch = r'(?P<time>[0-9]+(\.?[0-9]*))'
    start_re = re.compile(f'silence_start: {timematch}$')
    end_re = re.compile(f'silence_end: {timematch} ')

    def time_match(m):
        return float(m.group('time'))

    chunk_starts = []
    chunk_ends = []
    for line in lines:
        start_match = start_re.search(line)
        end_match = end_re.search(line)
        if start_match:
            chunk_ends.append(time_match(start_match))
            if len(chunk_starts) == 0:
                # Started with non-silence.
                chunk_starts.append(0.)
        elif end_match:
            chunk_starts.append(time_match(end_match))

    if len(chunk_starts) == 0:
        # No silence found.
        chunk_starts.append(0.)

    if len(chunk_starts) > len(chunk_ends):
        # Finished with non-silence.
        chunk_ends.append(10000000.)

    return list(zip(chunk_starts, chunk_ends))



if __name__ == '__main__':
    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(levels): %(message)s')
        logger.setLevel(logging.DEBUG)

    in_filename = args.in_filename
    silence_threshold = args.silence_threshold
    silence_duration = args.silence_duration

    chunk_times = get_chunk_times(in_filename, silence_threshold, silence_duration)
    print(f'Count of chunks: {len(chunk_times)}')
    print(chunk_times[0:10])

    chunk_times = [
        c for c in chunk_times
        if (c[1] - c[0] > 0.001)
    ]
    print(f'Count of chunks after filter: {len(chunk_times)}')
    
    # Now for each chunk, play the segments of the file.
    for ct in chunk_times[0:10]:
        print('----')
        print(ct)
        seg = pact.utils.audiosegment_from_mp3_time_range(in_filename, ct[0] * 1000.0, ct[1] * 1000.0)
        pydub.playback.play(seg)
