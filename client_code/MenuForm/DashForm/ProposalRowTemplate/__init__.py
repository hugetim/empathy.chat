from ._anvil_designer import ProposalRowTemplateTemplate
from anvil import *
import anvil.server
import anvil.tz
import datetime
from .... import timeproposals as t
from .... import helper as h


class ProposalRowTemplate(ProposalRowTemplateTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    
    # Any code you write here will run when the form opens.
    self.init()
    self.update()

  def init(self):
    time = self.item['prop_time']
    self.item.update({'time_id': time.time_id,
                      'duration': t.DURATION_TEXT[time.duration],
                      'expire_date': time.expire_date,
                     })
    if time.start_now:
      self.item['start_time'] = "now"  
    else:
      start = time.start_date.astimezone(anvil.tz.tzlocal())
      self.item['start_time'] = start.strftime("%a, %b %m %I:%M%p")
    self.item['expires_in'] = str(self.item['expire_date'] - h.now())
      
  def update(self):
    self.accept_button.visible = not self.item['own']
    self.renew_button.visible = self.item['own'] and self.item['start_time'] == "now"
    self.cancel_button.visible = self.item['own']

  def update_dash(self, *args):
    get_open_form().content.update_status(*args)
      
  def accept_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.update_dash(anvil.server.call('accept_proposal', 
                                       self.item['prop_time'].time_id))

  def renew_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.update_dash(anvil.server.call('confirm_wait'))

  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.update_dash(anvil.server.call('cancel', 
                                       self.item['prop_time'].time_id))
