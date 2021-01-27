from ._anvil_designer import UpcomingRowTemplateTemplate
from anvil import *
import anvil.server
import anvil.tz
import datetime
from ...portable import DURATION_TEXT


class UpcomingRowTemplate(UpcomingRowTemplateTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    
    # Any code you write here will run when the form opens.
    self.init()

  def init(self):
    # assumes only dyads allowed
    self.item['users'] = self.item.pop('port_users')[0].name
    self.item['duration'] = DURATION_TEXT[self.item.pop('duration_minutes')]
    start = self.item.pop('start_date').astimezone(anvil.tz.tzlocal())
    self.item['start_time'] = start.strftime("%a, %b %d %I:%M%p")
    self.top_form = get_open_form()

  def update_dash(self, state):
    self.top_form.content.update_status(state)
      
  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.update_dash(anvil.server.call('cancel_match', 
                                       self.item['match_id']))

