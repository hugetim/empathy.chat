import anvil.server
import anvil.secrets
from anvil import tables
from .server_misc import authenticated_callable
from . import server_misc as sm
from . import network_interactor as ni
from . import request_interactor as ri
from .exceptions import RowMissingError, UnauthorizedError
from . import exchange_gateway
from .exchanges import Exchange
from .requests import ExchangeFormat
from . import portable as port
from . import helper as h
from . import parameters as p


repo = exchange_gateway


def reset_repo():
  global repo
  repo = exchange_gateway


def upcoming_match_dicts(user):
  # can shift to just returning exchanges
  out = []
  user_id = user.get_id()
  for exchange in repo.exchanges_by_user(user):
    exchange.set_my(user_id)
    if not exchange.my['complete_dt']:
      out.append(_match_dict(user_id, exchange))
  return out


def _match_dict(user_id, exchange):
  other_user_ids = [p['user_id'] for p in exchange.participants
                    if p['user_id'] != user_id]
  port_users = [port.User(user_id=u_id, name=sm.get_other_user(u_id)['first_name']) 
                for u_id in other_user_ids]
  return {'port_users': port_users,
          'start_date': exchange.start_dt,
          'duration_minutes': exchange.exchange_format.duration,
          'note': exchange.exchange_format.note,
          'match_id': exchange.exchange_id,
         }


def current_user_exchange(user, to_join=False, record=False):
  """Return earliest if multiple current"""
  import datetime
  out = None
  now_plus = sm.now() + datetime.timedelta(minutes=p.START_EARLY_MINUTES)
  exchange_records = list(repo.exchanges_by_user_starting_prior_to(user, now_plus, records=True))
  user_id = user.get_id()
  for er in sorted(exchange_records, key=lambda er: er.entity.start_dt):
    er.entity.set_my(user_id)
    if (to_join or er.entity.my['entered_dt']) and not er.entity.my['complete_dt']:
      out = er if record else er.entity
      break
  return out


def commence_user_exchange(user):
  exchange_record = current_user_exchange(user, to_join=True, record=True)
  exchange_record.commence()
  user.update()


@tables.in_transaction
def commence_user_exchange_in_transaction(user):
  commence_user_exchange(user)


@authenticated_callable
def join_exchange(exchange_id):
  user = sm.get_acting_user()
  user_id = user.get_id()
  exchange_record = repo.ExchangeRecord.from_id(exchange_id)
  if user_id not in exchange_record.entity.user_ids:
    raise UnauthorizedError("You are not a participant in that exchange.")
  exchange_record.entity.set_my(user_id)
  _join_exchange_update(user, exchange_record)


@tables.in_transaction
def _join_exchange_update(user, exchange_record):
  exchange_record.entity.my['entered_dt'] = sm.now()
  exchange_record.save()
  user['status'] = "matched"


@sm.background_task_with_reporting
def prune_old_exchanges():
  """Switch to current=False old commenced exchanges for all users"""
  import datetime
  assume_complete = datetime.timedelta(hours=p.ASSUME_COMPLETE_HOURS)
  now = sm.now()
  cutoff_dt = now - assume_complete
  old_exchange_records = repo.exchanges_starting_prior_to(cutoff_dt, records=True)
  for er in old_exchange_records:
    er.end_in_transaction()


def prune_no_show_exchanges():
  """Complete no-show exchanges for all users"""
  if sm.DEBUG:
    print("_prune_no_show_exchanges")
  import datetime
  now = sm.now()
  exchange_records = repo.exchanges_starting_prior_to(now, records=True)
  for er in exchange_records:
    if not er.entity.any_appeared:
      duration = datetime.timedelta(minutes=er.entity.exchange_format.duration)
      if now > er.entity.start_dt + duration:
        er.end()


def ping(user, exchange):
  user_ids = exchange.user_ids.copy()
  user_ids.remove(user.get_id())
  anvil.server.launch_background_task(
    'pings',
    user_ids=user_ids,
    start=None if exchange.start_now else exchange.start_dt,
    duration=exchange.exchange_format.duration,
  )    

  
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
  user = sm.get_acting_user(user_id)
  exchange_record = current_user_exchange(user, to_join=True, record=True)
  if not exchange_record: raise RowMissingError("no current exchange")
  exchange = exchange_record.entity
  exchange.start_appearance(sm.now())
  exchange_record.save()
  other_user = sm.get_other_user(exchange.their['user_id'])
  other_user['update_needed'] = True
  return None, exchange.room_code, exchange.exchange_format.duration, exchange.my['slider_value']


def _init_match_form_not_matched(user_id):
  user = sm.get_acting_user(user_id)
  current_request = ri.now_request(user)
  if current_request:
    return _init_match_form_requesting(current_request)
  else:
    sm.warning(f"_init_match_form_not_matched request not found for {user_id}")
    return None, None, None, ""


def _init_match_form_requesting(current_request):
  jitsi_code = h.new_jitsi_code()
  return current_request.request_id, jitsi_code, current_request.exchange_format.duration, ""


@authenticated_callable
def update_match_form(user_id=""):
  """Return match_state dict
  
  Side effects: Update match['present'], late notifications, confirm_wait"""
  user = sm.get_acting_user(user_id)
  exchange = current_user_exchange(user, to_join=True)
  if exchange:
    return _update_match_form_already_matched(user, exchange)
  else:
    return _update_match_form_not_matched(user)
  

def _update_match_form_already_matched(user, exchange):
  changed = bool(not exchange.my['appearances'])
  exchange.continue_appearance(sm.now())
  #this_match, i = repo.exchange_i()
  other_user = sm.get_other_user(exchange.their['user_id'])
  if exchange.late_notify_needed(sm.now()):
    from . import notifies as n
    n.notify_late_for_chat(other_user, exchange.start_dt, [user])
    changed = True
    exchange.their['late_notified'] = True
  if changed:
    er = repo.ExchangeRecord(exchange, exchange.exchange_id)
    er.save()
    other_user['update_needed'] = True
  how_empathy_list = [user['how_empathy'], other_user['how_empathy']]
  messages_out = ni.get_messages(other_user, user)
  their_name = other_user['first_name']
  return dict(
    status=user['status'],
    how_empathy_list=how_empathy_list,
    their_name=their_name,
    message_items=messages_out,
    my_slider_value=exchange.my['slider_value'],
    their_slider_value=exchange.their['slider_value'],
    their_external=exchange.their['video_external'],
    their_complete=exchange.their['complete_dt'],
    jitsi_code=exchange.room_code,
  )

  
def _update_match_form_not_matched(user):
  from . import matcher
  request_record = ri.now_request(user, record=True)
  if request_record:
    ri.confirm_wait(request_record)
  matcher.propagate_update_needed(user)
  return dict(
    status=user['status'],
  )


# def create_new_match_from_proptime(proptime, user, present):
#   room_code, duration = proptime.get_match_info()
#   match_start = sm.now() if proptime['start_now'] else proptime['start_date']
#   participants = [dict(user_id=u.get_id(),
#                        present=int(present), # if result of a start_now request, go directly in
#                        complete=0,
#                        slider_value="", # see exchange_controller._slider_value_missing()
#                        late_notified=0,
#                        external=0,
#                       ) for u in proptime.all_users()]
#   # Note: 0 used for 'complete' b/c False not allowed in SimpleObjects
#   exchange = Exchange(None, room_code, participants, proptime['start_now'], match_start, ExchangeFormat(duration), user.get_id())
#   #exchange.my['present'] = int(present)
#   repo.create_exchange(exchange, proptime)


class ExchangeManager:
  @tables.in_transaction
  def complete_exchange(self, user):
    exchange_record = current_user_exchange(user, record=True)
    exchange = exchange_record.entity
    self.start_dt = exchange.start_dt
    sm.my_assert(exchange.size <= 2, "code below and _complete_exchange assumes dyads")
    self.user_ids_not_yet_entered = [exchange.their['user_id']] if not exchange.their['entered_dt'] else []
    _complete_exchange(exchange_record, user)


@authenticated_callable
def match_complete(user_id=""):
  """Switch 'complete' to true in matches table for user"""
  print(f"match_complete, {user_id}")
  from . import matcher
  from . import notifies as n
  user = sm.get_acting_user(user_id)
  exchange_manager = ExchangeManager()
  exchange_manager.complete_exchange(user)
  for other_user_id in exchange_manager.user_ids_not_yet_entered:
    other_user = sm.get_other_user(other_user_id)
    n.notify_match_cancel_bg(other_user, exchange_manager.start_dt, canceler_name=sm.name(user, to_user=other_user))
  matcher.propagate_update_needed()


def _complete_exchange(exchange_record, user):
  exchange = exchange_record.entity
  reset_my_status = exchange.current and exchange.my['entered_dt'] and not exchange.my['complete_dt']
  exchange.my['complete_dt'] = sm.now()
  if exchange.their['complete_dt'] or not exchange.their['entered_dt']:
    exchange.current = False
  _save_complete_exchange(exchange_record, user, reset_my_status)


def _save_complete_exchange(exchange_record, user, reset_my_status):
  if reset_my_status:
    user['status'] = None
  exchange_record.save()


def cancel_exchange(user, exchange_id):
  if sm.DEBUG:
    print(f"cancel_exchange, {exchange_id}")
  exchange_record = repo.ExchangeRecord.from_id(exchange_id)
  users_to_notify = [u for u in exchange_record.users if u != user]
  exchange_record.end_in_transaction()
  return users_to_notify, exchange_record.entity.start_dt

 
@authenticated_callable
def add_chat_message(message="[blank test message]", user_id=""):
  print(f"add_chat_message, {user_id}, '[redacted]'")
  user = sm.get_other_user(user_id)
  exchange_record = current_user_exchange(user, record=True)
  repo.add_chat(
    from_user=user,
    message=anvil.secrets.encrypt_with_key("new_key", message),
    now=sm.now(),
    users=exchange_record.users,
  )
  return _update_match_form_already_matched(user, exchange_record.entity)


@authenticated_callable
def update_my_external(my_external, user_id=""):
  print(f"update_my_external, {my_external}, {user_id}")
  user = sm.get_acting_user(user_id)
  exchange_record = current_user_exchange(user, record=True)
  if exchange_record:
    exchange_record.entity.my['video_external'] = bool(my_external)
    exchange_record.save()
  else:
    print("Exchange record not available to record my_external")


@authenticated_callable
def submit_slider(value, user_id=""):
  """Return their_value"""
  print(f"submit_slider, '[redacted]', {user_id}")
  user = sm.get_acting_user(user_id)
  exchange_record = current_user_exchange(user, record=True)
  exchange_record.entity.my['slider_value'] = value
  exchange_record.save()
  return exchange_record.entity.their['slider_value']
