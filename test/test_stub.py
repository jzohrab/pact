import unittest
import sys
import os

sys.path.append(os.path.abspath(sys.path[0]) + '/../')


class TestStub(unittest.TestCase):

    def setUp(self):
        pass

    def test_stub(self):
        self.assertEqual(2, 2)


if __name__ == '__main__':
    unittest.main()
