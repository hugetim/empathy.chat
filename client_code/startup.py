import anvil
from .Dialogs.Invited import Invited

h = anvil.get_url_hash()
if isinstance(h, dict) and 'invite' in h:
  item = anvil.server.call('invite_visit', h['invite'])
  if item:
    invited_alert = Invited(item=item)
    if anvil.alert(content=invited_alert, 
                   title="You have been invited to empathy.chat", 
                   buttons=[], large=True, dismissible=False):
      anvil.users.signup_with_form()
  else:
    anvil.alert("This is not a valid invite link.")

anvil.open_form('LoginForm')

