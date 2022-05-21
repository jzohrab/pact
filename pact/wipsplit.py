# Can run this from root dir like:
# python -m pact.wipsplit

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
import pact.music
import pydub.playback

import pact.textmatch
from pact.plugins.transcription import vosktranscription, unknown


logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__file__)
logger.setLevel(logging.INFO)

DEFAULT_DURATION = 0.3
DEFAULT_THRESHOLD = -10


def _logged_popen(cmd_line, *args, **kwargs):
    logger.debug('Running command: {}'.format(subprocess.list2cmdline(cmd_line)))
    return subprocess.Popen(cmd_line, *args, **kwargs)


# TODO: this belongs in utils
def get_chunk_starts(in_filename, silence_threshold, silence_duration):
    p = _logged_popen(
        (ffmpeg
            .input(in_filename)  # , ss = 0, t = 200)  # HACK SETTING TIME
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

    # Chunks start when silence ends.
    timematch = r'(?P<time>[0-9]+(\.?[0-9]*))'
    end_re = re.compile(f'silence_end: {timematch} ')
    duration_re = re.compile(
        r'size=[^ ]+ time=(?P<hours>[0-9]{2}):(?P<minutes>[0-9]{2}):(?P<seconds>[0-9\.]{5}) bitrate=')

    def time_ms(m):
        return round(float(m.group('time')) * 1000)

    chunk_starts = [0]
    for line in lines:
        end_match = end_re.search(line)
        duration_match = duration_re.search(line)
        if end_match:
            e = time_ms(end_match)
            chunk_starts.append(e)
        elif duration_match:
            hours = int(duration_match.group('hours'))
            minutes = int(duration_match.group('minutes'))
            seconds = float(duration_match.group('seconds'))
            end_s = hours * 3600 + minutes * 60 + seconds
            chunk_starts.append(end_s * 1000.0)

    chunk_starts.sort()
    return chunk_starts



### TODO - hide this somewhere, or just delete it.
def transcribe(c, bookmark, bookmark_done_callback):
    def __set_transcription(transcription):
        bookmark.transcription = transcription

    def __update_progressbar(n):
        print(f'{n}%')

    ## TODO: move this to textmatch.py, and add test cases.
    def __search_transcription(sought, transcription_file):
        if transcription_file is None:
            return sought

        contents = None
        with open(transcription_file) as f:
            contents = f.read()

        fuzzy_text_match_accuracy = 80
        matches = pact.textmatch.search(contents, sought, True, fuzzy_text_match_accuracy)
        if len(matches) == 0:
            return f'(?) {sought}'

        # print(f'matches: {matches}')
        result = [ pact.textmatch.ellipsify(m['match'], m['context']) for m in matches ]
        return '\n\n'.join(result).strip()

    def __try_transcription_search(sought, ts):
        sought = __search_transcription(sought, 'samples/input.txt')
        __set_transcription(sought)
        print(bookmark.display())
        bookmark_done_callback(bookmark)
        ts.stop()

    voskmodel = 'model/spanish'
    ts = vosktranscription.VoskTranscriptionStrategy(voskmodel)
    ts.start(
        audiosegment = c,
        on_update_transcription = lambda s: __set_transcription(s),
        on_update_progress = lambda n: print(f'{n}%'),
        on_finished = lambda s: __try_transcription_search(s, ts),
        on_daemon_thread = False
    )
    return ts.transcription_thread


def get_corrected_chunk_times(
        in_filename,
        silence_threshold = DEFAULT_THRESHOLD,
        silence_duration = DEFAULT_DURATION
):
    chunk_starts = get_chunk_starts(in_filename, silence_threshold, silence_duration)
    # chunk_times = chunk_times[0:10]
    # print(f'Count of chunks: {len(chunk_times)}')
    # print(chunk_times)

    # Note that chunk_starts 's last entry is the end of the file,
    # it's like an EOF marker, so can use it when determining the
    # actual starts we need.

    # Convert to durations, use consecutive start times.
    # add a fake ending time to make a final chunk.
    chunk_times = []
    for i in range(0, len(chunk_starts) - 1):
        chunk_times.append((chunk_starts[i], chunk_starts[i+1]))

    chunk_times = [
        c for c in chunk_times
        if (c[1] - c[0] > 10)
    ]

    return chunk_times


def get_bookmarks(
        in_filename,
        silence_threshold = DEFAULT_THRESHOLD,
        silence_duration = DEFAULT_DURATION,
        bookmark_done_callback = None
):
    chunk_times = get_corrected_chunk_times(in_filename, silence_threshold, silence_duration)

    allthreads = []
    allbookmarks = []
    # Now for each chunk, play the segments of the file.
    for ct in chunk_times:
        # print('----')
        # print(ct)

        b = pact.music.Bookmark(ct[0])
        b.clip_bounds_ms = [ ct[0], ct[1] ]
        bookmark_done_callback(b)
        allbookmarks.append(b)

        ## DISABLE transcription for now, just set the bounds.
        # seg = pact.utils.audiosegment_from_mp3_time_range(in_filename, ct[0], ct[1])
        # transcribe(seg, b, bookmark_done_callback)

        # pydub.playback.play(seg)
        # allthreads.append(t)
        # t.join()

    # for t in allthreads:
    #     t.join()

    return allbookmarks


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Split media into separate chunks wherever silence occurs')
    parser.add_argument('in_filename', help='Input filename (`-` for stdin)')
    parser.add_argument('--silence-threshold', default=DEFAULT_THRESHOLD, type=int, help='Silence threshold (in dB)')
    parser.add_argument('--silence-duration', default=DEFAULT_DURATION, type=float, help='Silence duration')
    parser.add_argument('-v', dest='verbose', action='store_true', help='Verbose mode')

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(levels): %(message)s')
        logger.setLevel(logging.DEBUG)

    ct = get_corrected_chunk_times(
        args.in_filename,
        args.silence_threshold,
        args.silence_duration
    )
    durations = [
        c[1] - c[0]
        for c in ct
    ]

    print(f'count of chunks: {len(ct)}')
    print(f'min duration: {min(durations)}')

    for c in ct[0:10]:
        print(c)
    print('...')
    for c in ct[-11:-1]:
        print(c)
        print(pact.utils.TimeUtils.time_string(c[1]))
