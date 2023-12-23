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
  return {'other_user_ids': exchange.theirs['user_id'],
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
  _join_exchange_update(user, exchange_id)


@tables.in_transaction(relaxed=True)
def _join_exchange_update(user, exchange_id):
  user_id = user.get_id()
  exchange_record = repo.ExchangeRecord.from_id(exchange_id)
  if user_id not in exchange_record.entity.user_ids:
    raise UnauthorizedError("You are not a participant in that exchange.")
  exchange_record.entity.set_my(user_id)
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
  other_users = [u for u in exchange_record.users if u != user]
  with tables.batch_update:
    for u in other_users:
      u['update_needed'] = True
  return dict(request_id=None,
              jitsi_code=exchange.room_code,
              duration=exchange.exchange_format.duration,
              my_slider_value=exchange.my['slider_value'],
              my_how_empathy=user['how_empathy'],
             )


def _init_match_form_not_matched(user_id):
  user = sm.get_acting_user(user_id)
  current_request = ri.now_request(user)
  if current_request:
    return _init_match_form_requesting(current_request)
  else:
    sm.warning(f"_init_match_form_not_matched request not found for {user_id}")
    return dict()


def _init_match_form_requesting(current_request):
  jitsi_code = h.new_jitsi_code()
  return dict(request_id=current_request.request_id,
              jitsi_code=jitsi_code,
              duration=current_request.exchange_format.duration,
             )


@authenticated_callable
def update_match_form(user_id=""):
  """Return match_state dict
  
  Side effects: Update match['present'], late notifications, confirm_wait"""
  user = sm.get_acting_user(user_id)
  exchange_record = current_user_exchange(user, to_join=True, record=True)
  if exchange_record:
    return _update_match_form_already_matched(user, exchange_record)
  else:
    return _update_match_form_not_matched(user)
  

def _update_match_form_already_matched(user, exchange_record):
  exchange = exchange_record.entity
  changed = bool(not exchange.my['appearances'])
  exchange.continue_appearance(sm.now())
  other_users = [u for u in exchange_record.users if u != user]
  user_ids_to_late_notify = exchange.user_ids_to_late_notify(sm.now())
  if user_ids_to_late_notify:
    _notify_late_for_chat(user_ids_to_late_notify, exchange_record, user)
    changed = True
    for u_id in user_ids_to_late_notify:
      exchange.participant_by_id(u_id)['late_notified'] = True
  if changed:
    er = repo.ExchangeRecord(exchange, exchange.exchange_id)
    er.save()
    with tables.batch_update:
      for u in other_users:
        u['update_needed'] = True
  messages_out = ni.get_message_dicts(user, other_users[0]) if len(other_users) == 1 else ni.get_message_dicts(user, messages=repo.get_exchange_messages(exchange_record, user))
  them = [dict(
    name=u['first_name'],
    how_empathy=u['how_empathy'],
    slider_value=exchange.participant_by_id(u.get_id())['slider_value'],
    external=exchange.participant_by_id(u.get_id())['video_external'],
    complete=exchange.participant_by_id(u.get_id())['complete_dt'],
  ) for u in other_users]
  return dict(
    status=user['status'],
    them=them,
    my_slider_value=exchange.my['slider_value'],
    message_items=messages_out,
    jitsi_code=exchange.room_code,
  )


def _notify_late_for_chat(user_ids_to_late_notify, exchange_record, user):
  anvil.server.launch_background_task(
    'late_notify',
    [u for u in exchange_record.users if u.get_id() in user_ids_to_late_notify],
    exchange_record.entity.start_dt,
    [u for u in exchange_record.users if u.get_id() not in user_ids_to_late_notify],
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


def ping_cancel(user):
  from . import notifies as n
  exchange_manager = ExchangeManager()
  exchange_manager.ping_cancel(user)
  for u in exchange_manager.users_to_notify:
    n.notify_match_cancel_bg(u, start=None, canceler_name=sm.name(user, to_user=u))


class ExchangeManager:
  @tables.in_transaction
  def complete_exchange(self, user):
    exchange_record = current_user_exchange(user, record=True)
    exchange = exchange_record.entity
    self.start_dt = exchange.start_dt
    self.user_ids_not_yet_entered = [p['user_id'] for p in exchange.others if not p['entered_dt']]
    _complete_exchange(exchange_record, user)

  @tables.in_transaction(relaxed=True)
  def cancel_exchange(self, user, exchange_id):
    if sm.DEBUG:
      print(f"cancel_exchange, {exchange_id}")
    exchange_record = repo.ExchangeRecord.from_id(exchange_id)
    self.users_to_notify = [u for u in exchange_record.users if u != user]
    exchange_record.end()
    self.start_dt = exchange_record.entity.start_dt

  @tables.in_transaction
  def ping_cancel(self, user):
    exchange_record = current_user_exchange(user, to_join=True, record=True)
    if sm.DEBUG:
      print(f"ping_cancel, {exchange_record.record_id}")
    self.users_to_notify = [u for u in exchange_record.users if u != user]
    exchange_record.ping_cancel(exchange_record.users)
    self.start_dt = exchange_record.entity.start_dt


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
  if all([(p['complete_dt'] or not p['entered_dt']) for p in exchange.others]):
    exchange.current = False
  _save_complete_exchange(exchange_record, user, reset_my_status)


def _save_complete_exchange(exchange_record, user, reset_my_status):
  if reset_my_status:
    user['status'] = None
  exchange_record.save()


@authenticated_callable
def cancel_match(match_id, user_id=""):
  """Cancel pending match"""
  from . import matcher
  from . import notifies as n
  print(f"cancel_match, {match_id}, {user_id}")
  user = sm.get_acting_user(user_id)
  exchange_manager = ExchangeManager()
  exchange_manager.cancel_exchange(user, match_id)
  for u in exchange_manager.users_to_notify:
    n.notify_match_cancel_bg(u, start=exchange_manager.start_dt, canceler_name=sm.name(user, to_user=u))
  matcher.propagate_update_needed(user)
  return matcher.get_state(user.get_id(), force_refresh=True)

 
@authenticated_callable
def add_chat_message(message="[blank test message]", user_id=""):
  print(f"add_chat_message, {user_id}, '[redacted]'")
  user = sm.get_other_user(user_id)
  exchange_record = current_user_exchange(user, record=True)
  if len(exchange_record.users) <= 2:
    repo.add_chat(
      from_user=user,
      message=anvil.secrets.encrypt_with_key("new_key", message),
      now=sm.now(),
      users=exchange_record.users,
    )
  else:
    repo.add_exchange_message(
      from_user=user,
      message=anvil.secrets.encrypt_with_key("new_key", message),
      now=sm.now(),
      exchange_record=exchange_record,
    )
  return _update_match_form_already_matched(user, exchange_record)


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
  their_slider_values = exchange_record.entity.theirs['slider_value']
  return their_slider_values
