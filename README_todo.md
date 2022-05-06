# TODO list


## MVP TODO (usable for me)

* need some kind of status update on export, "success" or similar.
* if exporting on thread, then gui update shouldn't cause seg fault.
* save the exported date with the clip
* if already exported, ask if want to re-export

* on bookmark, automatically set clip start and end to nearest 'silent times' (if any found and within reasonable range)
* auto-set transcription if bounds are set

* config file config.ini required at startup

* add "export all" button on main form?
* fresh checkout, install, build from scratch in new venv
* final README updates

* session reload fails if mp3 file has moved ... should it? maybe add menu "reload session with current file"
* also fails if transcription file moved.

## After MVP, possible pre-release

* change version
* fix TODOs in README.md
* packaging?


## Future TODOs

* hotkey help - https://mail.python.org/pipermail/python-list/2003-April/229647.html
* maybe "add note" to bookmark?
* export clipped mp3 file to disk ?
* clip editor popup:
  * add double slider https://github.com/MenxLi/tkSliderWidget?
  * respect double slider on playback
  * add buttons to reposition the start and end of the slider values, respecting max, re-graph

