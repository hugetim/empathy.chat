import anvil


h = anvil.get_url_hash()
if isinstance(h, dict) and 'invite' in h:
  if anvil.server.call('invite_visit', h['invite']):
    pass
  else:
    anvil.alert("This is not a valid invite link.")

anvil.open_form('LoginForm')

