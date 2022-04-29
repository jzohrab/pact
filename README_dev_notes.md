# Misc dev notes.

## The Bookmark/Clip editor window - possible future improvements

### Styling

I tried using ttk.scale for better styling, but it was garbage.  The
slider handle kept jumping out of the scale, and not respecting the
from_ and to values of the scale (e.g., for from_=2500 and to=4500, a
value of 3500 (right in the middle) would be shown about 75% along the
scale, and for higher values it would disappear completely).

ref
https://stackoverflow.com/questions/71994893/tkinter-ttk-scale-seems-broken-if-from-is-not-zero-mac-python-3-8-2-tcl-tk

### UI for clip selection

The current design is good enough -- I can define clips reasonably
quickly and easily.

I had tried to use a separate slider to define the "start and end" of
the clip, but it was a hassle.  The matplotlib chart of the waveform
didn't line up accurately with the slider position, and it just felt
inaccurate.  Using buttons and going by feel was better.

Ideally, the design/UI for this would be something like Audacity's
"clip selection", where the user clicks and drags a range on a plotted
chart of the audio waveform.  I tried various versions of this, but
couldn't get it to work reasonably:

#### Attempt 1: using axvspans on the chart.

In the plot() method, you can convert the bookmark clip bounds to the
corresponding axis positions on the chart, and then use axvspans:

```
# To shade a time span, we have to translate the time into the
# corresponding index in the signal array.
def signal_array_index(t_ms):
    span = self.to_val - self.from_val
    pct = (t_ms - self.from_val) / span
    return len(self.signal_plot_data) * pct

cs, ce = self.bookmark.clip_bounds_ms
if (cs is not None and ce is not None):
    shade_start = signal_array_index(cs)
    shade_end = signal_array_index(ce)
    self.axv = plot1.axvspan(shade_start, shade_end, alpha=0.25, color='blue')
```

I was hoping to use this to do on-the-fly updates of the chart as the
user dragged a slider bar, but the performance was terrible.

#### Attempt 2: using matplotlib.widgets.SpanSelector

Per
https://stackoverflow.com/questions/40325321/python-embed-a-matplotlib-plot-with-slider-in-tkinter-properly,
it appears that we can use the spanselector in tkinter, but when I
tried using the bare minimum code in this app's windows, it didn't
work ... the spanslider couldn't be selected.  Perhaps this is due to
grid being used, rather than pack ... not sure, didn't bother looking
further.

