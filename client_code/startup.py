import anvil


def error_handler(err):
  from . import error_helper as eh
  if isinstance(err, (anvil.server.AppOfflineError, anvil.server.TimeoutError)):
    eh.handle_server_connection_error(err)
  else:
    eh.report_error(err)
    raise(err)


anvil.set_default_error_handling(error_handler)


def _route_hash(known_hash_key, hash_value):
  from . import invited_procedures as invited
  invited.handle_link(known_hash_key, hash_value)


url_hash = anvil.get_url_hash()
known_hash_keys = {'invite', 'group'}
url_contains_one_known_hash_key = isinstance(url_hash, dict) and len(url_hash.keys() & known_hash_keys) == 1
if url_contains_one_known_hash_key:
  [known_key] = url_hash.keys() & known_hash_keys
  hash_value = url_hash[known_key]
  _route_hash(known_key, hash_value)
else:
  from . import ui_procedures as ui
  ui.clear_hash_and_open_form('LoginForm')


