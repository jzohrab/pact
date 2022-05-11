import os
from tkinter import Tk
import pact.app
import sys
import shutil


def copy_config_example():
    if not os.path.exists('config.ini'):
        print(f'\nCopying config.ini.example to config.ini')
        shutil.copy('config.ini.example', 'config.ini')


def get_config():
    use_config = os.environ.get('PACTCONFIG', 'config.ini')
    if not os.path.exists(use_config):
        print(f'\nMissing config file {use_config}, quitting.\n')
        sys.exit(1)
    config = pact.app.Config.from_file(use_config)
    return config


copy_config_example()
config = get_config()

root = Tk()
app = pact.app.MainWindow(root, config)
app.load_mp3("demo/Python audio clip tool.mp3")
root.mainloop()
