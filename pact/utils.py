from datetime import datetime
from tempfile import NamedTemporaryFile
import configparser
import os
import requests
import shutil


class TimeUtils:

    @staticmethod
    def time_string(ms):
        total_seconds = ms / 1000.0
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


def anki_card_export(audiosegment, transcription = None):
    """Export the current clip and transcription to Anki using Ankiconnect."""

    config = configparser.ConfigParser()
    config.read('config.ini')
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

    print(f'posting: {postjson}')
    url = config['Anki']['Ankiconnect']
    r = requests.post(url, json = postjson)
    print(f'result: {r.json()}')
    return r
