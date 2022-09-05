import anvil.server
import anvil.users
from anvil import *
from . import invites
from . import parameters as p
from . import ui_procedures as ui
from . import groups
from .exceptions import RowMissingError, ExpiredInviteError, MistakenVisitError
from .Dialogs.Invited import Invited


def invited_dialog(inviter):
  from . import portable as port
  invite = invites.Invite(inviter=inviter, invitee=port.User.from_logged_in())
  errors = invite.relay('load')
  top_form = get_open_form()
  top_form.invited_alert = Invited(item=invite)
  return alert(content=top_form.invited_alert,
               title="Accept this invitation to link?",
               buttons=[], large=True, dismissible=False)

  
def handle_link(hash_key, hash_value):
  hash_router = {'invite': _handle_close_invite,
                 'group': _handle_group_invite,
                }
  hash_router[hash_key](hash_value)


def _handle_close_invite(link_key):
  print(f"_handle_close_invite: {link_key}")
  user = anvil.users.get_user()
  invite = invites.Invite(link_key=link_key)
  errors = invite.relay('visit', {'user': user})
  _handle_close_invite_visit_outcome(invite, errors, user)
  ui.clear_hash_and_open_form('LoginForm')


def _handle_close_invite_visit_outcome(invite, errors, user):
  if not errors:
    invited_alert = Invited(item=invite)
    if alert(content=invited_alert, 
             title="", 
             buttons=[], large=True, dismissible=False):
      if not user:
        method = invited_signup(invite)
  elif "This invite link is no longer active." in errors:
    alert("This invite link is no longer active.")
  elif p.CLICKED_OWN_LINK_ERROR in errors:
    alert(p.CLICKED_OWN_LINK_ERROR, large=True)
  else:
    alert(" ".join(errors)) #This is not a valid invite link."


def _handle_group_invite(link_key):
  print(f"_handle_group_invite: {link_key}")
  user = anvil.users.get_user()
  invite = groups.Invite(link_key=link_key)
  try:
    invite.relay('visit', {'user': user})
    if not user:
      method = invited_signup(invite)
  except RowMissingError as err:
    alert(err.args[0])
  except ExpiredInviteError as err:
    alert(err.args[0])
  except MistakenVisitError as err:
    alert(err.args[0], large=True)
  ui.clear_hash_and_open_form('LoginForm')

    
def invited_signup(invite):
  from .Dialogs.Signup import Signup
  d = Signup()
  new_user = None
  while not new_user:
    method = alert(d, title="Sign Up", buttons=[("Sign Up", "email", 'primary')])
    new_user = _process_signup_dialog(d, method)
  errors = invite.relay('visit', dict(user=new_user, register=True))
  if isinstance(invite, invites.Invite) and new_user['phone'] and not errors:
    Notification("You have been successfully linked.", style="success").show()
  if new_user and method == "email":
    _show_alert_re_pw_email(new_user["email"])
  return method


def _show_alert_re_pw_email(email_address):
  alert((f'We have sent an email to {email_address} with "empathy.chat - (re)set your password" as the subject.\n\n'
         'Click the link contained in that email to set your password and login.\n\nYou can now close this window/tab.'), 
        large=True, 
        dismissible=False,
       )


def _process_signup_dialog(d, method):
  """Return new_user if successful signup/login
  
  Side effects: display errors on Dialog form
  """
  if method in ["google", "login"]:
    return d.new_user
  elif method == "email":
    try:
      return anvil.server.call('do_signup', d.email_box.text)
    except anvil.users.AuthenticationFailed:
      d.signup_err_lbl.text = "Email address missing or invalid. Please enter a valid email address."
      d.signup_err_lbl.visible = True
    except anvil.users.UserExists as err:
      d.signup_err_lbl.text = f"{err.args[0]}\nPlease login to your account normally and then try this invite link again."
      d.signup_err_lbl.visible = True
      