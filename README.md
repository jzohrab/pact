## Initial install and configuration

```
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies (some from other git repos, see requirements.txt)
.venv/bin/pip3 install -r requirements.txt

... work work work OR use use use

deactivate
```

TODO update this.  include:

* vosk model
* install and running
* ffmpeg???
* Anki note type and fields
* ankiconnect
* config.ini


## Running


In top-level dir, after installing all dependencies:

```
python3 -m venv .venv
source .venv/bin/activate

python main.py

deactivate
```

## GUI Hotkeys

### Main window

* `<Command-p>'`: Play/pause
* `<Right>`: Advance slider 100ms
* `<Left>`: Move slider back 100ms

* `<m>`: Add bookmark
* `<u>`: Update selected bookmark to slider position
* `<d>`: Delete selected bookmark
* `<Up>`: Select previous bookmark
* `<Down>`: Select next bookmark

* `<Return>`: Popup clip window for selected bookmark

### Clip editor popup

* `<Command-p>`: Play/pause clip
* `<Right>`: Advance slider 100ms
* `<Left>`: Move slider back 100ms
* `<Command-r>`: Reset the slider to 0

* `<Command-s>`: Set the clip start
* `<Command-e>`: Set the clip end
* `<Command-c>`: Play clip
* `<Command-t>`: Transcribe clip

* `<Command-x>`: Export clip and transcription to Anki
* `<Return>`: Close (and save) clip


# Dev notes

## TODOs

See README_todo.md

See also README_dev_notes.md

## Dependencies

Adding/freezing:

```
pip3 install X
pip3 freeze > requirements.txt
```

## Extra config settings

Preload an mp3 file during dev, add this to the config.ini:

```
[Dev]
LoadFile = /path/to/file.mp3
```