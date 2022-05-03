import unittest
import sys
import os

sys.path.append(os.path.abspath(sys.path[0]) + '/../')
from pact.gui import SliderMarkersWidget

class TestSliderMarkersWidgetHelper(unittest.TestCase):

    def test_marker_in_middle(self):
        arrow = (0, 0, 10, 0, 5, 10)  # canvas coords for widget
        c = SliderMarkersWidget.coordinates_for_value(50, 0, 100, 500, arrow)
        center_pos = 500 / 2  # 50 is halfway of 0-100
        halfwidth = 5  # (10 - 0 / 2)

        expected_coords = (
            center_pos - halfwidth, 0,
            center_pos + halfwidth, 0,
            center_pos, 10
        )
        self.assertEqual(expected_coords, c, "'middle' of object is halfway along canvas")

    def test_marker_at_0(self):
        arrow = (0, 0, 10, 0, 5, 10)  # canvas coords for widget
        c = SliderMarkersWidget.coordinates_for_value(0, 0, 100, 500, arrow)

        expected_coords = (
            -5, 0,
            +5, 0,
            0, 10
        )
        self.assertEqual(expected_coords, c)

    def test_marker_at_end(self):
        arrow = (0, 0, 10, 0, 5, 10)  # canvas coords for widget
        c = SliderMarkersWidget.coordinates_for_value(100, 0, 100, 500, arrow)

        expected_coords = (
            500-5, 0,
            500+5, 0,
            500, 10
        )
        self.assertEqual(expected_coords, c)

    def test_marker_with_different_scale_values(self):
        arrow = (0, 0, 10, 0, 5, 10)  # canvas coords for widget
        c = SliderMarkersWidget.coordinates_for_value(2, 1, 5, 500, arrow)

        location = 0.25  # 2 is 0.25 along 1 to 5
        expected_coords = (
            500 * location - 5, 0,
            500 * location + 5, 0,
            500 * location, 10
        )
        self.assertEqual(expected_coords, c)
