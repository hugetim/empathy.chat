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
from .Dialogs.Signup import Signup


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
        new_user = invited_signup(invite)
      if anvil.users.get_user():
        open_form('LoginForm')
  else:
    alert(" ".join(errors)) #This is not a valid invite link."

def invited_signup(invite):
  d = Signup()
  new_user = None
  while not new_user:
    method = alert(d, title="Sign Up", buttons=[("Sign Up", "email", 'primary')])
    if method == "google":
#       anvil.google.auth.login()
#       email = anvil.google.auth.get_user_email()
#       new_user = anvil.server.call('do_google_signup', email)
#       try:
#         new_user = anvil.users.signup_with_google()
#       except anvil.users.UserExists:
#         print("UserExists: Calling login_with_google")
#         d.signup_err_lbl.text = "An account already exists for that user, so sign up is unnecessary. Instead, please login now."
#         d.signup_err_lbl.visible = True
#         new_user = anvil.users.login_with_google()
      new_user = d.new_user
      print(anvil.users.get_user())
    elif method == "email":
      try:
        new_user = anvil.server.call('do_signup', d.email_box.text)
      except anvil.users.AuthenticationFailed:
        d.signup_err_lbl.text = "Email address missing or invalid. Please enter a valid email address."
        d.signup_err_lbl.visible = True
  invite.relay('visit', dict(user=new_user, register=True))
  if method == "email":
    alert(f"We have sent a login email to {d.email_box.text}.\n\nCheck your email, and click on the link.\n\nYou can now close this window.")
  return method
    