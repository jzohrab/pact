from datetime import datetime
from tempfile import NamedTemporaryFile
import configparser
import json
import os
import sys
import requests
import shutil
import ffmpeg
import pydub
from importlib import import_module
import time


class Profile(object):
    """Convenience for finding bottlenecks."""
    def __init__(self, name):
        self.name = name
        self.start = time.perf_counter()
        self.stopped = False

    def printElapsed(self):
        e = time.perf_counter()
        delta = e - self.start
        # print(f'{self.name}: {delta}')

    def __del__(self):
        if not self.stopped:
            self.printElapsed()

    def stop(self):
        self.stopped = True
        self.printElapsed()


class TimeUtils:

    @staticmethod
    def time_string(ms):
        total_seconds = round(ms / 1000.0, 1)
        s = int(total_seconds)
        hrs = s // 3600
        mins = (s - hrs * 3600) // 60
        secs = total_seconds % 60
        if hrs == 0:
            return '{:02d}:{:04.1f}'.format(mins, secs)
        return '{:d}:{:02d}:{:04.1f}'.format(hrs, mins, secs)

    @staticmethod
    def interval_string(s, e, ifInvalid = 'n/a'):
        if (s >= e):
            return ifInvalid
        ss = TimeUtils.time_string(s)
        es = TimeUtils.time_string(e)
        return f'{ss} - {es}'


def lookup(selected_text, lookup_module_name):
    mod = import_module(lookup_module_name)
    lookup = getattr(mod, 'lookup')
    return lookup(selected_text)


def audiosegment_from_mp3_time_range(path_to_mp3, starttime_ms, endtime_ms):
    """Make an audio clip from mp3 _very quickly_ using ffmpeg-python."""
    # ref https://github.com/jiaaro/pydub/issues/135

    duration_ms = endtime_ms - starttime_ms
    seg = None
    with NamedTemporaryFile("w+b", suffix=".mp3") as f:
        ffmpeg_cmd = (
            ffmpeg
            .input(path_to_mp3, ss = (starttime_ms/1000.0), t = (duration_ms/1000.0))

            # vsync vfr added per https://stackoverflow.com/questions/18064604/
            #   frame-rate-very-high-for-a-muxer-not-efficiently-supporting-it
            # loglevel added to quiet down ffmpeg console output.
            .output(f.name, acodec='copy', **{'vsync':'vfr', 'loglevel':'error'})
            .overwrite_output()
        )
        # print('args:')
        # print(ffmpeg_cmd.get_args())
        ffmpeg_cmd.run()

        seg = pydub.AudioSegment.from_mp3(f.name)

    return seg


def anki_tag_from_filename(f):
    tag = os.path.basename(f)
    tag = ''.join([
        c
        for c in tag
        if c.isalnum() or c in "._- "
    ])
    if tag == '.mp3':
        tag = 'Unknown.mp3'
    tag = tag.replace(' ', '-')
    return tag


def anki_card_export(
        audiosegment,
        ankiconfig,
        transcription = None,
        notes = None,
        tag = None):
    """Export the current clip and transcription to Anki using Ankiconnect."""

    required = [ 'Ankiconnect', 'MediaFolder',
                 'AudioField', 'TranscriptionField', 'NotesField',
                 'Deck', 'NoteType' ]
    missing = [r for r in required if ankiconfig.get(r, None) is None]
    if len(missing) > 0:
        msg = f"Missing required fields {', '.join(missing)} in config file."
        raise RuntimeError(msg)

    now = datetime.now() # current date and time
    date_time = now.strftime("%Y%m%d_%H%M%S")
    filename = f'clip_{date_time}_{id(audiosegment)}.mp3'
    destdir = ankiconfig['MediaFolder']
    destname = os.path.join(destdir, filename)

    with NamedTemporaryFile(suffix='.mp3') as temp:
        audiosegment.export(temp.name, format="mp3")
        shutil.copyfile(temp.name, destname)
        # print('Generated temp clip:')
        # print(temp.name)
        # print('Copied clip to:')
        # print(destname)

    fields = {
        ankiconfig['AudioField']: f'[sound:{filename}]'
    }

    def _set_field(fldname, txt):
        if txt is not None and txt != '':
            fields[fldname] = txt.strip().replace("\n", '<br>')

    _set_field(ankiconfig['TranscriptionField'], transcription)
    _set_field(ankiconfig['NotesField'], notes)

    postjson = {
        "action": "addNote",
        "version": 6,
        "params": {
            "note": {
                "deckName": ankiconfig['Deck'],
                "modelName": ankiconfig['NoteType'],
                "fields": fields
            }
        }
    }

    if tag is not None and tag != '':
        postjson['params']['note']['tags'] = [ tag ]

    print(f'posting: {postjson}')
    url = ankiconfig['Ankiconnect']
    r = requests.post(url, json = postjson)
    print(f'result: {r.json()}')

    e = r.json()['error']
    if e is not None:
        raise RuntimeError(e)

    return r


def play_beep():
    """Make a beep sound."""
    # Note using sys.stdout instead of print
    # to suppress console line feeds,
    # and flushing immediately to have the beep
    # sound right away.
    # Not sure if this is mac-only.
    sys.stdout.write('\a')
    sys.stdout.flush()
