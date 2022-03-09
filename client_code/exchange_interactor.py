from . import server_misc as sm
from .exceptions import RowMissingError
import anvil.secrets


def init_match_form(user_id, repo):
  """Return jitsi_code, duration (or Nones), my_slider_value
  
  Side effect: set this_match['present']"""
  try:
    return _init_match_form_already_matched(user_id, repo)
  except RowMissingError as err:
    return _init_match_form_not_matched(user_id)


def _init_match_form_already_matched(user_id, repo):
  exchange = repo.get_exchange(user_id)
  my = exchange.my()
  my['present'] = 1
  repo.save_exchange(exchange)
  other_user = sm.get_user(exchange.their()['user_id'])
  other_user['update_needed'] = True
  return None, exchange.room_code, exchange.exchange_format.duration, my['slider_value']


def _init_match_form_not_matched(user_id):
  from .proposals import ProposalTime
  user = sm.get_user(user_id)
  current_proptime = ProposalTime.get_now(user)
  if current_proptime:
    return _init_match_form_requesting(current_proptime)
  else:
    sm.warning(f"_init_match_form_not_matched request not found for {user_id}")
    return None, None, None, ""


def _init_match_form_requesting(current_proptime):
  jitsi_code, duration = current_proptime.get_match_info()
  return current_proptime.get_id(), jitsi_code, duration, ""
  
  
def update_match_form(user_id, repo):
  """Return match_state dict
  
  Side effect: Update match['present']"""
  try:
    exchange = repo.get_exchange(user_id)
    return _update_match_form_already_matched(user_id, exchange, repo)
  except RowMissingError as err:
    return _update_match_form_not_matched(user_id)
  

def _update_match_form_already_matched(user_id, exchange, repo):
  user = sm.get_user(user_id)
  my = exchange.my()
  changed = not my['present']
  my['present'] = 1
  #this_match, i = repo.exchange_i()
  their = exchange.their()
  other_user = sm.get_user(their['user_id'])
  if exchange.late_notify_needed(sm.now()):
    from . import notifies as n
    n.notify_late_for_chat(other_user, exchange.start_dt, [user])
    changed = True
    their['late_notified'] = 1
  if changed:
    repo.save_exchange(exchange)
    other_user['update_needed'] = True
  how_empathy_list = [user['how_empathy'], other_user['how_empathy']]
  messages = repo.get_chat_messages(exchange)
  messages_out = [{'me': (user == m['user']),
                   'message': anvil.secrets.decrypt_with_key("new_key", m['message'])}
                  for m in messages]
  their_name = other_user['first_name']
  return dict(
    status="matched",
    how_empathy_list=how_empathy_list,
    their_name=their_name,
    message_items=messages_out,
    my_slider_value=my['slider_value'],
    their_slider_value=their['slider_value'],
    their_external=their['external'],
    their_complete=their['complete'],
  )

  
def _update_match_form_not_matched(user_id):
  from . import matcher
  user = sm.get_user(user_id)
  matcher.confirm_wait_helper(user)
  partial_state = matcher.get_status_in_transaction(user)
  matcher.propagate_update_needed(user)
  return dict(
    status=partial_state['status'],
  )


def match_complete(user_id, repo):
  """Switch 'complete' to true in matches table for user"""
  from . import matcher
  try:
    exchange = repo.get_exchange(user_id)
    # Note: 0/1 used for 'complete' b/c Booleans not allowed in SimpleObjects
    exchange.my()['complete'] = 1
    repo.save_exchange(exchange)
  except RowMissingError as err:
    sm.warning(f"match_complete: match not found {user_id}")
  matcher.propagate_update_needed()

   
def add_chat_message(user_id, message, repo):
  exchange = repo.get_exchange(user_id)
  repo.add_chat(message=anvil.secrets.encrypt_with_key("new_key", message),
                now=sm.now(),
                exchange=exchange,
               )
  return _update_match_form_already_matched(user_id, exchange, repo)


def update_my_external(my_external, user_id, repo):
  try:
    exchange = repo.get_exchange(user_id)
    exchange.my()['external'] = int(my_external)
    repo.save_exchange(exchange)
  except RowMissingError:
    print("Exchange record not available to record my_external")


def submit_slider(value, user_id, repo):
  exchange = repo.get_exchange(user_id)
  exchange.my()['slider_value'] = value
  repo.save_exchange(exchange)
  return exchange.their()['slider_value']
  
  
def their_value(values, my_i):
  temp_values = [value for value in values]
  temp_values.pop(my_i)
  if len(temp_values) != 1:
    sm.warning(f"len(temp_values) != 1, but this function assumes dyads only")
  return temp_values[0]                     # return the remaining value
