from ._anvil_designer import ProfileTemplate
from anvil import *
import anvil.server
import anvil.users
from .... import helper as h
from .NameEdit import NameEdit
from .TextAreaEdit import TextAreaEdit


class Profile(ProfileTemplate):
  item_keys = {'me', 'user_id', 'first', 'name', 'degree', 'degree_str',
               'seeking', 'how_empathy', 'profile'}
  
  def __init__(self, user_id="", **properties):
    # Set Form properties and Data Bindings.
    self.item = anvil.server.call('init_profile', user_id)
    self.init_components(**properties)

    # Any code you write here will run when the form opens.
    self.update()
    
  def update(self):
    if not self.item['me']:
      get_open_form().title_label.text = f"{self.item['first']}'s Profile"
    self.name_label.text = self.item['name']
    self.degree_label.text = h.add_num_suffix(self.item['degree'])
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