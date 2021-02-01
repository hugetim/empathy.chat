from ._anvil_designer import MenuFormTemplate
from anvil import *
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.server
import anvil.users
from .DashForm import DashForm
from .WaitForm import WaitForm
from .MatchForm import MatchForm
from .ConnectionsMenu import ConnectionsMenu
from .GroupsMenu import GroupsMenu
from .MyGroupsForm import MyGroupsForm
from .UserMenu import UserMenu
from .SettingsForm import SettingsForm
from .DashForm.CreateForm import CreateForm
from .. import parameters as p
from .. import helper as h
from .. import portable as t
import unittest
import random
import time


class MenuForm(MenuFormTemplate):
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
  
    # 'prune' initializes new users to trust level 0 (via '_get_user_info')
    e = self.item['email_in_list']
    n = self.item['name']
    if e == False:
      alert('This account is not yet authorized to match with other users. '
            + 'Instead, it can be used to test things out. Your actions will not impact '
            + 'or be visible to other users. '
            + 'For help, contact: ' + p.CONTACT_EMAIL,
            dismissible=False)
    elif e == True:
      alert("Welcome, " + n + "!")
    self.test_mode.visible = self.item['test_mode']
    self.set_test_link()
    self.reset_status(self.item['state'])

  def reset_status(self, state):
    """Update form according to current state variables"""
    if state['status'] in ["pinging"]:
      self.go_wait(state)
    elif state['status'] == "matched":   
      self.go_match(state)
    else:
      assert state['status'] in [None, "requesting", "pinged"]
      self.go_dash(state) 

  def clear_page(self):
    self.link_bar_home.visible = True
    self.link_bar_profile.visible = True
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
    self.title_label.text = "Chat"
    self.link_bar_home.visible = False
    self.link_bar_profile.visible = False
    self.nav_panel.visible = False
    self.test_link.visible = False
    item = {k: state[k] for k in MatchForm.state_keys}
    self.reset_and_load(MatchForm(item=item))

  def go_wait(self, state):
    self.title_label.text = "Chat"
    self.link_bar_home.visible = False
    self.link_bar_profile.visible = False
    self.nav_panel.visible = False
    self.test_link.visible = False
    item = {k: state[k] for k in WaitForm.state_keys}
    self.reset_and_load(WaitForm(item=item))

  def go_connections(self):
    self.title_label.text = "My Connections"
    self.reset_and_load(ConnectionsMenu())
    self.connections_link.role = "selected"   

  def go_groups(self):
    self.title_label.text = "Groups"
    self.reset_and_load(GroupsMenu())       
    self.groups_link.role = "selected"
    
  def go_my_groups(self):
    self.title_label.text = "My Groups"
    self.reset_and_load(MyGroupsForm())   
    self.my_groups_link.role = "selected" 
    
  def go_profile(self):
    self.title_label.text = "My Profile"
    self.reset_and_load(UserMenu()) 
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
    num_chars = 4
    charset = "abcdefghijkmnopqrstuvwxyz23456789"
    random.seed()
    rand_code = "".join([random.choice(charset) for i in range(num_chars)])
    code = "test-" + rand_code
    self.test_link.url = "https://meet.jit.si/" + code
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
    content = CreateForm(item=t.Proposal().create_form_item())
    self.proposal_alert = content
    out = alert(content=self.proposal_alert,
                title="New Empathy Chat Proposal",
                large=True,
                dismissible=False,
                buttons=[])
    if user_id and out is True:
      proposal = content.proposal()
      if (not proposal.times[0].start_now) or len(proposal.times)>1:
        alert(title='"later" proposals not implemented yet')
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
    run_tests()

class TestNow(unittest.TestCase):

  def setUp(self):
    self.top_form = get_open_form()
    self.top_form.home_link_click()

  def test_repeat_now_proposal(self):
    for email, user_id in self.top_form.test_requestuser_drop_down.items:
      if email == "A":
        accept_user_id = user_id
    while True:
      anvil.server.call('add_now_proposal')
      time.sleep(15)
      anvil.server.call('accept_now_proposal', user_id=accept_user_id)
      time.sleep(5)
      anvil.server.call('cancel', user_id=accept_user_id)
      time.sleep(5)
      anvil.server.call('cancel')


def run_tests():
  #unittest.main()
  #print("run manually")
  test = TestNow()
  test.setUp()
  test.test_repeat_now_proposal()
