import anvil.server
import anvil.users
from anvil import *
from . import invites
from . import parameters as p
from . import ui_procedures as ui
from . import helper as h
from . import groups
from .glob import publisher
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
    _complete_close_invited_process(invite, user)
  elif "This invite link is no longer active." in errors:
    alert("This invite link is no longer active.")
  elif p.CLICKED_OWN_LINK_ERROR in errors:
    alert(p.CLICKED_OWN_LINK_ERROR, large=True)
  else:
    alert(" ".join(errors)) #This is not a valid invite link."


def _complete_close_invited_process(invite, user):
  invited_alert = Invited(item=invite)
  if alert(content=invited_alert, 
           title="", 
           buttons=[], large=True, dismissible=False):
    if not user:
      invited_signup(invite)


def _handle_group_invite(link_key):
  print(f"_handle_group_invite: {link_key}")
  user = anvil.users.get_user()
  invite = groups.Invite(link_key=link_key)
  _process_group_invite_visit(invite, user)
  ui.clear_hash_and_open_form('LoginForm')


def _process_group_invite_visit(invite, user):
  try:
    invite.relay('visit', {'user': user})
    if not user:
      invited_signup(invite)
  except RowMissingError as err:
    alert(err.args[0])
  except ExpiredInviteError as err:
    alert(err.args[0])
  except MistakenVisitError as err:
    alert(err.args[0], large=True)


def invited_signup(invite):
  from .Dialogs.Signup import Signup
  d = Signup()
  new_user = None
  while not new_user:
    method = alert(d, title="Sign Up", buttons=[("Sign Up", "email", 'primary')])
    new_user = _process_signup_dialog(d, method)
  publisher.close_channel("signup_error")
  errors = invite.relay('visit', dict(user=new_user, register=True))
  if isinstance(invite, invites.Invite) and new_user['phone'] and not errors:
    Notification("You have been successfully linked.", style="success").show()
  if new_user and method == "email":
    _show_alert_re_pw_email(new_user["email"])


def _show_alert_re_pw_email(email_address):
  alert((f'We have sent an email to {email_address} with "empathy.chat - (re)set your password" as the subject.\n\n'
         'Click the link contained in that email to set your password and login.\n\nYou can now close this window/tab.'), 
        large=True, 
        dismissible=False,
       )


def _process_signup_dialog(signup_dialog, method):
  """Return new_user if successful signup/login
  
  Side effects: display errors on Dialog form
  """
  if method in ["google", "login"]:
    return signup_dialog.new_user
  elif method == "email":
    return _submit_signup_email_to_server(signup_dialog.email_box.text)


def _submit_signup_email_to_server(email_address):
  """Return new_user if successful signup/login
  
  Side effects: publish errors (to Dialog form)
  """
  try:
    return anvil.server.call('do_signup', email_address)
  except anvil.users.AuthenticationFailed:
    publisher.publish("signup_error", 
                      "Email address missing or invalid. Please enter a valid email address.")
  except anvil.users.UserExists as err:
    publisher.publish("signup_error", 
                      f"{err.args[0]}\nPlease login to your account normally and then try this invite link again.")


def submit_response(invite):
  validation_errors = invite.invalid_response()
  if validation_errors:
    publisher.publish("invited1_error", "\n".join(validation_errors))
  else:
    _submit_response(invite)

def _submit_response(invite):
  errors = invite.relay('respond')
  if p.MISTAKEN_INVITER_GUESS_ERROR in errors:
    Notification(p.MISTAKEN_INVITER_GUESS_ERROR, title="Mistaken Invite", style="info", timeout=None).show()
    publisher.publish("invited", "failure")
  elif errors:
    publisher.publish("invited1_error", "\n".join(errors))
  else:
    _handle_successful_response(invite)

def _handle_successful_response(invite):    
  user = anvil.users.get_user()
  has_phone = user['phone'] if user else None
  h.my_assert(has_phone or invite.from_invite_link, "either Confirmed or link invite")
  if not user:
    publisher.publish("invited", "go_invited2", invite)
  elif not has_phone:
    publisher.publish("invited", "success")
  else:
    Notification("You have been successfully linked.", style="success").show()
    publisher.publish("invited", "success")