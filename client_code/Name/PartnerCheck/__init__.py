from ._anvil_designer import PartnerCheckTemplate
from anvil import *


class PartnerCheck(PartnerCheckTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    @property
    def visible(self):
      return self.label_1.visible
    
    @visible.setter
    def visible(self, value):
      self.label_1.visible = value
