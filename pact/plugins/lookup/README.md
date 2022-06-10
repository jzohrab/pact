# Lookup plugins.

The lookup should be a python script (.py) that defines a method,
'lookup(string)', and either returns a string, or None.

If it returns a string as the lookup result, this is shown in a popup text box.

If it returns None, nothing happens -- it assumes that a separate page
or app has been opened.

The plugin can do whatever it needs to get the result - scrap web
pages, call internal dictionaries, whatever.  But the script should be
self-contained.  It could even make a system call to do something, if
another lookup package is already installed on the client machine.

See `sample.py`
