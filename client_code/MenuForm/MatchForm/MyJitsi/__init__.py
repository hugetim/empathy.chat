from ._anvil_designer import MyJitsiTemplate
from anvil import *
import anvil.users
import anvil.server


class MyJitsi(MyJitsiTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    self.alreadyinit = 0
    # Any code you write here will run when the form opens.
    
  def form_show(self, **event_args):
    """This method is called when the HTML panel is shown on the screen"""
    if not self.alreadyinit:
      self.alreadyinit += 1
      domain = "8x8.vc" #"meet.jit.si"
      room_name = f"vpaas-magic-cookie-848c456481fc4755aeb61d02b9d9dab2/{self.item['room_name']}"
      self.call_js("initJitsi", domain, {"roomName": room_name, "height": "100%", "width": "100%",
                                         "userInfo": {"displayName": " "}}, self.item['room_name']) #self.item['name']
      