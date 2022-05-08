import os
from tkinter import Tk
import pact.app


def get_config():
    filename = os.environ.get('PACTCONFIG', 'config.ini')
    if not os.path.exists(filename):
        print(f'\nMissing required config file {filename}, quitting.\n')
        sys.exit(1)
    config = pact.app.Config.from_file(filename)
    return config


root = Tk()
config = get_config()
app = pact.app.MainWindow(root, config)
root.mainloop()
