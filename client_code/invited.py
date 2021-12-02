import anvil.server
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil
from . import parameters as p


def handle_link(link_key):
  user = anvil.users.get_user()
  item = anvil.server.call('invite_visit', link_key, user2=user)
  if item:
    invited_alert = Invited(item=item)
    if anvil.alert(content=invited_alert, 
                   title="", 
                   buttons=[], large=True, dismissible=False):
      if not user:
        new_user = anvil.users.signup_with_form()
        anvil.server.call('invite_visit_register', link_key, new_user)
      anvil.open_form('LoginForm')
  else:
    anvil.alert("This is not a valid invite link.")


def submit_invite_reply(item):
  """Returns error_message
  
  Side effects: submits well-formatted item to server, updates input item"""
  if len(item['phone_last4']) != 4:
    return "Wrong number of digits entered."
  elif len(item['relationship']) < p.MIN_RELATIONSHIP_LENGTH:
    return "Please add a description of your relationship."
  else:
    if item['link_key']: # from a link invite
      invited_item = anvil.server.call('add_invited', item)
    else:
      invited_item = anvil.server.call('connect_invited', item)
    if invited_item:
      item.update(invited_item)
      return None
    else:
      return f"The last 4 digits you provided do not match {item['inviter']}'s phone number."
