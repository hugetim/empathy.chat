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
from . import portable as port


def invited_dialog(inviter):
  invite = invites.Invite(inviter=inviter, invitee=port.User.from_logged_in())
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
      open_form('LoginForm')
  else:
    alert(" ".join(errors)) #This is not a valid invite link."
