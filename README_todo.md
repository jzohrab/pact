# TODO list


## MVP TODO (usable for me)

* move full clip load to main window, calc zero bounds and store
* on bookmark, automatically set clip start and end to nearest zero bounds (if any found and within reasonable range)
* auto-set transcription if bounds are set

* config file config.ini required at startup
* strip carriage returns in the json export of the transcription (from textbox)
* play clip using the regular player, so can stop it if you want, and see updates.
* transcribe on separate thread
* transcribe on thread shouldn't bomb if window closes during
* on play clip, if transcription is not there, add it.
* play clip on separate thread
* Change "Clip mm:ss - mm:ss" to show just the start time, if only that is set (Clip: "06m17.s - ?")
* If the start time is set after the end, set end to null
* When "Clip mm:ss - mm:ss" present, on click of time set slider.  then can adjust easily
* clicking "transcribe" re-transcribes existing
* need some kind of status update on export, "success" or similar.
* if exporting on thread, then gui update shouldn't cause seg fault.
* save the exported date with the clip
* if already exported, ask if want to re-export
* say "are you sure?" message if clip has been defined and transcribed
* add "export all" button on main form?
* change title.
* load button to menu
* remove all other menu things
* fresh checkout, install, build from scratch in new venv
* final README updates


## After MVP, possible pre-release

* save and import to load all bookmarks, current position
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

