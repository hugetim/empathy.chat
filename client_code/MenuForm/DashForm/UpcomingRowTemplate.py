from ._anvil_designer import UpcomingRowTemplateTemplate
from anvil import *
import anvil.server
import anvil.tz
import datetime
from ... import helper as h
from ... import parameters as p
from ...portable import DURATION_TEXT, User
from ...Name import Name
from ... import exchange_controller as ec
from ... import glob


class UpcomingRowTemplate(UpcomingRowTemplateTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)
    
    # Any code you write here will run when the form opens.
    self.init()

  def init(self):
    other_user_ids = self.item.pop('other_user_ids')
    for u_id in other_user_ids:
      port_u = glob.users[u_id]
      self.users_flow_panel.add_component(Name(item=User(user_id=u_id, name=port_u.name)))
    self.item['duration'] = DURATION_TEXT[self.item.pop('duration_minutes')]
    self.start_dt = self.item.pop('start_date')
    self.item['start_time'] = h.day_time_str(h.as_local_tz(self.start_dt))
    self.top_form = get_open_form()
    self.show_join_button_if_time()
    self.note_1.text = self.item['note']
    self.refresh_data_bindings()

  def update_dash(self, state):
    self.top_form.content.update_status(state)
      
  def cancel_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if confirm("Are you sure you want to cancel this upcoming empathy exchange?"):
      self.update_dash(anvil.server.call('cancel_match',
                                         self.item['match_id']))

  def show_join_button_if_time(self):
    timedelta_left = self.start_dt - h.now()
    if timedelta_left.total_seconds() <= 60*p.START_EARLY_MINUTES:
      self.join_button.visible = True

  def join_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.update_dash(ec.join_exchange(self.item['match_id']))
