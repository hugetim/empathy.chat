from ._anvil_designer import ProposalRowTemplateTemplate
from anvil import *
import datetime
from .... import helper as h


class ProposalRowTemplate(ProposalRowTemplateTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.accept_button.visible = not self.item['own']
    self.renew_button.visible = self.item['own'] and self.item['start_time'] == "now"
    self.cancel_button.visible = self.item['own']
    self.item['expires_in'] = str(self.item['expire_date'] - h.now())