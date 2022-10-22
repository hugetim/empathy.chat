from ._anvil_designer import MenuFormTemplate
from anvil import *
import anvil.users
import anvil.server
import anvil.js
from .DashForm import DashForm
from .WaitForm import WaitForm
from ..MatchForm import MatchForm
from .NetworkMenu import NetworkMenu
from .MyGroupsMenu import MyGroupsMenu
from .UserMenu import UserMenu
from .SettingsForm import SettingsForm
from .DashForm.CreateForm import CreateForm
from .. import parameters as p
from .. import helper as h
from .. import portable as t
from .. import auto_test
from .. import glob
from ..network_controller import not_me


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
    self.connections_link.visible = glob.trust_level >= 2 # show if guest_allowed (DashForm.timer_1)
    self.my_groups_link.visible = glob.trust_level >= 3
    self.test_column_panel.visible = self.item['test_mode']
    # if p.DEBUG_MODE and self.item['test_mode']:
    #   auto_test.client_auto_tests()
    self.set_test_link()
    self.timer_1.interval = 30*60 #kludge to prevent cache from becoming *too* stale
    
  def form_show(self, **event_args):
    self.reset_status(self.item['state'])

  def timer_1_tick(self, **event_args):
    """This method is called Every [interval] seconds. Does not trigger if [interval] is 0."""
    # with h.PausedTimer(self.timer_2):
    print("refreshing cache")
    glob.populate_lazy_vars(spinner=False)
  
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
    if not_me(user_id):
      self.title_label.text = "" # other user's profile
      item = {'user_id': user_id, 'tab': 'connections'}
      self.reset_and_load(UserMenu(item=item)) 
    else:
      self.title_label.text = "My Network"
      self.reset_and_load(NetworkMenu())
      self.connections_link.role = "selected"   
    
  def go_my_groups(self):
    self.title_label.text = "My Groups"
    self.reset_and_load(MyGroupsMenu())   
    self.my_groups_link.role = "selected" 
    
  def go_profile(self, user_id="", tab="profile"):
    if not_me(user_id):
      self.title_label.text = "" # other user's profile
      item = {'user_id': user_id, 'tab': tab}
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
    self.hide_sidebar_mobile()
    self.reset_status(anvil.server.call('get_state'))
    
  def connections_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.hide_sidebar_mobile()
    self.go_connections()  
    
  def groups_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.hide_sidebar_mobile()
    self.go_groups()  
  
  def my_groups_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.hide_sidebar_mobile()
    self.go_my_groups()  
    
  def profile_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.hide_sidebar_mobile()
    self.go_profile()
  
  def settings_link_click(self, **event_args):
    """This method is called when the link is clicked"""
    self.hide_sidebar_mobile()
    self.go_settings()

  def hide_sidebar_mobile(self):
    if glob.MOBILE:
      from anvil.js.window import hideSidebar
      anvil.js.call(hideSidebar)
    
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
    print("logout")
    anvil.users.logout()
    glob.logged_in_user = None
    glob.logged_in_user_id = ""
    open_form('LoginForm')

  def autotest_butten_click(self, **event_args):
    """This method is called when the button is clicked"""
    auto_test.run_now_test()
