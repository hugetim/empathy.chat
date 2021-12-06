import anvil.facebook.auth
import anvil.server
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil
from . import parameters as p


def invited_dialog(inviter, inviter_id, rel):
  item = {"relationship": "", "phone_last4": "", "name": inviter, "inviter_id": inviter_id,
          "relationship1to2": rel, "inviter": inviter, "link_key": ""}
  top_form = get_open_form()
  from .Dialogs.Invited import Invited
  top_form.invited_alert = Invited(item=item)
  return alert(content=top_form.invited_alert,
               title="Accept this invitation to connect?",
               buttons=[], large=True, dismissible=False)
  

def handle_link(link_key):
  user = anvil.users.get_user()
  item = anvil.server.call('invite_visit', link_key, user2=user)
  if item:
    from .Dialogs.Invited import Invited
    invited_alert = Invited(item=item)
    if anvil.alert(content=invited_alert, 
                   title="", 
                   buttons=[], large=True, dismissible=False):
      if not user:
        new_user = anvil.users.signup_with_form(allow_cancel=True)
        if not new_user:
          new_user = anvil.users.login_with_form()
        anvil.server.call('invite_visit_register', link_key, new_user)
      anvil.open_form('LoginForm')
  else:
    anvil.alert("This is not a valid invite link.")


def submit_invite_reply(item):
  """Returns error_message if item not well-formatted or doesn't match phone number
  
  Side effects: submits well-formatted item to server"""
  if len(item['phone_last4']) != 4:
    return "Wrong number of digits entered."
  elif len(item['relationship']) < p.MIN_RELATIONSHIP_LENGTH:
    return "Please add a description of your relationship."
  else:
    return anvil.server.call('submit_invited', item)


def cancel(item):
  anvil.server.call('cancel_invited', item)
  