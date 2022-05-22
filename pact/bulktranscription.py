"""Bulk transcription.

This module works, but it's slow.  It might suffice for _some_
purpose, but I don't need it yet, and so am not hooking it up.

Sample run of __main__:

$ python -m pact.bulktranscription samples/input.mp3 model/spanish --endms 40000
1 of 6: 00:00.0  "... Esta semana terminamos las charlas y talleres  ..."
2 of 6: 00:08.7  "Si te perdiste algún evento aún puedes acceder a é ..."
3 of 6: 00:15.7  "... da clic en compra: enviaremos a tu correo una  ..."
4 of 6: 00:22.0  "Cada boleto que has comprado contribuye a sostener ..."
5 of 6: 00:29.0  "Pronto tendremos también nuestra fiesta para que f ..."
6 of 6: 00:36.6  "(?) dieciséis de julio de mil novecientos noventa  ..."
Got 6 bookmarks after 00:25.3.
"""

import argparse
import sys
import pact.utils
import pact.music
import pact.textmatch


def make_bounds(start_times, end_time):
    if len(start_times) == 0:
        return []
    ret = []
    for i in range(0, len(start_times) - 1):
        ret.append([ start_times[i], start_times[i + 1] ])
    ret.append([ start_times[-1], end_time ])
    return ret


def __transcribe(c, bookmark, transcription_strategy, bookmark_done_callback):
    def __set_transcription(transcription):
        bookmark.transcription = transcription

    def __search_transcription(sought, transcription_file):
        if transcription_file is None:
            return sought
        fuzzy_text_match_accuracy = 80
        result = pact.textmatch.search_transcription(
            sought, transcription_file, fuzzy_text_match_accuracy)
        if result is None:
            return f'(?) {sought}'
        return '\n\n'.join(result).strip()

    def __try_transcription_search(sought, ts):
        sought = __search_transcription(sought, 'samples/input.txt')
        __set_transcription(sought)
        bookmark_done_callback(bookmark)
        ts.stop()

    ts = transcription_strategy
    transcription_strategy.start(
        audiosegment = c,
        on_update_transcription = lambda s: __set_transcription(s),
        on_update_progress = lambda n: None,
        on_finished = lambda s: __try_transcription_search(s, ts),
        on_daemon_thread = False
    )


def get_transcribed_bookmarks(
        in_filename,
        segment_starts,
        end_time,
        transcription_strategy,
        bookmark_done_callback = None
):
    if in_filename is None or len(segment_starts) == 0:
        return []

    allbookmarks = []
    for ct in make_bounds(segment_starts, end_time):
        b = pact.music.Bookmark(ct[0])
        b.clip_bounds_ms = [ ct[0], ct[1] ]
        seg = pact.utils.audiosegment_from_mp3_time_range(in_filename, ct[0], ct[1])
        __transcribe(seg, b, transcription_strategy, bookmark_done_callback)
        allbookmarks.append(b)

    return allbookmarks


if __name__ == '__main__':
    import pact.split
    from pact.plugins.transcription import vosktranscription
    from pact.utils import TimeUtils
    import time

    parser = argparse.ArgumentParser(description='Bulk transcription test')
    parser.add_argument('in_filename')
    parser.add_argument('vosk_model')
    parser.add_argument('--startms', type=int, default=0, help='start time (ms) for bookmarks')
    parser.add_argument('--endms', type=int, default=60000, help='end time (ms) for bookmarks')
    args = parser.parse_args()

    starttime = time.time()
    segment_starts = pact.split.segment_start_times(
        in_filename = args.in_filename,
        min_duration_ms = 5000.0,
        start_ms = args.startms,
        end_ms = args.endms
    )

    strategy = vosktranscription.VoskTranscriptionStrategy(args.vosk_model)

    n = 0
    def print_progress(b):
        global n
        n += 1
        print(f'{n} of {len(segment_starts)}: {b.display()}')

    bookmarks = get_transcribed_bookmarks(
        in_filename = args.in_filename,
        segment_starts = segment_starts,
        end_time = args.endms,
        transcription_strategy = strategy,
        bookmark_done_callback = print_progress)

    endtime = time.time()
    duration = endtime - starttime
    t = TimeUtils.time_string(duration * 1000)
    print(f'Got {len(bookmarks)} bookmarks after {t}.')

