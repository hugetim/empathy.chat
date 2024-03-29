from ._anvil_designer import MyGroupsMenuTemplate
from anvil import *
import anvil.server
from .MyGroupSettings import MyGroupSettings
from .MyGroupMembers import MyGroupMembers
from ... import parameters as p
from ... import glob
from ... import relationship as rel
from ..UserMenu.Profile.TextAreaEdit import TextAreaEdit


class MyGroupsMenu(MyGroupsMenuTemplate):
  def __init__(self, **properties):
    # Set Form properties and Data Bindings.
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    if glob.trust_level >= 4:
      self.reset()
    else:
      self.my_groups_panel.visible = False
      self.populate_partner_criteria_panel()
      self.partner_criteria_panel.visible = True

  @property
  def selected_group(self):
    return self.groups_drop_down.selected_value
    
  def reset(self):
    self.update_drop_down()
    if glob.my_groups:
      self.go_group_settings()
    for component in [self.groups_drop_down, self.tabs_flow_panel, self.content_column_panel]:
      component.visible = glob.my_groups

  def update_drop_down(self):
    self.groups_drop_down.items = [(g['name'], g) for g in glob.my_groups]

  def groups_drop_down_change(self, **event_args):
    """This method is called when an item is selected"""
    self.content.group = self.groups_drop_down.selected_value
    self.content.update()
    
  def create_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    glob.my_groups = anvil.server.call('add_my_group', glob.my_groups)
    self.groups_drop_down.selected_value = glob.my_groups[-1]
    self.reset()
      
  def clear_page(self):
    for button in self.tabs_flow_panel.get_components():
      button.background = p.NONSELECTED_TAB_COLOR
      button.role = ""
    self.content_column_panel.clear()

  def select_tab_button(self, button):
    button.background = p.SELECTED_TAB_COLOR
    button.role = "raised"
  
  def load_component(self, content):
    """Reset MenuForm and load content form"""
    self.clear_page()
    self.content = content
    self.content_column_panel.add_component(self.content)

  def go_group_settings(self):
    content = MyGroupSettings(menu=self)
    self.load_component(content)
    self.select_tab_button(self.group_settings_tab_button)

  def go_members(self):
    content = MyGroupMembers(menu=self)
    self.load_component(content)
    self.select_tab_button(self.members_tab_button)
    
  def group_settings_tab_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.go_group_settings()

  def members_tab_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.go_members()

  def invites_tab_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    pass

  def populate_partner_criteria_panel(self):
    self.item = anvil.server.call('get_partner_criteria_info')
    url_confirmed = bool(self.item['url_confirmed_date'])
    self.identity_check_label.icon = "fa:check-square-o" if url_confirmed else "fa:square-o"
    self.url_text_box.text = self.item['profile_url']
    if url_confirmed:
      self.url_text_box.enabled = False
      self.submit_url_button.visible = False
    elif not self.url_text_box.text:
      self.submit_url_button.enabled = False
    self.profile_url_note_label.text = f"({rel.Relationship.PROFILE_URL_NOTE})"
    self.contributor_check_label.icon = "fa:check-square-o" if self.item['contributor'] else "fa:square-o"
    if self.item['contributor']:
      self.explain_contribution_button.visible = False
      
  def url_text_box_change(self, **event_args):
    """This method is called when the text in this text box is edited"""
    self.submit_url_button.enabled = self.url_text_box.text

  def submit_url_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    anvil.server.call('submit_url_for_review', self.url_text_box.text)
    Notification("Profile link submitted").show()
    self.submit_url_button.enabled = False

  def explain_contribution_button_click(self, **event_args):
    """This method is called when the link is clicked"""
    prompt = ('If you have already contributed in some way, but the "Contribute" box is not yet checked, please explain how you have contributed below. '
              'Tim will follow up by email as needed.')
    area_item = {'prompt': prompt, 'text': ""}
    edit_form = TextAreaEdit(item=area_item)
    out = alert(content=edit_form,
                title="Submit description of your contribution",
                large=True,
                dismissible=False,
                buttons=[])
    if out is True:
      anvil.server.call('submit_contribution_desc', edit_form.item['text'])
      Notification("Contribution description submitted").show()
      self.explain_contribution_button.enabled = False
