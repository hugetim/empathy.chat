import anvil


def error_handler(err):
  from . import error_helper as eh
  if isinstance(err, (anvil.server.AppOfflineError, anvil.server.TimeoutError)):
    eh.handle_server_connection_error(err)
  else:
    eh.report_error(err)
    raise(err)


anvil.set_default_error_handling(error_handler)


def _route_hash_key(known_hash_key):
  hash_value = url_hash[known_hash_key]
  from . import invited
  from . import groups
  hash_router = {'invite': invited.handle_link,
                 'group': groups.handle_link,
                }
  hash_router[known_hash_key](hash_value)


url_hash = anvil.get_url_hash()
known_hash_keys = {'invite', 'group'}
url_contains_one_known_hash_key = isinstance(url_hash, dict) and len(url_hash.keys() & known_hash_keys) == 1
if url_contains_one_known_hash_key:
  [known_key] = url_hash.keys() & known_hash_keys
  _route_hash_key(known_key)
else:
  from . import ui_procedures as ui
  ui.clear_hash_and_open_form('LoginForm')


