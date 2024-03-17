from ._anvil_designer import ATestFormTemplate
from anvil import *
import anvil.server
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files

class ATestForm(ATestFormTemplate):
    def __init__(self, **properties):
        # You must call self.init_components() before doing anything else in this function
        self.init_components(**properties)

        # Any code you write here will run when the form opens.

    def empathy_slider_1_change(self, **event_args):
        print(f"Current slider value {self.empathy_slider_1.value}")
