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
def get_chunk_times(in_filename, silence_threshold, silence_duration):
    p = _logged_popen(
        (ffmpeg
            .input(in_filename, ss = 0, t = 200)  # HACK SETTING TIME
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
    # ... but setting the chunk end to be at the silence start appears
    # to cut off the clip -- clips are ending too early.
    timematch = r'(?P<time>[0-9]+(\.?[0-9]*))'
    start_re = re.compile(f'silence_start: {timematch}$')
    end_re = re.compile(f'silence_end: {timematch} ')

    def time_match(m):
        return float(m.group('time'))

    chunk_starts = []
    chunk_ends = []
    current_start = 0
    for line in lines:
        start_match = start_re.search(line)
        end_match = end_re.search(line)
        if start_match:
            s = time_match(start_match)
            chunk_ends.append(s)
            if len(chunk_starts) == 0:
                # Started with non-silence.
                chunk_starts.append(0.)
        elif end_match:
            e = time_match(end_match)
            chunk_starts.append(e)

    if len(chunk_starts) == 0:
        # No silence found.
        chunk_starts.append(0.)

    if len(chunk_starts) > len(chunk_ends):
        # Finished with non-silence.
        chunk_ends.append(10000000.)

    return list(zip(chunk_starts, chunk_ends))



def transcribe(c, bookmark):
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

    def __try_transcription_search(sought):
        sought = __search_transcription(sought, 'samples/input.txt')
        __set_transcription(sought)

    voskmodel = 'model/spanish'
    ts = vosktranscription.VoskTranscriptionStrategy(voskmodel)
    ts.start(
        audiosegment = c,
        on_update_transcription = lambda s: __set_transcription(s),
        on_update_progress = lambda n: None,
        on_finished = lambda s: __try_transcription_search(s)
    )
    return ts.transcription_thread


def get_bookmarks(
    in_filename,
    silence_threshold = DEFAULT_THRESHOLD,
    silence_duration = DEFAULT_DURATION
):
    chunk_times = get_chunk_times(in_filename, silence_threshold, silence_duration)
    chunk_times = chunk_times[0:5]
    print(f'Count of chunks: {len(chunk_times)}')
    print(chunk_times)

    # Chunks are getting cut off early, so instead of using the start
    # and end times, just use the start times (and for the last one,
    # use the end time plus an arbitrary padding, which will hopefully
    # prevent it from being cut off).
    padding = 0.25
    faketimes = chunk_times
    lastchunk = chunk_times[-1]
    faketimes.append((lastchunk[1] + padding, lastchunk[1] + padding))
    print('fakes:')
    print(faketimes)
    newtimes = []
    for i in range(0, len(faketimes) - 1):
        newtimes.append((faketimes[i][0], faketimes[i+1][0]))

    print('new:')
    print(newtimes)

    chunk_times = newtimes
    chunk_times = [
        c for c in chunk_times
        if (c[1] - c[0] > 0.001)
    ]
    print(f'Count of chunks after filter: {len(chunk_times)}')

    allthreads = []
    allbookmarks = []
    # Now for each chunk, play the segments of the file.
    for ct in chunk_times:
        print('----')
        print(ct)

        b = pact.music.Bookmark(ct[0])
        b.clip_bounds_ms = [ ct[0], ct[1] ]
        allbookmarks.append(b)

        seg = pact.utils.audiosegment_from_mp3_time_range(in_filename, ct[0] * 1000.0, ct[1] * 1000.0)
        t = transcribe(seg, b)
        # pydub.playback.play(seg)
        allthreads.append(t)

    for t in allthreads:
        t.join()

    return allbookmarks


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Split media into separate chunks wherever silence occurs')
    parser.add_argument('--in_filename', default = 'samples/input.mp3', help='Input filename (`-` for stdin)')
    parser.add_argument('--silence-threshold', default=DEFAULT_THRESHOLD, type=int, help='Silence threshold (in dB)')
    parser.add_argument('--silence-duration', default=DEFAULT_DURATION, type=float, help='Silence duration')
    parser.add_argument('-v', dest='verbose', action='store_true', help='Verbose mode')

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(levels): %(message)s')
        logger.setLevel(logging.DEBUG)

    bookmarks = get_bookmarks(
        args.in_filename,
        args.silence_threshold,
        args.silence_duration
    )
    print('=' * 50)
    for b in bookmarks:
        print(b.to_dict())
