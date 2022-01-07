from ._anvil_designer import MenuFormTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.js
from .DashForm import DashForm
from .WaitForm import WaitForm
from .MatchForm import MatchForm
from .NetworkMenu import NetworkMenu
from .GroupsMenu import GroupsMenu
from .MyGroupsMenu import MyGroupsMenu
from .UserMenu import UserMenu
from .SettingsForm import SettingsForm
from .DashForm.CreateForm import CreateForm
from .. import parameters as p
from .. import helper as h
from .. import portable as t
from .. import auto_test
from .. import glob


class MenuForm(MenuFormTemplate):
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
    
    if glob.trust_level < 0:
      alert('This account is not yet authorized, but '
            + 'it can be used to test things out. Your actions will not impact '
            + 'or be visible to other users. '
            + 'For help, contact: ' + p.CONTACT_EMAIL,
            dismissible=False)
    else:
      self.set_help_link("https://www.loomio.org/join/group/G537YtVTZmNTW1S1KTJnDvUb/")
    self.connections_link.visible = glob.trust_level >= 2 # should only be for level 2 if have connections
    self.my_groups_link.visible = glob.trust_level >= 4
    self.test_mode.visible = self.item['test_mode']
    if p.DEBUG_MODE and self.item['test_mode']:
      auto_test.client_auto_tests()
    self.set_test_link()
    
  def form_show(self, **event_args):
    self.reset_status(self.item['state'])

  def set_help_link(self, url):
    self.side_help_link.url = url
    self.link_bar_help.url = url
    
  def reset_status(self, state):
    """Update form according to current state variables"""
    if state['status'] in ["pinging"]:
      self.go_wait(state)
    elif state['status'] in ["matched", "requesting", "pinged"]:   
      self.go_match(state)
    else:
      if state['status'] not in [None]:
        h.warning(f'{state["status"]} not in [None]')
      self.go_dash(state) 

  def clear_page(self):
    self.link_bar_home.visible = True
#     self.link_bar_profile.visible = True
    self.nav_panel.visible = True
    self.test_link.visible = True 
    for link in self.nav_panel.get_components():
      link.role = ""
    self.content_column_panel.clear()
      
  def reset_and_load(self, content):
    """Reset MenuForm and load content form"""
    self.clear_page()
    self.content = content
    self.content_column_panel.add_component(self.content)  
    
  def go_dash(self, state):
    self.title_label.text = "Dashboard"
    item = {k: state[k] for k in DashForm.state_keys}
    self.reset_and_load(DashForm(item=item))
    self.home_link.role = "selected"

  def go_match(self, state):
#     from anvil.js.window import hideSidebar, hideAppbar
#     self.title_label.text = "Empathy Chat"
    item = {k: state[k] for k in MatchForm.state_keys}
    open_form(MatchForm(item=item))
#     self.reset_and_load(MatchForm(item=item))
#     self.link_bar_home.visible = False
#     self.link_bar_profile.visible = False
#     self.nav_panel.visible = False
#     self.test_link.visible = False
#     anvil.js.call(hideSidebar)
#     anvil.js.call(hideAppbar)
#     title_bar = document.getElementsByClassName("app-bar")[0]
#     title_bar.css("display", "none") #style.display = 'none'

  def go_wait(self, state):
    self.title_label.text = "Empathy Chat"
    item = {k: state[k] for k in WaitForm.state_keys}
    self.reset_and_load(WaitForm(item=item))
    self.link_bar_home.visible = False
#     self.link_bar_profile.visible = False
    self.nav_panel.visible = False
    self.test_link.visible = False
#     anvil.js.call(hideSidebar)

  def go_connections(self, user_id=""):
    if h.not_me(user_id):
      self.title_label.text = "" # other user's profile
      item = {'user_id': user_id, 'tab': 'connections'}
      self.reset_and_load(UserMenu(item=item)) 
    else:
      self.title_label.text = "My Connections"
      self.reset_and_load(NetworkMenu())
      self.connections_link.role = "selected"   

  def go_groups(self):
    self.title_label.text = "Groups"
    self.reset_and_load(GroupsMenu())       
    self.groups_link.role = "selected"
    
  def go_my_groups(self):
    self.title_label.text = "My Groups"
    self.reset_and_load(MyGroupsMenu())   
    self.my_groups_link.role = "selected" 
    
  def go_profile(self, user_id=""):
    if h.not_me(user_id):
      self.title_label.text = "" # other user's profile
      item = {'user_id': user_id, 'tab': 'profile'}
      self.reset_and_load(UserMenu(item=item)) 
    else:
      self.title_label.text = "My Profile"
      item = {'user_id': "", 'tab': 'profile'}
      self.reset_and_load(UserMenu(item=item)) 
      self.profile_link.role = "selected"    
  
  def go_settings(self):
    self.title_label.text = "Settings"
    self.reset_and_load(SettingsForm())
    self.settings_link.role = "selected"

  def home_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.reset_status(anvil.server.call('get_status'))
    
  def connections_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.go_connections()  
    
  def groups_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.go_groups()  
  
  def my_groups_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.go_my_groups()  
    
  def profile_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.go_profile()
  
  def settings_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.go_settings()
    
  def set_test_link(self):
    import random
    num_chars = 5
    charset = "abcdefghijkmnopqrstuvwxyz23456789"
    random.seed()
    rand_code = "".join([random.choice(charset) for i in range(num_chars)])
    code = "empathy-test-" + rand_code
    self.test_link.url = "https://meet.jit.si/" + code + "#config.prejoinPageEnabled=false"
    return code          
    
  def logout_button_click(self, **event_args):
    self.logout_user()
    
  def logout_user(self):
    anvil.users.logout()
    open_form('LoginForm')

  def test_mode_change(self, **event_args):
    """This method is called when this checkbox is checked or unchecked"""
    self.test_column_panel.visible = self.test_mode.checked
    if self.test_mode.checked:
      self.test_requestuser_drop_down_refresh()

  def test_adduser_button_click(self, **event_args):
    email = self.test_adduser_email.text
    if email:
      anvil.server.call('test_add_user', email)
      self.test_adduser_email.text = ""
      self.test_requestuser_drop_down_refresh()
    else:
      alert("Email address required to add user.")

  def test_proposal_button_click(self, **event_args):
    user_id = self.test_requestuser_drop_down.selected_value
    form_item = t.Proposal().create_form_item()
    content = CreateForm(item=form_item)
    self.proposal_alert = content
    out = alert(content=self.proposal_alert,
                title="New Empathy Chat Proposal",
                large=True,
                dismissible=False,
                buttons=[])
    if user_id and out is True:
      proposal = content.proposal()
      anvil.server.call('test_add_request', user_id, proposal)
    else:
      alert("User and saved proposal required to add request.")

  def test_clear_click(self, **event_args):
    anvil.server.call('test_clear')
    self.test_requestuser_drop_down_refresh()

  def test_requestuser_drop_down_refresh(self):
    out = anvil.server.call('test_get_user_list')
    self.test_requestuser_drop_down.items = out

  def test_other_action_click(self, **event_args):
    action = self.test_other_action_drop_down.selected_value
    user_id = self.test_requestuser_drop_down.selected_value
    anvil.server.call(action, user_id=user_id)

  def autotest_butten_click(self, **event_args):
    """This method is called when the button is clicked"""
    auto_test.run_now_test()

