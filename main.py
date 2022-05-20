import os
from tkinter import Tk
import pact.app
import sys
import shutil


def must_exist(f):
    if not os.path.exists(f):
        print(f'\nMissing {f}, quitting.\n')
        sys.exit(1)


def copy_config_example():
    if not os.path.exists('config.ini'):
        print(f'\nCopying config.ini.example to config.ini')
        shutil.copy('config.ini.example', 'config.ini')


def get_config():
    use_config = os.environ.get('PACTCONFIG', 'config.ini')
    must_exist(use_config)
    config = pact.app.Config.from_file(use_config)
    return config


def actual_filename(f, optionaldir = None):
    if os.path.exists(f):
        return f
    ret = os.path.join(optionaldir, f)
    if os.path.exists(ret):
        return ret
    # Just return the original file, it's later checked with
    # must_exist.
    return f


def configure_from_args(app, args):
    if args.pact is not None:
        f = actual_filename(args.pact, args.dirname)
        must_exist(f)
        app.load_pact_file(f)
    elif args.mp3 is not None:
        f = actual_filename(args.mp3, args.dirname)
        must_exist(f)
        app.load_mp3(f)


###############################

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--dirname", help="directory to search for files")
parser.add_argument("-p", "--pact", help="path to .pact file")
parser.add_argument("-m", "--mp3", help="path to .mp3 file")
args = parser.parse_args()


copy_config_example()
config = get_config()
root = Tk()
app = pact.app.MainWindow(root, config)

if config.has_section('Dev'):
    if args.pact or args.mp3:
        # Could get confusing if the Dev settings are set,
        # but the files are also set.
        print('\nPotential confusing configuration:')
        print('Config file [Dev] is set, but pact file or mp3 specified.')
        print('STOPPING, just in case of args confusion.\n')
        sys.exit(1)

    print('Loading dev configuration')
    app.init_dev()

else:
    # Setup using the provided flags.
    configure_from_args(app, args)


root.mainloop()
