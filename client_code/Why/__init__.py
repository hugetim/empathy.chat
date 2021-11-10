import anvil.server
from ._anvil_designer import WhyTemplate


class Why(WhyTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    
  @property
  def tooltip(self):
    return self.link_1.tooltip
  
  @tooltip.setter
  def tooltip(self, value):
    self.link_1.tooltip = value
