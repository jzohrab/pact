# Lookup plugins.

The lookup should be a python script (.py) that defines a method,
'lookup(string)', and returns a string which is the lookup result.
The string result is then shown in a popup text box.

The plugin can do whatever it needs to get the result - scrap web
pages, call internal dictionaries, whatever.  But the script should be
self-contained.  It could even make a system call to do something, if
another lookup package is already installed on the client machine.

See `sample.py`
