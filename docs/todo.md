# TODO list

## Most important ... -ish.

* any obvious bugfixes

* additional smoke test coverage (ref `test/test_app.py` comments)

* whatever fixes/changes are needed for Pact to work on other OSs

* perhaps related to fixes for OS's: the hotkeys in app.py are very
  Mac-specific.  It would be simple to create a "hotkeys.ini" config
  file, read at startup, that the user can edit to change their hotkey
  settings.

* packaging to release as application, and/or simplify installation
  for people?  This may require a lot of work, for things like better
  error handling/messaging, logging, etc.

## Other possible future TODOs

* some kind of status update on export, "success" or similar.
* if exporting on thread, then gui update shouldn't cause seg fault.
* save the exported date with the clip
* if already exported, ask if want to re-export
* on bookmark, automatically set clip start and end to nearest 'silent times' (if any found and within reasonable range)
* add "export all" button on main form to export anything not already exported.  Would need status feedback/window, pass/fail indication in bookmark list, and reporting on failures.
* hotkey fixes - https://mail.python.org/pipermail/python-list/2003-April/229647.html
* maybe "add note" to bookmark
* export clipped mp3 file to disk ?
* clip editor popup:
  * add double slider https://github.com/MenxLi/tkSliderWidget?
  * respect double slider on playback
  * add buttons to reposition the start and end of the slider values, respecting max, re-graph

