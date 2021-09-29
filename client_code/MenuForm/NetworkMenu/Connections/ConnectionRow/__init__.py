from ._anvil_designer import ConnectionRowTemplate
from anvil import *
from ..... import helper as h


class ConnectionRow(ConnectionRowTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.degree_label.text = h.add_num_suffix(self.item['distance'])

