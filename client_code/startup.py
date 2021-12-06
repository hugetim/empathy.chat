import anvil.facebook.auth
import anvil.users
import anvil.server
import anvil
from .Dialogs.Invited import Invited
from . import invited


h = anvil.get_url_hash()
if isinstance(h, dict) and 'invite' in h:
  invited.handle_link(h['invite'])
else:
  anvil.open_form('LoginForm')

