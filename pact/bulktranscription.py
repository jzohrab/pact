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

    def __update_progressbar(n):
        print(f'{n}%')

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
        print(bookmark.display())
        bookmark_done_callback(bookmark)
        ts.stop()

    ts = transcription_strategy
    transcription_strategy.start(
        audiosegment = c,
        on_update_transcription = lambda s: __set_transcription(s),
        on_update_progress = lambda n: print(f'{n}%'),
        on_finished = lambda s: __try_transcription_search(s, ts),
        on_daemon_thread = False
    )
    return transcription_strategy.transcription_thread


def get_transcribed_bookmarks(
        in_filename,
        segment_starts,
        end_time,
        transcription_strategy,
        bookmark_done_callback = None
):
    if in_filename is None or len(segment_starts) == 0:
        return []

    clipbounds = make_bounds(segment_starts, end_time)
    
    allthreads = []
    allbookmarks = []
    # Now for each chunk, play the segments of the file.
    for ct in clipbounds:
        # print('----')
        # print(ct)

        b = pact.music.Bookmark(ct[0])
        b.clip_bounds_ms = [ ct[0], ct[1] ]
        bookmark_done_callback(b)

        ## DISABLE transcription for now, just set the bounds.
        seg = pact.utils.audiosegment_from_mp3_time_range(in_filename, ct[0], ct[1])
        __transcribe(seg, b, transcription_strategy, bookmark_done_callback)

        allbookmarks.append(b)

        # allthreads.append(t)
        # t.join()

    # for t in allthreads:
    #     t.join()

    return allbookmarks


if __name__ == '__main__':
    import pact.split
    from pact.plugins.transcription import vosktranscription

    parser = argparse.ArgumentParser(description='Bulk transcription test')
    parser.add_argument('in_filename')
    parser.add_argument('vosk_model')
    parser.add_argument('--startms', type=int, default=0, help='start time (ms) for bookmarks')
    parser.add_argument('--endms', type=int, default=60000, help='end time (ms) for bookmarks')
    args = parser.parse_args()
    
    segment_starts = pact.split.segment_start_times(
        in_filename = args.in_filename,
        min_duration_ms = 5000.0,
        start_ms = args.startms,
        end_ms = args.endms
    )

    strategy = vosktranscription.VoskTranscriptionStrategy(args.vosk_model)

    def print_bookmark(b):
        print(b.to_dict())

    bookmarks = get_transcribed_bookmarks(
        in_filename = args.in_filename,
        segment_starts = segment_starts,
        end_time = args.endms,
        transcription_strategy = strategy,
        bookmark_done_callback = print_bookmark)

    print(f'Got {len(bookmarks)} bookmarks.')
