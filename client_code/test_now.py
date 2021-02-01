from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.server
import unittest
from .MenuForm import MenuForm
from .MenuForm.DashForm import DashForm


class TestNow(unittest.TestCase):

  def setUp(self):
    self.top_form = get_open_form()
    self.top_form.go_dash()

  def test_add_my_now_proposal(self):
    self.top_form.content.propose_button_click()
    focused_component = get_focused_component()
    print(focused_component.__dict__())
    #self.assertEqual( multiply(3,4), 12)


def run_tests():
  unittest.main()