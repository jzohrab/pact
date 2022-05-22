import argparse
import ffmpeg
import logging
import os
import re
import subprocess
import sys

import pact.utils
import pact.music
import pact.textmatch
from pact.plugins.transcription import vosktranscription, unknown


def make_bounds(start_times, end_time):
    if len(start_times) == 0:
        return []
    ret = []
    for i in range(0, len(start_times) - 1):
        ret.append([ start_times[i], start_times[i + 1] ])
    ret.append([ start_times[-1], end_time ])
    return ret


def transcribe(c, bookmark, transcription_strategy, bookmark_done_callback):
    def __set_transcription(transcription):
        bookmark.transcription = transcription

    def __update_progressbar(n):
        print(f'{n}%')

    def __search_transcription(sought, transcription_file):
        if transcription_file is None:
            return sought
        fuzzy_text_match_accuracy = 80
        result = pact.textmatch.search_transcription(
            sought, transcription_file, fuzzy_text_match_accuracy)
        if len(result) == 0:
            return f'(?) {sought}'
        return '\n\n'.join(result).strip()

    def __try_transcription_search(sought, ts):
        sought = __search_transcription(sought, 'samples/input.txt')
        __set_transcription(sought)
        print(bookmark.display())
        bookmark_done_callback(bookmark)
        ts.stop()

    transcription_strategy.start(
        audiosegment = c,
        on_update_transcription = lambda s: __set_transcription(s),
        on_update_progress = lambda n: print(f'{n}%'),
        on_finished = lambda s: __try_transcription_search(s, ts),
        on_daemon_thread = False
    )
    return ts.transcription_thread


def get_transcribed_bookmarks(
        in_filename,
        segment_starts,
        transcription_strategy,
        bookmark_done_callback = None
):
    if in_filename is None or len(segment_starts) == 0:
        return []

    endtime = max(segment_starts) + 60 * 60 * 1000;
    clipbounds = make_bounds(segment_starts, endtime)
    
    allthreads = []
    allbookmarks = []
    # Now for each chunk, play the segments of the file.
    for ct in clipbounds:
        # print('----')
        # print(ct)

        b = pact.music.Bookmark(ct[0])
        b.clip_bounds_ms = [ ct[0], ct[1] ]
        bookmark_done_callback(b)
        allbookmarks.append(b)

        ## DISABLE transcription for now, just set the bounds.
        # seg = pact.utils.audiosegment_from_mp3_time_range(in_filename, ct[0], ct[1])
        # transcribe(seg, b, bookmark_done_callback)

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
