from ._anvil_designer import MyGroupSettingsTemplate
from anvil import *
import anvil.server
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
      out, edit_form = self._edit_name_alert()
      if out is True:
        self.group['name'] = edit_form.item['text']
        self.group.relay('save_settings')
        self.update()
        self.my_groups_menu.update_drop_down()
      elif (self.group['name'] in ['', self.group.default_name]
            and not self.group.invites
            and not self.group.members):
        anvil.server.call('delete_group', self.group)
        # self.group.relay('delete')
        glob.my_groups.relay('load')
        self.my_groups_menu.reset()

  def form_show(self, **event_args):
    """This method is called when the column panel is shown on the screen"""
    pass  
      
  def update(self):
    self.refresh_data_bindings()
    
  def edit_name_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    out, edit_form = self._edit_name_alert()
    if out is True:
      self.group['name'] = edit_form.item['text']
      self.group.relay('save_settings')
      self.update()
      self.my_groups_menu.update_drop_down()
    # elif (self.group['name'] in ['', self.group.default_name]
    #       and not self.group.invites
    #       and not self.group.members):
    #   # self.group.relay('delete')
    #   glob.my_groups.relay('load')
    #   self.my_groups_menu.reset()

  def _edit_name_alert(self):
    disallowed_list = glob.my_groups.names_taken + ["", self.group.default_name]
    if self.group['name'] in disallowed_list and self.group['name'] != self.group.default_name:
      disallowed_list.remove(self.group['name'])
    name_item = {'text': self.group['name'],
                 'disallowed_list': disallowed_list,
                }
    edit_form = TextBoxEdit(item=name_item)
    out = alert(content=edit_form,
                title="Edit Name",
                large=False,
                dismissible=False,
                buttons=[])
    return out, edit_form
  
  def button_invite_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.group.relay('create_invite')
    self.update()


