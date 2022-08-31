import anvil.server
import anvil.users
from anvil import *
from . import invites
from . import parameters as p


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
  elif p.CLICKED_OWN_LINK_ERROR in errors:
    alert(p.CLICKED_OWN_LINK_ERROR, large=True)
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
    if method in ["google", "login"]:
      new_user = d.new_user
    elif method == "email":
      try:
        new_user = anvil.server.call('do_signup', d.email_box.text)
      except anvil.users.AuthenticationFailed:
        d.signup_err_lbl.text = "Email address missing or invalid. Please enter a valid email address."
        d.signup_err_lbl.visible = True
      except anvil.users.UserExists as err:
        d.signup_err_lbl.text = f"{err.args[0]}\nPlease login to your account normally and then try this invite link again."
        d.signup_err_lbl.visible = True
  errors = invite.relay('visit', dict(user=new_user, register=True))
  if isinstance(invite, invites.Invite) and not errors and new_user['phone']:
    Notification("You have been successfully linked.", style="success").show()
  if new_user and method == "email":
    alert((f'We have sent an email to {new_user["email"]} with "empathy.chat - (re)set your password" as the subject.\n\n'
           'Click the link contained in that email to set your password and login.\n\nYou can now close this window/tab.'), 
          large=True, dismissible=False,
         )
  return method
    