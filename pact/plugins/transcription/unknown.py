
class NeedsConfiguration:
    """Used if vosk not set up."""

    def start(
        self,

        # A Pydub audiosegment.
        audiosegment,

        # Callbacks:
        # Called if the transcription service offers on-the-fly updates.
        on_update_transcription = lambda s: print(f'Current transcription: {s}'),

        # Called if service alerts of progress.
        on_update_progress = lambda n: print(f'{n}%'),

        # Called when service returns full transcription.
        on_finished = lambda s: print(f'Final transcription: {s}')
    ):

        # Note: not just calling 'print' here, because when pact uses
        # this it sets on_finished to a lambda that updates the gui.
        on_finished('<transcription vosk model not configured, see README>')


    def stop(self):
        pass


#############################

def main():
    song = None # not used
    v = NeedsConfiguration()
    v.start(audiosegment = song)

if __name__ == "__main__":
   main()
