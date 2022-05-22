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


# TODO: this belongs in utils
def get_chunk_starts(in_filename, silence_threshold, silence_duration, start_ms = 0, end_ms = 200 * 1000):
    print(f'start_ms = {start_ms}')
    print(f'end_ms = {end_ms}')
    ss = (start_ms/1000.0)
    print(f'ss = {ss}')
    t = (end_ms - start_ms)/1000.0
    print(f't = {t}')

    outlines = []
    cmd = (
        ffmpeg
        .input(in_filename, ss=ss, t=t)
        .filter('silencedetect', n='{}dB'.format(silence_threshold), d=silence_duration)
        .output('-', format='null')
        .compile()
    ) + ['-nostats']  # FIXME: use .nostats() once it's implemented in ffmpeg-python.
    logger.debug(f'Running command: {subprocess.list2cmdline(cmd)}')
    with subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            stdout = subprocess.PIPE
    ) as p:
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
    timematch = r'(?P<deltafromstart>[0-9]+(\.?[0-9]*))'
    end_re = re.compile(f'silence_end: {timematch} ')

    # The time returned is the deltafromstart ... i.e., the actual
    # time is the start_ms + the delta.
    def time_ms(m):
        return start_ms + round(float(m.group('deltafromstart')) * 1000)

    chunk_starts = [start_ms]
    for line in lines:
        end_match = end_re.search(line)
        if end_match:
            e = time_ms(end_match)
            chunk_starts.append(e)

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
        silence_duration = DEFAULT_DURATION,
        min_duration_ms = 5000.0,
        start_ms = 0,
        end_ms = 200 * 1000
):
    chunk_starts = get_chunk_starts(in_filename, silence_threshold, silence_duration, start_ms = start_ms, end_ms = end_ms)

    # On my system at least, ffmpeg appears to find the start times a
    # shade too late (i.e., the sound is clipped at the start if I
    # start playing exactly where it ends).  I can't sort out why
    # given what I currently know, so arbitrarily shift the start
    # times back a few hundred ms.  It will give a small bit of noise,
    # but that's fine.
    shift_by_ms = 200
    chunk_starts = [
        c - shift_by_ms if c > start_ms + shift_by_ms else c
        for c
        in chunk_starts
    ]
    chunk_times = pact.utils.sensible_start_times(chunk_starts, min_duration_ms)

    print(f'Initial split chunk count: {len(chunk_starts)}')
    print(f'cleaned up chunk count: {len(chunk_times)}')

    return chunk_times


def get_bookmarks(
        in_filename,
        silence_threshold = DEFAULT_THRESHOLD,
        silence_duration = DEFAULT_DURATION,
        min_duration_ms = 2000.0,
        bookmark_done_callback = None
):
    chunk_times = get_corrected_chunk_times(in_filename, silence_threshold, silence_duration, min_duration_ms)

    allthreads = []
    allbookmarks = []
    # Now for each chunk, play the segments of the file.
    for ct in chunk_times:
        # print('----')
        # print(ct)

        b = pact.music.Bookmark(ct)
        # b.clip_bounds_ms = [ ct[0], ct[1] ]
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
    parser.add_argument('--startms', default=0, type=int, help='Start ms')
    parser.add_argument('--endms', default=120000, type=int, help='End ms')
    parser.add_argument('-v', dest='verbose', action='store_true', help='Verbose mode')

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(levels): %(message)s')
        logger.setLevel(logging.DEBUG)

    ct = get_corrected_chunk_times(
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

    for c in ct:
        print(pact.utils.TimeUtils.time_string(c))
