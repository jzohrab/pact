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


logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)

DEFAULT_DURATION = 0.3
DEFAULT_THRESHOLD = -30

parser = argparse.ArgumentParser(description='Split media into separate chunks wherever silence occurs')
parser.add_argument('--in_filename', default = 'samples/input.mp3', help='Input filename (`-` for stdin)')
parser.add_argument('--silence-threshold', default=DEFAULT_THRESHOLD, type=int, help='Silence threshold (in dB)')
parser.add_argument('--silence-duration', default=DEFAULT_DURATION, type=float, help='Silence duration')
parser.add_argument('-v', dest='verbose', action='store_true', help='Verbose mode')

silence_start_re = re.compile(r' silence_start: (?P<start>[0-9]+(\.?[0-9]*))$')
silence_end_re = re.compile(r' silence_end: (?P<end>[0-9]+(\.?[0-9]*)) ')
total_duration_re = re.compile(
    r'size=[^ ]+ time=(?P<hours>[0-9]{2}):(?P<minutes>[0-9]{2}):(?P<seconds>[0-9\.]{5}) bitrate=')


def _logged_popen(cmd_line, *args, **kwargs):
    logger.debug('Running command: {}'.format(subprocess.list2cmdline(cmd_line)))
    return subprocess.Popen(cmd_line, *args, **kwargs)


def get_chunk_times(in_filename, silence_threshold, silence_duration):
    p = _logged_popen(
        (ffmpeg
            .input(in_filename)
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
    
    lines = outlines

    # Chunks start when silence ends, and chunks end when silence starts.
    chunk_starts = []
    chunk_ends = []
    for line in lines:
        silence_start_match = silence_start_re.search(line)
        silence_end_match = silence_end_re.search(line)
        total_duration_match = total_duration_re.search(line)
        if silence_start_match:
            chunk_ends.append(float(silence_start_match.group('start')))
            if len(chunk_starts) == 0:
                # Started with non-silence.
                chunk_starts.append(0.)
        elif silence_end_match:
            chunk_starts.append(float(silence_end_match.group('end')))
        elif total_duration_match:
            hours = int(total_duration_match.group('hours'))
            minutes = int(total_duration_match.group('minutes'))
            seconds = float(total_duration_match.group('seconds'))
            end_time = hours * 3600 + minutes * 60 + seconds

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
