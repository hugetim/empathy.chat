from ._anvil_designer import HistoryTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables

class History(HistoryTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.timer_2.interval = 30
    self.chat_repeating_panel.items = [] # for len(old_items) in update_messages()
    new_items = anvil.server.call('update_history_form', self.item['user_id']) # for spinner
    self.update_messages(new_items)
    
  def form_show(self, **event_args):
    """This method is called when the HTML panel is shown on the screen"""
    self.top_form = get_open_form()
       
  def update(self): 
    new_items = anvil.server.call_s('update_history_form', self.item['user_id'])
    self.update_messages(new_items)

  def update_messages(self, message_list):
    old_items = self.chat_repeating_panel.items
    if len(message_list) > len(old_items):
      message_list[0]['new_day'] = True
      for i in range(1, len(message_list)):
        message_list[i]['new_day'] = (message_list[i]['time_stamp'].date() 
                                      != message_list[i-1]['time_stamp'].date())
      self.chat_repeating_panel.items = message_list
      self.call_js('scrollCardLong') 
  
  def timer_2_tick(self, **event_args):
    """This method is called approx. once every 5 seconds, checking for messages"""
    self.update() 

  def message_textbox_pressed_enter(self, **event_args):
    if self.message_textbox.text:
      temp = anvil.server.call('add_message', self.item['user_id'], message=self.message_textbox.text)
      self.message_textbox.text = ""
      self.update_messages(temp)
      self.call_js('scrollCardLong')

  