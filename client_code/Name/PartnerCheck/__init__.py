from ._anvil_designer import PartnerCheckTemplate
from anvil import *
from ... import parameters as p


class PartnerCheck(PartnerCheckTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.label_1.tooltip = f"This user has confirmed ownership of an external web site profile, thus verifying their name."
