from ._anvil_designer import MyGroupSettingsTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from ....Dialogs.TextBoxEdit import TextBoxEdit
from .... import glob

class MyGroupSettings(MyGroupSettingsTemplate):
  def __init__(self, menu, **properties):
    # Set Form properties and Data Bindings.
    self.group = menu.selected_group
    self.my_groups_menu = menu
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    if not self.group['name']:
      self.group['name'] = self.group.default_name
      self.edit_name_button_click()

  def form_show(self, **event_args):
    """This method is called when the column panel is shown on the screen"""
    pass  
      
  def update(self):
    self.refresh_data_bindings()
    
  def edit_name_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    name_item = {'text': self.group['name'],
                 'disallowed_list': glob.my_groups.names_taken,
                }
    edit_form = TextBoxEdit(item=name_item)
    out = alert(content=edit_form,
                title="Edit Name",
                large=False,
                dismissible=False,
                buttons=[])
    if out is True:
      self.group['name'] = edit_form.item['text']
      self.group.relay('save_settings')
      self.update()
      self.my_groups_menu.update_drop_down()
    elif (self.group['name'] in ['', self.group.default_name]
          and not self.group.invites
          and not self.group.members):
      self.group.relay('delete')
      glob.my_groups.relay('load')
      self.my_groups_menu.reset()

  def button_invite_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.group.relay('create_invite')
    self.update()


