import anvil.server
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from anvil import *
from . import invites


def invited_dialog(inviter):
  from . import portable as port
  invite = invites.Invite(inviter=inviter, invitee=port.User.from_logged_in())
  errors = invite.relay('load')
  top_form = get_open_form()
  from .Dialogs.Invited import Invited
  top_form.invited_alert = Invited(item=invite)
  return alert(content=top_form.invited_alert,
               title="Accept this invitation to link?",
               buttons=[], large=True, dismissible=False)
  

def handle_link(link_key):
  print(f"handle_link: {link_key}")
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
        method = invited_signup(invite)
      if anvil.users.get_user():
        open_form('LoginForm')
  elif "This invite link is no longer active." in errors:
    alert("This invite link is no longer active.")
    set_url_hash('')
    open_form('LoginForm')
  else:
    alert(" ".join(errors)) #This is not a valid invite link."

    
def invited_signup(invite):
  from .Dialogs.Signup import Signup
  d = Signup()
  new_user = None
  while not new_user:
    method = alert(d, title="Sign Up", buttons=[("Sign Up", "email", 'primary')])
    if method == "google":
      new_user = d.new_user
    elif method == "email":
      try:
        new_user = anvil.server.call('do_signup', d.email_box.text)
      except anvil.users.AuthenticationFailed:
        d.signup_err_lbl.text = "Email address missing or invalid. Please enter a valid email address."
        d.signup_err_lbl.visible = True
  invite.relay('visit', dict(user=new_user, register=True))
  if method == "email":
    alert(f"We have sent a login email to {new_user['email']}.\n\nCheck your email, and click on the link.\n\nYou can now close this window.")
  return method
    