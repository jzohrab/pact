# Pact - Python Audio Clip Tool

Summary: this lets you quickly extract audio clips from .mp3 files
(from podcasts, etc) with a transcription, and export it to Anki using
Ankiconnect.

mp3 playing and hacking is done using VLC and ffmpeg.

The transcription is done using
[Vosk](https://github.com/alphacep/vosk-api/tree/master/python).

If you also have a transcription file (in .txt format), it's searched
to find the best possible match using the Vosk transcription as a
starting point.  This is helpful because sometimes the Vosk
transcription is a bit off.

**NOTE: I've only run this (and tested it) on Mac ... I'm not sure how
it will behave on other OS's.**

## A quick demo

* TODO - YouTube video here
* TODO YouTube video in Pact wiki

## Installation

Installation has 2 parts: parts needed for Pact itself, and then parts needed for your particular use.

Part 1:

* [Get the code](#get-the-code)
* [Install VLC](#vlc)
* [Install ffmpeg](#ffmpeg)
* [Install python requirements](#install-python-requirements)
* [Test it out](#test-it-out)

Part 2:

* [Install a Vosk model](#vosk-model)
* [AnkiConnect](#ankiconnect)
* [Anki notes](#anki-notes)
* [Set up your config.ini](#config-ini)

### Install 1: Pact

#### Get the code

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

### VLC

Install VLC on your system.

Mac with homebrew:

```
brew install --cask vlc
```

Other OSs: ?

### ffmpeg

Install ffmpeg on your system.

For Mac with homebrew:

```
brew install ffmpeg
```

Other OSs: ?

### Install python requirements

```
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (some from other git repos, see requirements.txt)
.venv/bin/pip3 install -r requirements.txt

deactivate
```

or, on systems with bash (Mac etc):

```
./install-deps.sh
```

#### Test it out

At this point, you should be able to run pact:

```
./pact.sh
```

The pact app should open, and when you click "Play" you should hear
some audio.  If you can, the basics are in place.

### Install 2: Your stuff

#### Vosk model

Vosk uses a "language model" for offline audio transcription.

* Download the appropriate model from https://alphacephei.com/vosk/models

* Unzip it into a subdirectory under the main directory (a sibling to
  the `pact` directory).

For example, my directory structure looks like this:

```
LICENSE
README.md  # (this file)
...
- /model
    - /spanish
        Gr.fst
        HCLr.fst
        README   # (the Vosk model readme)
        disambig_tid.int
        ...
+ /pact
...
```

#### Ankiconnect

This is an add-on for Anki.  See
[https://ankiweb.nqet/shared/info/2055492159](AnkiConnect add-on) on
AnkiWeb.

See https://github.com/FooSoft/anki-connect#installation for possible
additional setup required.

#### Anki notes

You'll need a Note Type with separate fields for the audio file and
the transcription.  The names don't matter, because you specify that
in the `config.ini` file.

If you're going to leave the transcription blank -- e.g., if you
delete the transcription suggestions that `pact` provides using Vosk
-- the Transcription field can't be the first field in the Note type,
because Anki doesn't allow empty first fields.

See the [wiki](https://github.com/jzohrab/pact/wiki) for an Anki card
layout idea.

#### config.ini

Edit `config.ini` to match your setup.


## Plugins

### Lookup plugins

> Note: I've only used Pact for Spanish, but there are monolingual
  lookup modules for French and German as well, in
  ./pact/plugins/lookup/`.  One with Python coding experience
  should be able to implement other dictionary web lookups.

While I haven't needed it myself, Pact _should_ allow for simple
plugins for lookups.  See ./pact/plugins/lookup/README.md.

If you have a plugin that has the correct function available, you
should be able to place it in `./myplugins` or in the `plugins`
folder, and then specify the module name in `config.ini`.

Only use plugins you trust, or that you write yourself ... since they
execute arbitrary code, they might be malicious etc etc.
Unfortunately it's not easy to sandbox them (so that they can only do
"safe" things).

### Transcription plugins

Currently, Pact only has a transcription plugin for Vosk, but others
should be possible.  See ./pact/plugins/transcription/README.md.

## Usage

See the [pact wiki](https://github.com/jzohrab/pact/wiki).

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
python3 -m venv .venv
source .venv/bin/activate
python -m unittest discover -s test
deactivate
```

To run a single one matching a pattern, use `-k`:

```
python -m unittest discover -s test -k save_session
```

See `python -m unittest -h` for more flags.