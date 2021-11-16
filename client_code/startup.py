import anvil.users
import anvil.server
import anvil
from .Dialogs.Invited import Invited

h = anvil.get_url_hash()
if isinstance(h, dict) and 'invite' in h:
  user = anvil.users.get_user()
  item = anvil.server.call('invite_visit', h['invite'], user_id=user.get_id())
  if item:
    invited_alert = Invited(item=item)
    if anvil.alert(content=invited_alert, 
                   title="You have been invited to empathy.chat", 
                   buttons=[], large=True, dismissible=False):
      if not user:
        new_user = anvil.users.signup_with_form()
        anvil.server.call('invite_visit_register', h['invite'], new_user)
      anvil.open_form('LoginForm')
  else:
    anvil.alert("This is not a valid invite link.")
else:
  anvil.open_form('LoginForm')

