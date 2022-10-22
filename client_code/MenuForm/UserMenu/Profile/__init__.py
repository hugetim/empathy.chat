from ._anvil_designer import ProfileTemplate
from anvil import *
import anvil.server
from .... import helper as h
from .... import ui_procedures as ui
from .... import prompts
from .... import glob
from .... import invited_procedures as invited
from .... import portable as port
from .... import parameters as p
from .... import relationship as rel
from .... import network_controller as nc
from .NameEdit import NameEdit
from .TextAreaEdit import TextAreaEdit
from .Relationship import Relationship


class Profile(ProfileTemplate):
  """item attribute is a port.UserProfile"""
  trust_tooltip = p.TRUST_TOOLTIP
  
  def __init__(self, user_id="", **properties):
    # Set Form properties and Data Bindings.
    self.trust_level = glob.trust_level
    if not user_id:
      user_id = glob.logged_in_user_id
    self.item = glob.users[user_id]
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.star_button.tooltip = p.STAR_TOOLTIP
    self.relationship_repeating_panel.items = nc.get_relationships(user_id)
    self.relationship_flow_panel.visible = bool(self.relationship_repeating_panel.items)
    self.connections_seeking_flow_panel.visible = (self.connections_flow_panel.visible 
                                                   or self.seeking_switch.visible 
                                                   or self.seeking_label.visible)
    self.last_active_label.text = f"  Last Active: {self.item.last_active_str},"
    self.connections_button.text = "My Network" if self.item['me'] else "Buddies"
    self.column_panel_1.row_spacing = 0
    if self.item['url_confirmed']:
      self.web_page_link.tooltip = (
        f"{self.item['first']}'s ownership of an external web site profile "
        f"was confirmed on {self.item.url_confirmed_date_str}.\n"
        f"({rel.Relationship.PROFILE_URL_NOTE})"
      )
      self.web_page_alt_label.tooltip = self.web_page_link.tooltip
    
  def form_show(self, **event_args):
    """This method is called when the column panel is shown on the screen"""
    if self.item['distance'] > 2:
      get_open_form().content.connections_tab_button.visible = False
    self.update()
    
  def update(self):
    if not self.item['me']:
      get_open_form().title_label.text = f"{self.item['first']}'s Profile"
    self.name_label.text = self.item['name']
    self.degree_label.text = self.item.distance_str
    if self.item['status'] == "invite":
      self.degree_label.text += " (pending invite)"
    name_likes = ("I like" if self.item['me'] 
                  else self.item['first'] + " likes")
    self.how_empathy_label.text = f"How {name_likes} to receive empathy:"
    if self.item.profile_updated_dt:
      self.profile_text_area.tooltip = (
        f"last updated {self.item.profile_updated_date_str}"
      )
    self.refresh_data_bindings()

  def connections_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if self.item['me']:
      get_open_form().go_connections()
    else:
      get_open_form().content.go_connections()

  def message_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    get_open_form().content.go_history()
    get_open_form().content.content.message_textbox.scroll_into_view()

  def edit_name_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    name_item = {'first': self.item['first'],
                 'last': self.item['last'],
                }
    edit_form = NameEdit(item=name_item)
    out = alert(content=edit_form,
                title="Edit Name",
                large=False,
                dismissible=False,
                buttons=[])
    if out is True:
      anvil.server.call('save_name', edit_form.item)
      self.item['first'] = edit_form.item['first']
      glob.name = self.item['first']
      get_open_form().item['name'] = glob.name
      self.item['last'] = edit_form.item['last']
      self.item['name'] = f"{self.item['first']} {self.item['last']}"
      self.update()

  def seeking_toggleswitch_change(self, **event_args):
    anvil.server.call('set_seeking_buddy', self.item['seeking'])
    self.refresh_data_bindings()

  def edit_how_empathy_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    prompt = ('(e.g., "silent empathy," "wait until I request an empathy guess," '
              'or "feel free to interrupt with guesses")')
    area_item = {'prompt': prompt, 'text': self.item['how_empathy']}
    edit_form = TextAreaEdit(item=area_item)
    out = alert(content=edit_form,
                title="How do you like to receive empathy?",
                large=True,
                dismissible=False,
                buttons=[])
    if out is True:
      anvil.server.call('save_user_field', 'how_empathy', edit_form.item['text'])
      self.item['how_empathy'] = edit_form.item['text']
      self.update()

  def edit_profile_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    prompt = (
      "Please share your background with NVC and experience level exchanging empathy, in a few sentences.\n"
      "You could also share what you're looking for in an empathy buddy, "
      "things about you that others might relate to, or anything else you like. "
    )
    area_item = {'prompt': prompt, 'text': self.item['profile']}
    edit_form = TextAreaEdit(item=area_item)
    out = alert(content=edit_form,
                title="Edit Profile",
                large=True,
                dismissible=False,
                buttons=[])
    if out is True:
      anvil.server.call('save_user_field', 'profile', edit_form.item['text'])
      self.item['profile'] = edit_form.item['text']
      self.item.profile_updated_dt = h.now()
      self.update()

  def propose_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    state = anvil.server.call('get_state')
    top_form = get_open_form()
    top_form.reset_status(state)
    if state['status'] not in ["pinging", "matched"]:
      top_form.content.propose(specified_users=[self.item['user_id']])
    else:
      alert("Unable to propose exchange just now. Please try again later.")

  def unconnect_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if ui.disconnect_flow(self.item['user_id'], self.item['name']):
      get_open_form().go_connections()

  def connect_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if prompts.invite_dialog(port.User(name=self.item['name'], user_id=self.item['user_id']),
                             title="Connect to a phone buddy",):
      get_open_form().go_profile(self.item['user_id'])

  def confirm_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if invited.invited_dialog(port.User(name=self.item['name'], user_id=self.item['user_id'])):
      get_open_form().go_profile(self.item['user_id'])

  def star_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    self.item.toggle_starred()
    self.update()
