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

[![A quick demo](./README-img.png?raw=true)](https://www.youtube.com/embed/ildGZXoe0Cg "A quick demo")

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

The pact app should open.  Then you can open an mp3 on your system, or
the file "pact/assets/pact.mp3", and click "Play".  If you can hear
audio, the basics are in place.

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

Note that some models are very large, and could be slow on your
system.  For example, the German model `vosk-model-de-0.21` is about 2
gigs.  When I used it on a brief German clip, the transcription was
accurate, but the loading was so slow as to be almost unusable.  With
the much smaller `vosk-model-small-de-0.15` (45 MB), the Vosk
transcription was still accurate enough to find the correct match in
the accompanying transcription.

_NB: Pact currently reloads the entire Vosk model on every
transcription; perhaps this could be convered to a one-time load.
This would only be useful for very large models._

#### Ankiconnect

This is an add-on for Anki.  See
[AnkiConnect add-on](https://ankiweb.nqet/shared/info/2055492159) on
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

# If SessionFile is set, load this bookmark
# (indexed from 0):
LoadBookmark = 7

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

## Releases

* Make sure all tests pass
* Update CHANGELOG.md, pact/_version.py
* Commit
* Tag (e.g. `git tag v0.2.0 1f0f2a6`)
* `git push origin <tagname>`


## Contributing

* fork the repo
* make a branch, make your changes
* ensure the unit tests all still pass.  Add tests as needed to increase coverage/stability
* push to your fork
* open a PR

For some ideas of stuff that might need work, see the [wiki](https://github.com/jzohrab/pact/wiki/).
