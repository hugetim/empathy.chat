import anvil.users
import anvil.server
import anvil


def error_handler(err):
  app_info_dict = {'id': anvil.app.id,
                   'branch': anvil.app.branch,
                   'environment.name': anvil.app.environment.name,
                  }
  anvil.server.call('report_error', repr(err), app_info_dict)
  raise(err)


from .Dialogs.Invited import Invited
from . import invited
  

anvil.set_default_error_handling(error_handler)
h = anvil.get_url_hash()
if isinstance(h, dict) and 'invite' in h:
  invited.handle_link(h['invite'])
else:
  anvil.open_form('LoginForm')
