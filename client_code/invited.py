import anvil.server
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from anvil import *
from . import parameters as p
from . import invites


def invited_dialog(inviter):
  invite = invites.Invite(inviter=inviter, invitee=anvil.users.get_user())
  errors = invite.relay('load')
  top_form = get_open_form()
  from .Dialogs.Invited import Invited
  top_form.invited_alert = Invited(item=invite)
  return alert(content=top_form.invited_alert,
               title="Accept this invitation to connect?",
               buttons=[], large=True, dismissible=False)
  

def handle_link(link_key):
  user = anvil.users.get_user()
  invite = invites.Invite(link_key=link_key)
  errors = invite.relay('visit', {'user': user})
  #item = anvil.server.call('invite_visit', link_key, user2=user)
  if not errors:
    from .Dialogs.Invited import Invited
    invited_alert = Invited(item=invite)
    if alert(content=invited_alert, 
             title="", 
             buttons=[], large=True, dismissible=False):
      if not user:
        new_user = anvil.users.signup_with_form(allow_cancel=True)
        if not new_user:
          new_user = anvil.users.login_with_form()
        invite.relay('visit', dict(user=new_user, register=True))
        #anvil.server.call('invite_visit_register', link_key, new_user)
      open_form('LoginForm')
  else:
    alert(" ".join(errors)) #This is not a valid invite link."


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
  