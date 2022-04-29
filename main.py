from pygame import mixer
from tkinter import Tk
from pact import gui

root = Tk()
mixer.init()
app = gui.MainWindow(root)
root.mainloop()
