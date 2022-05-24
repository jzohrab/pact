__version__ = "0.2.2"

# Get version changes via
# git log -- pact/_version.py

version_notes = """
0.2.3 (7d1f527): Show bookmark text, notes on main window

- layout change

0.2.2 (38697cc): Add navigation to natural splits in audio

- finding natural audio break points using ffmpeg
- added functional bulk-transcription module, though it's
  not actually included in pact itself yet

0.2.1 (4af3f26): Auto-create temp pact file

- opening mp3 creates a temp pact file, just in case.

0.2.0 (b699ad8): Clip notes

- allow lookup from notes textbox
- add notes textbox to clip window

0.1.2 (5276a01): Clip list display changes

0.1.1 (2e29895): Many small changes:

- export checkmarks
- main.py flags
- docs
- more tests
- lookup modules
- autosave
- bugfixes

0.1.0 (2d9dc14): Initial stable version:

- session files
- using transcriptions
- VLC and ffmpeg
- main app


0.0.0 (dfeb216): Initial commit

- copy of files over from another test project.
"""
