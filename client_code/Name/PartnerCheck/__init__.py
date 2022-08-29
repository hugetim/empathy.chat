from ._anvil_designer import PartnerCheckTemplate
from anvil import *
from ... import parameters as p


class PartnerCheck(PartnerCheckTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.label_1.tooltip = p.PARTNER_CHECK_TOOLTIP
