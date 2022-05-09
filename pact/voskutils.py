from pydub import AudioSegment
from pydub import playback
from tempfile import NamedTemporaryFile
from vosk import Model, KaldiRecognizer, SetLogLevel
import json
import os
import sys
import tkinter
import wave

SetLogLevel(-1)


class TranscriptionCallback:
    """Called during transcribe_wav()."""

    def __init__(
            self,
            on_update_transcription = None,
            on_update_progress = None,
            on_finished = None
    ):
        super()
        self._totalbytes = 100
        self._bytesread = 0
        self._pct = 0
        self._last_pct = 0

        # Callback when transcription is updated.
        self.on_update_transcription = on_update_transcription

        # Callback when progress increases by 10%
        self.on_update_progress = on_update_progress

        # When done.
        self.on_finished = on_finished

        self.current_partial_result = None

        # Vosk returns 'partial results' as it processes, but then
        # each individual sentence (as best as Vosk can determine)
        # is returned as a 'result', or a 'final result'.
        self.sentences = []

        self.should_be_stopped = False

    def totalbytes(self, t):
        # print(f'About to read {t}')
        self._totalbytes = t

    def bytesread(self, b):
        self._bytesread += b
        self._pct = int((self._bytesread / self._totalbytes) * 100)
        if self._pct - self._last_pct >= 10:
            self.alert_update()
            self._last_pct = self._pct
        if self.on_update_progress and not self.should_be_stopped:
            self.on_update_progress(self._pct)

    def transcription(self):
        base = '. '.join(self.sentences)
        all = [
            s for s in
            [ '. '.join(self.sentences), self.current_partial_result ]
            if s is not None and s != ''
        ]
        return '. '.join(all)

    def alert_update(self):
        if self.should_be_stopped:
            # print('stopped, no update')
            return
        if self.on_update_transcription:
            self.on_update_transcription(self.transcription())

    def partial_result(self, r):
        t = json.loads(r)
        self.current_partial_result = t.get('partial')

    def result(self, r):
        t = json.loads(r)
        self.sentences.append(t.get('text'))
        self.current_partial_result = None

    def final_result(self, r):
        self.result(r)
        self.alert_update()
        if self.on_finished:
            self.on_finished(self.transcription())
        # print()
        # print('done')

    def stop(self):
        self.should_be_stopped = True

    def should_stop(self):
        return self.should_be_stopped



def transcribe_wav(f, callback):
    """Transcrabe a .wav file, calling back to provide updates.
    ref https://github.com/alphacep/vosk-api/blob/master/python/example/test_simple.py
    """

    # Precondition for vosk.
    if not os.path.exists("model"):
        msg = "Missing vosk model directory, download from https://alphacephei.com/vosk/models and unpack as 'model' in the current folder."
        raise RuntimeError(msg)

    wf = wave.open(f, "rb")
    # print(f"channels: {wf.getnchannels()}")
    # print(f"width: {wf.getsampwidth()}")
    # print(f"comp type: {wf.getcomptype()}")
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
        print ("Audio file must be WAV format mono PCM.")
        wf.close()
        exit (1)

    model = Model("model")
    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)
    # rec.SetPartialWords(True)

    totalbytes = wf.getnframes() * wf.getsampwidth()
    callback.totalbytes(totalbytes)

    end_of_stream = False
    while not end_of_stream and not callback.should_stop():
        data = wf.readframes(4000)
        callback.bytesread(len(data))

        if len(data) == 0:
            end_of_stream = True
        if rec.AcceptWaveform(data):
            callback.result(rec.Result())
        else:
            callback.partial_result(rec.PartialResult())
    wf.close()

    if not callback.should_stop():
        callback.final_result(rec.FinalResult())


def transcribe_audiosegment(chunk, cb = TranscriptionCallback()):
    # Per https://github.com/jiaaro/pydub/blob/master/pydub/playback.py,
    # playback falls back to ffplay, so we'll assume that's what's being used.
    # In this case, pydub actually dumps content to a temp .wav file, and
    # then plays with that.
    # Since that's how we're playing it, just use that for vosk as well.
    chunk = chunk.set_channels(1)
    with NamedTemporaryFile("w+b", suffix=".wav") as f:
        chunk.export(f.name, format='wav')
        transcribe_wav(f.name, cb)


#############################
# Sample usage with callback.

def main():

    if len(sys.argv) < 2:
        print('Specify file, please.')
        sys.exit(1)

    f = sys.argv[1]
    song = AudioSegment.from_mp3(f)
    print("making chunk")
    duration = 5 * 1000  # ms
    chunk = song[:duration]

    cb = TranscriptionCallback(
        on_update_transcription = lambda s: print(f'Current: {s}'),
        on_update_progress = lambda n: print(f'{n}%'),
        on_finished = lambda s: print(f'Final: {s}')
    )
    transcribe_audiosegment(chunk, cb)

    print('done')

if __name__ == "__main__":
   main()
