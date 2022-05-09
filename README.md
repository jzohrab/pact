# Pact - Python Audio Clip Tool

Summary: this lets you quickly extract audio clips from .mp3 files
(from podcasts, etc) with a transcription, and export it to Anki using
Ankiconnect.

mp3 playing and hacking is done using ffmpeg.

The transcription is done using
[Vosk](https://github.com/alphacep/vosk-api/tree/master/python).

If you also have a transcription file (in .txt format), it's searched
to find the best possible match using the Vosk transcription as a
starting point.  This is helpful because sometimes the Vosk
transcription is a bit off.

**NOTE: I've only run this (and tested it) on Mac ... I'm not sure how
it will behave on other OS's.**


## Installation

To use this, you'll need to:

* [Get the code](#get-the-code)
* [Install python requirements](#install-python-requirements)
* [Install ffmpeg](#ffmpeg)
* [Install a Vosk model](#vosk-model)

To automatically export to Anki, you'll also need:

* [AnkiConnect](#ankiconnect)
* [Anki notes](#anki-notes)
* [config.ini](#config-ini)


### Get the code

```
# Clone using Github ...
cd /some/directory
git clone git@github.com:jzohrab/pact.git
cd pact

# ... or get it in a zipfile
cd /some/directory
mkdir pact  # or whatever
# get file from https://github.com/jzohrab/pact/archive/refs/heads/main.zip ...
# ... and unzip in pact directory
```

### Install python requirements

```
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (some from other git repos, see requirements.txt)
.venv/bin/pip3 install -r requirements.txt

# (... work work work OR use use use)

deactivate
```

### ffmpeg

Install ffmpeg on your system.

For Mac with homebrew:

```
brew install ffmpeg
```

Other OSs: ?

### Vosk model

Vosk uses a "language model" for offline audio transcription.

* Download the appropriate model from https://alphacephei.com/vosk/models

* Unzip it and store the contents in a `model` subdirectory under this
  main directory (a sibling to the `pact` directory).

For example, my directory structure looks like this:

```
LICENSE
README.md  # (this file)
...
+ model
    Gr.fst
    HCLr.fst
    README   # (the Vosk model readme)
    disambig_tid.int
+ pact
...
```

### Ankiconnect

This is an add-on for Anki.  See
[https://ankiweb.nqet/shared/info/2055492159](AnkiConnect add-on) on
AnkiWeb.

See https://github.com/FooSoft/anki-connect#installation for possible
additional setup required.

### Anki notes

You'll need a Note Type with separate fields for the audio file and
the transcription.  The names don't matter, because you specify that
in the `config.ini` file.

If you're going to leave the transcription blank -- e.g., if you
delete the transcription suggestions that `pact` provides using Vosk
-- the Transcription field can't be the first field in the Note type,
because Anki doesn't allow empty first fields.

<details>
  <summary>Sample card layout</summary>
  <p>

Front template:

```
<div style="background-color: black; margin: 20px; margin-top: 50px;">
  {{Text}}
</div>

{{Audio}}

<div class="tag">{{Tags}}</div>
```

Back template:

```
<div style="/* background-color: black;*/ margin: 20px; margin-top: 50px;">
  {{Text}}
</div>

{{Audio}}

<div class="tag">{{Tags}}</div>


{{#Extra_info}}
  <br>
  <div style="text-align: center;">
  <div style="display: inline-block;" class="greybox">
  {{Extra_info}}
  </div>
</div>
{{/Extra_info}}
```

Styling:

```
.card {
 font-family: arial;
 font-size: 20px;
 text-align: center;
 color: black;
 background-color: white;
}

.tag {
 font-size: 12px;
 color: grey;
 font-style: italic;
 padding: 10px;
 text-align: right;
}

.greybox {
  text-align: left;
  max-width: 400px;
  background-color: #f5f5f5;
  padding: 5px;
}

.card1 { background-color: #FFFFFF; }
.card2 { background-color: #FFFFFF; }
```
  </p>
</details>


### config.ini

Copy `config.ini.example` to `config.ini`, and edit it to match your setup.


### Lookup plugins

> Note: I've only used Pact for Spanish, and so have only written a
  lookup module for monolingual Spanish lookups (in
  `./pact/plugins/lookup/spanish/es_thefreedictionary.py`), but one
  with Python coding experience should be able to implement other
  dictionary web lookups.

While I haven't needed it myself, Pact _should_ allow for simple
plugins for lookups.  See ./pact/plugins/lookup/README.md.

If you have a plugin that has the correct function available, you
should be able to place it in `./myplugins` or in the `plugins`
folder, and then specify the module name in `config.ini`.

Only use plugins you trust, or that you write yourself ... since they
execute arbitrary code, they might be malicious etc etc.
Unfortunately it's not easy to sandbox them (so that they can only do
"safe" things).

## Running

Start it from the command line:

In top-level dir, after installing all dependencies:

```
python3 -m venv .venv
source .venv/bin/activate

python main.py

deactivate
```

or (tested on Mac):

```
./pact.sh
```

## Using

Open an mp3 file and a .txt translation file, and start making bookmarks.

TODO: create a YouTube video or similar to demonstrate usage.

### Saving

`Menu > File > Save session` saves the currently loaded files (mp3 and
transcription) and any defined bookmarks to disk.  Then later, you can
reload that session with `Menu > File > Open session` and continue.

This is useful when you're working with longer podcasts etc.

The session file (`.pact`) is just json, so if needed you can open the
file in an editor and update it, e.g. if the mp3 or transcription
files have moved or been renamed.

### GUI Hotkeys

#### Main window

* `<Command-p>`: Play/pause

* `<Right>`: Advance slider 100 ms
* `<Left>`: Move slider back 100 ms
* `<Command-Right>`: Advance slider 1000 ms
* `<Command-Left>`: Move slider back 1000 ms

* `<m>`: Add bookmark
* `<u>`: Update selected bookmark to slider position
* `<d>`: Delete selected bookmark
* `<Up>`: Select previous bookmark
* `<Down>`: Select next bookmark

* `<Return>`: Popup clip window for selected bookmark

#### Clip editor popup

* `<Command-p>`: Play/pause full clip
* `<Command-r>`: Reset the slider to 0

* `<Right>`: Advance slider 100 ms
* `<Left>`: Move slider back 100 ms
* `<Command-Right>`: Advance slider 1000 ms
* `<Command-Left>`: Move slider back 1000 ms

* `<Command-s>`: Set the clip start
* `<Command-e>`: Set the clip end
* `<Command-Shift-s>`: Move slider to clip start
* `<Command-Shift-e>`: Move slider to clip end

* `<Command-l>`: Play clip between start and end
* `<Command-t>`: Transcribe clip

* `<Command-u>`: Lookup selected word using lookup plugin
* `<Command-x>`: Export clip and transcription to Anki
* `<Command-k>`: OK.  Close (and save) clip


# Dev notes

## TODOs

See `README_todo.md` and `README_dev_notes.md`.

## Dependencies

Adding/freezing:

```
pip3 install X
pip3 freeze > requirements.txt
```

## Dev config

Use `PACTCONFIG` env variable to use a different config file (e.g., for different Anki export deck, etc.):

```
PACTCONFIG=config-dev.ini ./pact.sh
```

### Extra config settings:

```
# Add this section
[Dev]

# Load this session file on start:
SessionFile = /path/to/some/file.clips

# Load this mp3 on start, if SessionFile not present
LoadFile = /path/to/file.mp3
```

## Unit tests

Are in `/test`.  Run them all with:

```
python -m unittest discover -s test
```

To run a single one matching a pattern, use `-k`:

```
python -m unittest discover -s test -k save_session
```

See `python -m unittest -h` for more flags.