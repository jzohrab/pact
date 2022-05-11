# Transcription

Currently Pact just supports transcription using Vosk, but it could
conceivably support different transcription types, such as Amazon
Transcribe, Deepgram, etc.

See `unknown.py` for the minimum API that a transcription plugin must
provide.

> Note: the "plugin" idea for transcription isn't complete
  ... currenty app.py just imports full modules from here rather than
  instantiating them from a factory.
