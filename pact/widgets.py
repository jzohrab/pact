class SliderMarkersWidget:

    @staticmethod
    def coordinates_for_value(val, minval, maxval, length, coords):

        def chunks(l, n):
            n = max(1, n)
            return (l[i:i+n] for i in range(0, len(l), n))
        coordpairs = list(chunks(coords, 2))
        xcoords = [el[0] for el in coordpairs]

        width = max(xcoords) - min(xcoords)
        middle = width / 2.0
        shiftleft = min(xcoords) + middle


        # shift everything so that the middle is at zero
        middleatzero = [(c[0] - shiftleft, c[1]) for c in coordpairs]

        # Where there middle is actually supposed to go.
        placement = int(length * (val - minval) / (maxval - minval))

        # Shift the middle so that it's at placement
        final = [(c[0] + placement, c[1]) for c in middleatzero]

        # print(xcoords)
        # print(f'shifting by shiftleft = {shiftleft}')
        # print(f'shifted = {middleatzero}')
        # print(f'final = {final}')

        # This python flattening is mental.
        flattened = [item for sublist in final for item in sublist]
        return tuple(flattened)

    def __init__(self, canvas, width, minvalue, maxvalue):
        self.canvas = canvas
        self.width = width
        self.polygons = []
        self.minvalue = minvalue
        self.maxvalue = maxvalue

    def add_marker(self, value, polygon_coords, fill = "red"):
        adjusted_coords = SliderMarkersWidget.coordinates_for_value(
            value, self.minvalue, self.maxvalue, self.width, polygon_coords)
        p = self.canvas.create_polygon(adjusted_coords, fill=fill)
        self.polygons.append(p)

    def clear(self):
        for p in self.polygons:
            self.canvas.delete(p)
        self.polygons = []
