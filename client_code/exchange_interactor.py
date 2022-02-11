from . import server_misc as sm
from .exchange_gateway import ExchangeRepository #, in_transaction
from anvil.tables import in_transaction
from .exceptions import RowMissingError
import anvil.secrets


def init_match_form(user_id):
  """Return jitsi_code, duration (or Nones), my_slider_value
  
  Side effect: set this_match['present']"""
  user = sm.get_user(user_id)
  try:
    return _init_match_form_already_matched(user)
  except RowMissingError as err:
    return _init_match_form_not_matched(user)


def _init_match_form_already_matched(user):
  from .proposals import ProposalTime
  from . import matcher
  repo = ExchangeRepository(user)
  _mark_present(repo)
  matcher.propagate_update_needed()
  this_match, i = repo.exchange_i()
  proptime = ProposalTime(this_match['proposal_time'])
  jitsi_code, duration = proptime.get_match_info()
  return proptime.get_id(), jitsi_code, duration, this_match['slider_values'][i]


def _init_match_form_not_matched(user):
  from .proposals import ProposalTime
  current_proptime = ProposalTime.get_now(user)
  if current_proptime:
    return _init_match_form_requesting(current_proptime)
  else:
    sm.warning(f"_init_match_form_not_matched request not found for {user.get_id()}")
    return None, None, None, ""


def _init_match_form_requesting(current_proptime):
  jitsi_code, duration = current_proptime.get_match_info()
  return current_proptime.get_id(), jitsi_code, duration, ""
  
  
def update_match_form(user_id, repo=None):
  """Return match_state dict
  
  Side effect: Update match['present']"""
  user = sm.get_user(user_id)
  if not repo:
    try:
      repo = ExchangeRepository(user)
    except RowMissingError as err:
      return _update_match_form_not_matched(user)
  return _update_match_form_already_matched(user, repo)
  

def _update_match_form_already_matched(user, repo):
  from . import matcher
  _mark_present(repo)
  matcher.propagate_update_needed()
  this_match, i = repo.exchange_i()
  other_user = their_value(this_match['users'], i)
  if _late_notify_needed(this_match, i):
    from . import notifies as n
    n.notify_late_for_chat(other_user, this_match['match_commence'], [user])
    _mark_notified(repo, other_user)
  _their_value = their_value(this_match['slider_values'], i)
  their_external = their_value(this_match['external'], i)
  their_complete = their_value(this_match['complete'], i)
  how_empathy_list = ([user['how_empathy']]
                      + [u['how_empathy'] for u in this_match['users']
                         if u != user]
                     )
  messages = repo.chat_messages()
  messages_out = [{'me': (user == m['user']),
                   'message': anvil.secrets.decrypt_with_key("new_key", m['message'])}
                  for m in messages]
  their_name = other_user['first_name']
  return dict(
    status="matched",
    how_empathy_list=how_empathy_list,
    their_name=their_name,
    message_items=messages_out,
    their_slider_value=_their_value,
    their_external=their_external,
    their_complete=their_complete,
  )


def _late_notify_needed(this_match, i):
  their_present = their_value(this_match['present'], i)
  their_notified = their_value(this_match['late_notified'], i)
  if their_present or their_notified:
    return False
  now = sm.now()
  later_scheduled_match = this_match['proposal_time']['expire_date'] < now
  past_start_time = this_match['match_commence'] < now
  return later_scheduled_match and past_start_time

  
def _update_match_form_not_matched(user):
  from . import matcher
  matcher.confirm_wait_helper(user)
  partial_state = matcher.get_status(user)
  matcher.propagate_update_needed(user)
  return dict(
    status=partial_state['status'],
    how_empathy_list=[],
    their_name="",
    message_items=[],
    their_slider_value="",
    their_external=None,
    their_complete=None,
  )


def match_complete(user_id):
  """Switch 'complete' to true in matches table for user"""
  from . import matcher
  user = sm.get_user(user_id)
  try:
    repo = ExchangeRepository(user)
    _mark_complete(repo)
  except RowMissingError as err:
    sm.warning(f"match_complete: match not found {user.get_id()}")
  matcher.propagate_update_needed()


@in_transaction(relaxed=True)
def _mark_present(repo):
  repo.mark_present()

  
@in_transaction(relaxed=True)
def _mark_complete(repo):
  repo.complete()

  
@in_transaction(relaxed=True)
def _mark_notified(repo, other_user): 
  repo.mark_notified(other_user)

  
def add_chat_message(user_id, message):
  user = sm.get_user(user_id)
  repo = ExchangeRepository(user)
  repo.add_chat(message=anvil.secrets.encrypt_with_key("new_key", message),
                now=sm.now(),
               )
  return update_match_form(user_id, repo=repo)


@in_transaction(relaxed=True)
def update_my_external(my_external, user_id):
  user = sm.get_user(user_id)
  try:
    repo = ExchangeRepository(user)
    repo.update_my_external(int(my_external))
  except RowMissingError:
    print("Exchange record not available to record my_external")


@in_transaction(relaxed=True)
def submit_slider(value, user_id):
  user = sm.get_user(user_id)
  repo = ExchangeRepository(user)
  this_match, i = repo.submit_slider(value)
  return their_value(this_match['slider_values'], i)  
  
  
def their_value(values, my_i):
  temp_values = [value for value in values]
  temp_values.pop(my_i)
  if len(temp_values) != 1:
    sm.warning(f"len(temp_values) != 1, but this function assumes dyads only")
  return temp_values[0]                     # return the remaining value
