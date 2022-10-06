from anvil import *
import anvil.server
import anvil.users
from anvil.js import window, ExternalError, call_js
from . import glob
from anvil_extras.utils import timed


def login():
  user = anvil.users.login_with_form(show_signup_option=False, allow_cancel=True)
  if user and (not user['init_date']):
    anvil.users.logout()
    with Notification(f"Sorry, there is no account for {user['email']} (and empathy.chat is currently invite-only). "
                      "Creating a new account requires an invite link."):
      anvil.server.call_s('remove_user', user)
      import time
      time.sleep(4)
    user = None
  return user


def clear_hash_and_open_form(form):
  set_url_hash('')
  open_form(form)


def get_user_agent():
  from anvil.js.window import navigator
  return navigator.userAgent


def get_mobile_status():
  import re
  mobile_devices = "Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini"
  glob.MOBILE = re.search(mobile_devices, get_user_agent()) is not None
  if glob.MOBILE:
    print("MOBILE")

  
def disconnect_flow(user2_id, user2_name, user1_id=""):
  if confirm(f"Really remove your link to {user2_name}? This cannot be undone."):
    return anvil.server.call('disconnect', user2_id, user1_id)
  else:
    return False

      
def reload(init_dict=None, do_open=True):
  """Resest app after any potential change to trust_level or prompts"""
  if not init_dict:
    init_dict = get_init()
  glob.name = init_dict['name']
  glob.trust_level = init_dict['trust_level']
  if init_dict['state']['status'] in ["matched", "requesting", "pinged"]:
    from .MenuForm.MatchForm import MatchForm
    item = {k: init_dict['state'][k] for k in MatchForm.state_keys}
    new_form = MatchForm(item=item)
  else:
    from .MenuForm import MenuForm
    new_form = MenuForm(item=init_dict)
  if do_open:
    open_form(new_form)
  else:
    return new_form


@timed
def get_init(spinner=True):
  from anvil.js.window import Intl
  from . import helper as h
  time_zone = Intl.DateTimeFormat().resolvedOptions().timeZone
  if spinner:
    return h.robust_server_call('init', time_zone)
  else:
    return h.robust_server_call_s('init', time_zone)

  
def copy_to_clipboard(text, desc="It"):
  from anvil.js.window import navigator
  try:
    navigator.clipboard.writeText(text)
    Notification(f"{desc} has been copied to the clipboard.", style="success").show()
  except ExternalError as err:
    Notification(str(err), timeout=5).show()
    print(f"copy_to_clipboard error: {repr(err)}")

    
def set_document_title(text):
  try:
    window.document.title = text
  except ExternalError as err:
    print(f"Error setting document title: {repr(err)}")


def change_favicon(url):
  favicons = window.document.querySelectorAll('link[rel="icon"]')
  # If a <link rel="icon"> element already exists,
  # change its href to the given link.
  old_hrefs = []
  for favicon in favicons:
    if favicon:
      old_hrefs.append(favicon.href)
      favicon.href = url
  return old_hrefs


def return_favicons(old_hrefs):
  favicons = window.document.querySelectorAll('link[rel="icon"]')
  # If a <link rel="icon"> element already exists,
  # change its href to the given link.
  for favicon, old_href in zip(favicons, old_hrefs):
    if favicon:
      favicon.href = old_href


class BrowserTab():
  def __init__(self, title=None, favicon_url=None):
    self.title = title
    self.favicon_url = favicon_url
    
  def __enter__(self):
    if self.title is not None:
      self.old_title = window.document.title
      set_document_title(self.title)
    if self.favicon_url is not None:
      try:
        self.old_hrefs = change_favicon(self.favicon_url)
      except ExternalError as err:
        self.favicon_url = None
        print(f"Error setting favicon: {repr(err)}")
        
  def __exit__(self, type, value, tb):
    if self.title is not None:
      set_document_title(self.old_title)
    if self.favicon_url is not None:
      self.old_hrefs = return_favicons(self.old_hrefs)      


class _loading_indicator:
    def __enter__(self):
        call_js('setLoading', True)
        return self
    def __exit__(self, exc_type, exc_value, tb):
        call_js('setLoading', False)
    def __call__(self, func):
#         @wraps(func)
        def wrapper(*args, **kw):
            with self:
                return func(*args, **kw)
        return wrapper

loading_indicator = _loading_indicator()
