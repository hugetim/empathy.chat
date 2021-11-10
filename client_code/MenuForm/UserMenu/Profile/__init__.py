from ._anvil_designer import ProfileTemplate
from anvil import *
import anvil.server
import anvil.users
from .... import helper as h
from .... import ui_procedures as ui
from .... import prompts
from .... import glob
from .NameEdit import NameEdit
from .TextAreaEdit import TextAreaEdit
from .Relationship import Relationship


class Profile(ProfileTemplate):
  item_keys = {'me', 'user_id', 'first', 'last', 'name', 'degree', 'distance',
               'seeking', 'how_empathy', 'profile', 'trust_label', 'status'}
  trust_tooltip = {"Visitor": "Has not yet confirmed an email address",
                   "Guest": "Has not yet confirmed a phone number",
                   "Confirmed": "Has not yet matched with a Member who is a close connection",
                   "Member": ("Has confirmed an email address and phone number" 
                              "and matched with a Member who is a close connection"),
                   "Partner": "Confirmed url and has contributed at least a half hour's worth",
                   "Admin": "empathy.chat admin"
                  }
  def __init__(self, user_id="", **properties):
    # Set Form properties and Data Bindings.
    self.trust_level = glob.trust_level
    self.item = anvil.server.call('init_profile', user_id)
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.relationship_repeating_panel.items = self.item['relationships']
    
  def form_show(self, **event_args):
    """This method is called when the column panel is shown on the screen"""
    if self.item['distance'] > 1:
      get_open_form().content.connections_tab_button.visible = False
    self.update()
    
  def update(self):
    if not self.item['me']:
      get_open_form().title_label.text = f"{self.item['first']}'s Profile"
    self.name_label.text = self.item['name']
    self.degree_label.text = h.add_num_suffix(self.item['distance'])
    if self.item['status'] == "invite":
      self.degree_label.text += " (pending invite)"
    name_likes = ("I like" if self.item['me'] 
                  else self.item['first'] + " likes")
    self.how_empathy_label.text = f"How {name_likes} to receive empathy:"
    self.refresh_data_bindings()

  def connections_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if self.item['me']:
      get_open_form().go_connections()
    else:
      get_open_form().content.go_connections()

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
      self.item['last'] = edit_form.item['last']
      self.item['name'] = f"{self.item['first']} {self.item['last']}"
      self.update()

  def seeking_toggleswitch_change(self, **event_args):
    self.item['seeking']
    anvil.server.call('set_seeking_buddy', self.item['seeking'])

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
      anvil.server.call('save_user_item', 'how_empathy', edit_form.item['text'])
      self.item['how_empathy'] = edit_form.item['text']
      self.update()

  def edit_profile_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    prompt = ("What would meet a potential empathy buddy's need for trust? "
              "Share as much or as little as you'd like.")
    area_item = {'prompt': prompt, 'text': self.item['profile']}
    edit_form = TextAreaEdit(item=area_item)
    out = alert(content=edit_form,
                title="Edit Profile",
                large=True,
                dismissible=False,
                buttons=[])
    if out is True:
      anvil.server.call('save_user_item', 'profile', edit_form.item['text'])
      self.item['profile'] = edit_form.item['text']
      self.update()

  def propose_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    state = anvil.server.call('get_status')
    top_form = get_open_form()
    top_form.reset_status(state)
    if state['status'] not in ["pinging", "matched"]:
      top_form.content.propose(specified_users=[self.item['user_id']])
    else:
      alert("Unable to propose exchange just now. Please try again later.")

  def unconnect_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if ui.disconnect_flow(self.item['user_id'], self.item['name']):
      get_open_form().go_profile(self.item['user_id'])

  def connect_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    if prompts.invite_dialog(self.item['name'], self.item['user_id']):
      get_open_form().go_profile(self.item['user_id'])

  def confirm_button_click(self, **event_args):
    """This method is called when the button is clicked"""
    invited_item = anvil.server.call('invited_item', self.item['user_id'])
    if prompts.invited_dialog(**invited_item):
      get_open_form().go_profile(self.item['user_id'])


