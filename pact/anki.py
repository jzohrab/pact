import os
import sys
import threading
from datetime import datetime
import json
import requests
from tempfile import NamedTemporaryFile
import shutil


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


def export(
        bookmark,
        audiosegment,
        tag,
        ankiconfig,
        onSuccess = lambda b: None,
        onError = lambda e: None
):
    """Exports a bookmark/clip to Anki in a thread."""

    def __do_export():
        try:
            bookmark.exported = 'Pending'
            anki_card_export(
                audiosegment = audiosegment,
                ankiconfig = ankiconfig,
                transcription = bookmark.transcription,
                notes = bookmark.notes,
                tag = tag
            )
            bookmark.exported = True
            onSuccess(bookmark)
            print(f'done export of bookmark {id(bookmark)}')
        except Exception as e:
            bookmark.exported = False
            onError(e)

    t = threading.Thread(target=__do_export)
    t.setDaemon(True)
    print(f'starting export of bookmark {id(bookmark)}')
    t.start()
