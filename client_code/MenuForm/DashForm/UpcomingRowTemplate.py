from ._anvil_designer import UpcomingRowTemplateTemplate
from anvil import *
import anvil.server
import anvil.tz
import datetime
from ...timeproposals import DURATION_TEXT


class UpcomingRowTemplate(UpcomingRowTemplateTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    
    # Any code you write here will run when the form opens.
    self.init()

  def init(self):
    time = self.item['prop_time']
    if self.item['own']:
      self.item['users'] = time['users_accepting']
    self.item['duration'] = DURATION_TEXT[time.duration]
    start = time.start_date.astimezone(anvil.tz.tzlocal())
    self.item['start_time'] = start.strftime("%a, %b %d %I:%M%p")
    self.top_form = get_open_form()

  def update_dash(self, state):
    self.top_form.content.update_status(state)
      
  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.update_dash(anvil.server.call('cancel', 
                                       self.item['prop_time'].time_id))

