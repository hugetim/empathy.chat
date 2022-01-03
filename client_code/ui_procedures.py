from anvil import *
import anvil.users
import anvil.server
from datetime import datetime
from . import glob


def disconnect_flow(user2_id, user2_name, user1_id=""):
  if confirm(f"Really remove your connection to {user2_name}? This cannot be undone."):
    return anvil.server.call('disconnect', user2_id, user1_id)
  else:
    return False

      
def reload(init_dict=None):
  """Resest app after any potential change to trust_level or prompts"""
  if not init_dict:
    init_dict = get_init()
  glob.name = init_dict['name']
  glob.trust_level = init_dict['trust_level']
  if init_dict['state']['status'] in ["matched", "requesting", "pinged"]:
    from .MenuForm.MatchForm import MatchForm
    item = {k: init_dict['state'][k] for k in MatchForm.state_keys}
    open_form(MatchForm(item=item))
  else:
    open_form('MenuForm', item=init_dict)

    
def get_init():
    from anvil.js.window import Intl 
    time_zone = Intl.DateTimeFormat().resolvedOptions().timeZone
    now = datetime.now()
    return anvil.server.call('init', time_zone)
    
  
def set_document_title(text):
  from anvil.js import window
  old_title = window.document.title
  window.document.title = text
  return old_title


def change_favicon(url):
  from anvil.js import window
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
  from anvil.js import window
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
      self.old_title = set_document_title(self.title)
    if self.favicon_url is not None:
      self.old_hrefs = change_favicon(self.favicon_url)
  def __exit__(self, type, value, tb):
    if self.title is not None:
      set_document_title(self.old_title)
    if self.favicon_url is not None:
      self.old_hrefs = return_favicons(self.old_hrefs)