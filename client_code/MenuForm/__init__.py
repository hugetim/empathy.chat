from ._anvil_designer import MenuFormTemplate
from anvil import *
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
from .. import parameters as p
from .. import helper as h
import random


class MenuForm(MenuFormTemplate):
  def __init__(self, **properties):
    # You must call self.init_components() before doing anything else in this function
    self.init_components(**properties)
  
    # 'prune' initializes new users to trust level 0 (via '_get_user_info')
    self.confirming_wait = False
    tm, pe, rt, s, sl, tallies, e, n = anvil.server.call('init')
    if e == False:
      alert('This account is not yet authorized to match with other users. '
            + 'Instead, it can be used to test things out. Your actions will not impact '
            + 'or be visible to other users. '
            + 'For help, contact: ' + p.CONTACT_EMAIL,
            dismissible=False)
    elif e == True:
      alert("Welcome, " + n + "!")
    self.name = n
    self.test_mode.visible = tm
    self.pinged_em_checked = pe
    self.tallies = tallies
    self.request_type = rt
    self.set_test_link()
    self.set_seconds_left(s, sl)
    self.reset_status()

### Code that doesn't really belong here, but pending moving it ###
  def set_seconds_left(self, new_status=None, new_seconds_left=None):
    """Set status and related time variables"""
    self.last_5sec = h.now()
    if new_status and new_status != "matched":
      self.seconds_left = new_seconds_left
      if self.status == "pinging" and new_status == "requesting":
        self.seconds_left = max(self.seconds_left, p.BUFFER_SECONDS)
    #print('before status change: ', self.seconds_left)
    self.status = new_status

  def request_button_click(self, request_type):
    self.request_type = request_type
    s, sl, num_emailed = anvil.server.call('add_request', self.request_type)
    self.set_seconds_left(s, sl)
    self.reset_status()
    if self.status == "requesting" and num_emailed > 0:
      self.emailed_notification(num_emailed).show()
    
  def emailed_notification(self, num):
    """Return Notification (assumes num>0)"""
    if num == 1:
      message = ('Someone has been sent a '
                 + 'notification email about your request.')
      headline = 'Email notification sent'
    else:
      message = (str(num) + ' others have been sent '
                 + 'notification emails about your request.')
      headline = 'Email notifications sent'
    return Notification(message,
                        title=headline,
                        timeout=10)

  def complete_button_click(self):
    self.set_seconds_left(None)
    self.tallies = anvil.server.call('match_complete')
    self.reset_status()   
        
  def confirm_wait(self):
    s, sl, self.tallies = anvil.server.call('confirm_wait')
    self.set_seconds_left(s, sl)
    self.reset_status()

  def reset_status(self):
    """Update form according to current state variables"""
    if self.status in ["requesting", "pinged", "pinging"]:
        self.go_wait()
    elif self.status == "matched":
        self.go_match()
    else:
      assert not self.status
      self.go_dash() 
###                                                                 ###
  def clear_page(self):
    self.nav_panel.visible = True
    self.test_link.visible = True 
    for link in self.nav_panel.get_components():
      link.role = ""
    self.content_column_panel.clear()
      
  def load_component(self, content):
    """Reset MenuForm and load content form"""
    self.clear_page()
    self.content = content
    self.content_column_panel.add_component(self.content)  
    
  def go_dash(self):
    self.title_label.text = "Dashboard"
    self.load_component(DashForm(self.name, self.tallies))
    self.home_link.role = "selected"

  def go_match(self):
    self.title_label.text = "Chat"
    self.nav_panel.visible = False
    self.test_link.visible = False
    self.load_component(MatchForm())

  def go_wait(self):
    self.title_label.text = "Chat"
    self.nav_panel.visible = False
    self.test_link.visible = False
    self.load_component(WaitForm(self.pinged_em_checked))

  def go_connections(self):
    self.title_label.text = "Connections"
    self.load_component(ConnectionsMenu())
    self.connections_link.role = "selected"   

  def go_groups(self):
    self.title_label.text = "Groups"
    self.load_component(GroupsMenu())       
    self.groups_link.role = "selected"
    
  def go_my_groups(self):
    self.title_label.text = "My Groups"
    self.load_component(MyGroupsForm())   
    self.my_groups_link.role = "selected" 
    
  def go_profile(self):
    self.title_label.text = "My Profile"
    self.load_component(UserMenu()) 
    self.profile_link.role = "selected"   
    
  def go_settings(self):
    self.title_label.text = "Settings"
    self.load_component(SettingsForm())
    self.settings_link.role = "selected"

  def home_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.go_dash()
    
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

  def test_request_button_click(self, **event_args):
    user_id = self.test_requestuser_drop_down.selected_value
    requesttype = self.test_requesttype_drop_down.selected_value
    if user_id and requesttype:
      anvil.server.call('test_add_request', user_id, requesttype)
    else:
      alert("User and request type required to add request.")

  def test_clear_click(self, **event_args):
    anvil.server.call('test_clear')
    self.test_requestuser_drop_down_refresh()

  def test_requestuser_drop_down_refresh(self):
    out = anvil.server.call('test_get_user_list')
    self.test_requestuser_drop_down.items = out

  def test_other_action_click(self, **event_args):
    action = self.test_other_action_drop_down.selected_value
    user_id = self.test_requestuser_drop_down.selected_value
    anvil.server.call(action, user_id)
