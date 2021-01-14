from ._anvil_designer import MyJitsiTemplate
from anvil import *


class MyJitsi(MyJitsiTemplate):
  def __init__(self, room_name, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.room_name = room_name
    self.alreadyinit = 0
    # Any code you write here will run when the form opens.
    
  def form_show(self, **event_args):
    """This method is called when the HTML panel is shown on the screen"""
    if not self.alreadyinit:
      self.alreadyinit += 1
      self.call_js("initJitsi", "meet.jit.si", {"roomName": self.room_name, "height": 500,})


