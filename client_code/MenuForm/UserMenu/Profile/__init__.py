from ._anvil_designer import ProfileTemplate
from anvil import *
import anvil.server
import anvil.users
from .NameEdit import NameEdit


class Profile(ProfileTemplate):
  item_keys = {'me', 'user_id', 'first', 'last', 'degree', 
               'seeking', 'how_empathy', 'profile'}
  
  def __init__(self, user_id="", **properties):
    # Set Form properties and Data Bindings.
    self.item = anvil.server.call('init_profile', user_id)
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.update()
    
  def update(self):
    self.name_label.text = self.item['first']
    if (self.item['me'] or (self.item['degree'] in {1, 2})):
      self.name_label.text += " " + self.item['last']
    self.refresh_data_bindings()

  def connections_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    get_open_form().go_connections(self.item['user_id'])

  def edit_name_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    name_item = {'first': self.item['first'],
                 'last': self.item['last'],
                 'edits': False,
                }
    name_edit_form = NameEdit(item=name_item)
    out = alert(content=name_edit_form,
                title="Edit Name",
                large=False,
                dismissible=False,
                buttons=[])
    if out is True:
      anvil.server.call('save_name', name_edit_form.item)
      self.update()

  def seeking_toggleswitch_change(self, **event_args):
    self.item['seeking']
    anvil.server.call('set_seeking_buddy', self.seeking_toggleswitch.checked)

