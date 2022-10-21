import anvil.secrets
from .server_misc import authenticated_callable
from . import server_misc as sm
from . import network_interactor as ni
from .exceptions import RowMissingError
from .exchange_gateway import ExchangeRepository
from .exchanges import Exchange, Format


repo = ExchangeRepository()


def reset_repo():
  global repo
  repo = ExchangeRepository()

  
@authenticated_callable
def init_match_form(user_id=""):
  """Return current_proptime id (or None), jitsi_code, duration (or Nones), my_slider_value
  
  Side effect: if already matched, set this_match['present']"""
  print(f"init_match_form, {user_id}")
  try:
    return _init_match_form_already_matched(user_id)
  except RowMissingError as err:
    return _init_match_form_not_matched(user_id)


def _init_match_form_already_matched(user_id):
  exchange = repo.get_exchange(user_id, to_join=True)
  exchange.my['present'] = 1
  repo.save_exchange(exchange)
  other_user = sm.get_other_user(exchange.their['user_id'])
  other_user['update_needed'] = True
  return None, exchange.room_code, exchange.exchange_format.duration, exchange.my['slider_value']


def _init_match_form_not_matched(user_id):
  from .proposals import ProposalTime
  user = sm.get_acting_user(user_id)
  current_proptime = ProposalTime.get_now(user)
  if current_proptime:
    return _init_match_form_requesting(current_proptime)
  else:
    sm.warning(f"_init_match_form_not_matched request not found for {user_id}")
    return None, None, None, ""


def _init_match_form_requesting(current_proptime):
  jitsi_code, duration = current_proptime.get_match_info()
  return current_proptime.get_id(), jitsi_code, duration, ""


@authenticated_callable
def update_match_form(user_id=""):
  """Return match_state dict
  
  Side effects: Update match['present'], late notifications, confirm_wait"""
  try:
    exchange = repo.get_exchange(user_id, to_join=True)
    return _update_match_form_already_matched(user_id, exchange)
  except RowMissingError as err:
    return _update_match_form_not_matched(user_id)
  

def _update_match_form_already_matched(user_id, exchange):
  user = sm.get_acting_user(user_id)
  changed = not exchange.my['present']
  exchange.my['present'] = 1
  #this_match, i = repo.exchange_i()
  other_user = sm.get_other_user(exchange.their['user_id'])
  if exchange.late_notify_needed(sm.now()):
    from . import notifies as n
    n.notify_late_for_chat(other_user, exchange.start_dt, [user])
    changed = True
    exchange.their['late_notified'] = 1
  if changed:
    repo.save_exchange(exchange)
    other_user['update_needed'] = True
  how_empathy_list = [user['how_empathy'], other_user['how_empathy']]
  messages_out = ni.get_messages(other_user, user)
  their_name = other_user['first_name']
  return dict(
    status="matched",
    how_empathy_list=how_empathy_list,
    their_name=their_name,
    message_items=messages_out,
    my_slider_value=exchange.my['slider_value'],
    their_slider_value=exchange.their['slider_value'],
    their_external=exchange.their['external'],
    their_complete=exchange.their['complete'],
  )

  
def _update_match_form_not_matched(user_id):
  from . import matcher
  user = sm.get_acting_user(user_id)
  matcher.confirm_wait_helper(user)
  partial_state = matcher.get_partial_state(user)
  matcher.propagate_update_needed(user)
  return dict(
    status=partial_state['status'],
  )


def create_new_match_from_proptime(proptime, user, present):
  room_code, duration = proptime.get_match_info()
  match_start = sm.now() if proptime['start_now'] else proptime['start_date']
  participants = [dict(user_id=u.get_id(),
                       present=int(present), # if result of a start_now request, go directly in
                       complete=0,
                       slider_value="", # see exchange_controller._slider_value_missing()
                       late_notified=0,
                       external=0,
                      ) for u in proptime.all_users()]
  # Note: 0 used for 'complete' b/c False not allowed in SimpleObjects
  exchange = Exchange(None, room_code, participants, proptime['start_now'], match_start, Format(duration), user.get_id())
  #exchange.my['present'] = int(present)
  repo.create_exchange(exchange, proptime)


@authenticated_callable
def match_complete(user_id=""):
  """Switch 'complete' to true in matches table for user"""
  print(f"match_complete, {user_id}")
  from . import matcher
  try:
    exchange = repo.get_exchange(user_id)
    # Note: 0/1 used for 'complete' b/c Booleans not allowed in SimpleObjects
    exchange.my['complete'] = 1
    if exchange.their['present'] == 0:
      from . import notifies as n
      user = sm.get_acting_user()
      other_user = sm.get_other_user(exchange.their['user_id'])
      n.notify_match_cancel_bg(other_user, exchange.start_dt, canceler_name=sm.name(user, to_user=other_user))
      exchange.their['complete'] = 1
    repo.save_exchange(exchange)
    matcher.propagate_update_needed()
  except RowMissingError as err:
    sm.warning(f"match_complete: match not found {user_id}")

 
@authenticated_callable
def add_chat_message(message="[blank test message]", user_id=""):
  print(f"add_chat_message, {user_id}, '[redacted]'")
  exchange = repo.get_exchange(user_id)
  repo.add_chat(message=anvil.secrets.encrypt_with_key("new_key", message),
                now=sm.now(),
                exchange=exchange,
               )
  return _update_match_form_already_matched(user_id, exchange)


@authenticated_callable
def update_my_external(my_external, user_id=""):
  print(f"update_my_external, {my_external}, {user_id}")
  try:
    exchange = repo.get_exchange(user_id)
    exchange.my['external'] = int(my_external)
    repo.save_exchange(exchange)
  except RowMissingError:
    print("Exchange record not available to record my_external")


@authenticated_callable
def submit_slider(value, user_id=""):
  """Return their_value"""
  print(f"submit_slider, '[redacted]', {user_id}")
  exchange = repo.get_exchange(user_id)
  exchange.my['slider_value'] = value
  repo.save_exchange(exchange)
  return exchange.their['slider_value']
