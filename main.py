from pygame import mixer
from tkinter import Tk
from pact import player

root = Tk()
mixer.init()
app = player.MainWindow(root)
root.mainloop()
