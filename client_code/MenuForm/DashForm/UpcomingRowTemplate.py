from ._anvil_designer import UpcomingRowTemplateTemplate
from anvil import *
import anvil.facebook.auth
import anvil.users
import anvil.server
import anvil.tz
import datetime
from ... import helper as h
from ...portable import DURATION_TEXT
from ...Name import Name


class UpcomingRowTemplate(UpcomingRowTemplateTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    
    # Any code you write here will run when the form opens.
    self.init()

  def init(self):
    # assumes only dyads allowed
    self.users_flow_panel.add_component(Name(item=self.item.pop('port_users')[0].__dict__))
    self.item['duration'] = DURATION_TEXT[self.item.pop('duration_minutes')]
    self.item['start_time'] = h.day_time_str(self.item.pop('start_date'))
    self.top_form = get_open_form()

  def update_dash(self, state):
    self.top_form.content.update_status(state)
      
  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if confirm("Are you sure you want to cancel this upcoming empathy exchange?"):
      self.update_dash(anvil.server.call('cancel_match',
                                         self.item['match_id']))

