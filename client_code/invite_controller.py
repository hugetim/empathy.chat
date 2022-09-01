import anvil.server
import anvil.users
from . import ui_procedures as ui
from . import groups
from . import invited
from .exceptions import RowMissingError, ExpiredInviteError, MistakenVisitError


def _handle_group_link(link_key):
  print(f"groups.handle_link: {link_key}")
  user = anvil.users.get_user()
  invite = groups.Invite(link_key=link_key)
  try:
    invite.relay('visit', {'user': user})
  except RowMissingError as err:
    alert(err.args[0])
    ui.clear_hash_and_open_form('LoginForm')
    return
  except ExpiredInviteError as err:
    alert(err.args[0])
    ui.clear_hash_and_open_form('LoginForm')
    return
  except MistakenVisitError as err:
    alert(err.args[0], large=True)
    ui.clear_hash_and_open_form('LoginForm')
    return
  if not user:
    method = invited.invited_signup(invite)
  if anvil.users.get_user():
    ui.clear_hash_and_open_form('LoginForm')


def load_invites():
  return anvil.server.call('load_invites')
