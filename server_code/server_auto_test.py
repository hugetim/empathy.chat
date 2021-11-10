import unittest
from . import matcher as m
from . import parameters as p


class SecondsLeftTest(unittest.TestCase):
  def test_initial_requesting(self):
    self.assertEqual(m._seconds_left("requesting"), p.WAIT_SECONDS)
    

def server_auto_tests(verbosity=0):
  #unittest.main(exit=False)
  import sys
  test_modules = ['auto_test', 'server_auto_test']
  test = unittest.TestLoader().loadTestsFromNames(test_modules)
  unittest.TextTestRunner(stream=sys.stdout, verbosity=verbosity).run(test)
    