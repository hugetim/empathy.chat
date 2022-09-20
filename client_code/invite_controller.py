import anvil.server
from .glob import publisher
from .exceptions import RowMissingError, ExpiredInviteError, MistakenVisitError, InvalidInviteError, MistakenGuessError


def submit_invite(invite):
  validation_errors = invite.invalid_invite()
  if validation_errors:
    publisher.publish("invite_a_error", "\n".join(validation_errors))
  else:
    _submit_invite(invite)


def _submit_invite(invite):
  try:
    invite.relay('add')
    if invite.invitee: #existing user
      message = f"You will be linked once {invite.invitee.name} confirms."
      publisher.publish("invite", "success")
      alert(message)
    else:
      publisher.publish("invite", "go_invite_b", invite)
  except InvalidInviteError as err:
    publisher.publish("invite_a_error", err.args[0])
  except MistakenGuessError as err:
    publisher.publish("invite_a_error", err.args[0])


def load_invites():
  return anvil.server.call('load_invites')
