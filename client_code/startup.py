from anvil import *


h = get_url_hash()
if isinstance(h, dict) and 'invite' in h:
  if not anvil.server.call('invite_visit', h['invite']):
    alert("This is not a valid invite link.")

open_form('LoginForm')

