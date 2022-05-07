# TODO list

## MVP TODO

* session reload fails if mp3 file has moved, or transcription moved ... continue to load, but with big warning.
* change version
* record simple YouTube video of usage, update link in README.
* fix TODOs in README.md

## Possible future TODOs

* add tags to exported file (set at the top window)
* fresh checkout, install, build from scratch in new venv

* packaging to release as application?
* some kind of status update on export, "success" or similar.
* if exporting on thread, then gui update shouldn't cause seg fault.
* save the exported date with the clip
* if already exported, ask if want to re-export
* on bookmark, automatically set clip start and end to nearest 'silent times' (if any found and within reasonable range)
* auto-set transcription if bounds are set
* add "export all" button on main form?

* hotkey help - https://mail.python.org/pipermail/python-list/2003-April/229647.html
* maybe "add note" to bookmark
* export clipped mp3 file to disk ?
* clip editor popup:
  * add double slider https://github.com/MenxLi/tkSliderWidget?
  * respect double slider on playback
  * add buttons to reposition the start and end of the slider values, respecting max, re-graph

