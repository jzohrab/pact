from datetime import datetime
from tempfile import NamedTemporaryFile
import configparser
import os
import sys
import requests
import shutil
import ffmpeg
import pydub
import threading


class TimeUtils:

    @staticmethod
    def time_string(ms):
        total_seconds = round(ms / 1000.0, 1)
        mins = int(total_seconds) // 60
        secs = total_seconds % 60
        return '{:02d}:{:04.1f}'.format(mins, secs)

    @staticmethod
    def interval_string(s, e, ifInvalid = 'n/a'):
        if (s >= e):
            return ifInvalid
        ss = TimeUtils.time_string(s)
        es = TimeUtils.time_string(e)
        return f'{ss} - {es}'


def get_config():
    """Return configparser.config for config.ini, or the value in PACTCONFIG env var."""
    config = configparser.ConfigParser()
    filename = os.environ.get('PACTCONFIG', 'config.ini')
    if not os.path.exists(filename):
        print(f'\nMissing required config file {filename}, quitting.\n')
        sys.exit(1)
    config.read(filename)
    return config


# From https://stackoverflow.com/questions/323972/is-there-any-way-to-kill-a-thread/
class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""
    def __init__(self,  *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


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


def anki_card_export(audiosegment, transcription = None, tag = None):
    """Export the current clip and transcription to Anki using Ankiconnect."""

    config = get_config()
    destdir = config['Anki']['MediaFolder']

    now = datetime.now() # current date and time
    date_time = now.strftime("%Y%m%d_%H%M%S")
    filename = f'clip_{date_time}_{id(audiosegment)}.mp3'
    destname = os.path.join(destdir, filename)

    with NamedTemporaryFile(suffix='.mp3') as temp:
        audiosegment.export(temp.name, format="mp3")
        shutil.copyfile(temp.name, destname)
        # print('Generated temp clip:')
        # print(temp.name)
        # print('Copied clip to:')
        # print(destname)

    a = config['AnkiCard']

    fields = {
        a['AudioField']: f'[sound:{filename}]'
    }

    if transcription is not None and transcription != '':
        fields[ a['TranscriptionField'] ] = transcription

    postjson = {
        "action": "addNote",
        "version": 6,
        "params": {
            "note": {
                "deckName": a['Deck'],
                "modelName": a['NoteType'],
                "fields": fields
            }
        }
    }

    if tag is not None and tag != '':
        postjson['params']['note']['tags'] = [ tag ]

    print(f'posting: {postjson}')
    url = config['Anki']['Ankiconnect']
    r = requests.post(url, json = postjson)
    print(f'result: {r.json()}')
    return r
