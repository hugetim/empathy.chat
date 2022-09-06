import anvil.tables
from anvil.tables import app_tables
import anvil.tables.query as q
import anvil.server
from . import parameters as p
from . import notifies as n
from . import accounts
from . import server_misc as sm
from .server_misc import authenticated_callable
from . import portable as port
from .proposals import Proposal, ProposalTime
from anvil_extras.server_utils import timed
from anvil_extras.logging import TimerLogger


def _seconds_left(status, expire_date=None, ping_start=None):
  now = sm.now()
  if status in ["pinging", "pinged"]:
    if ping_start:
      confirm_match = p.CONFIRM_MATCH_SECONDS - (now - ping_start).total_seconds()
    else:
      confirm_match = p.CONFIRM_MATCH_SECONDS
    if status == "pinging":
      return confirm_match + 2*p.BUFFER_SECONDS # accounts for delay in response arriving
    elif status == "pinged":
      return confirm_match + p.BUFFER_SECONDS # accounts for delay in ping arriving
  elif status == "requesting":
    if expire_date:
      return (expire_date - now).total_seconds()
    else:
      return p.WAIT_SECONDS
  elif status in [None, "matched"]:
    return None
  else:
    print("matcher.seconds_left(s,lc,ps): " + status)


@anvil.server.background_task
def prune_old_matches():
  """Complete old commenced matches for all users"""
  import datetime
  assume_complete = datetime.timedelta(hours=p.ASSUME_COMPLETE_HOURS)
  now = sm.now()
  cutoff_m = now - assume_complete
  # Note: 0 used for 'complete' field b/c False not allowed in SimpleObjects
  old_matches = app_tables.matches.search(complete=[0],
                                          match_commence=q.less_than(cutoff_m),
                                         )
  for row in old_matches:
    _mark_matches_row_complete(row)
    
    
def _prune_newer_matches():
  """Complete no-show matches for all users"""
  if sm.DEBUG:
    print("_prune_newer_matches")
  import datetime
  now = sm.now()
  newer_matches = app_tables.matches.search(complete=[0],
                                            match_commence=q.less_than(now),
                                            present=q.not_([1]),
                                           )
  for row in newer_matches:
    duration = datetime.timedelta(minutes=row['proposal_time']['duration'])
    if now > row['match_commence'] + duration:
      _mark_matches_row_complete(row)


def _mark_matches_row_complete(row):
  temp = row['complete']
  for i in range(len(temp)):
    # Note: 1 used for 'complete' field b/c True not allowed in SimpleObjects
    temp[i] = 1
  row['complete'] = temp
    

@authenticated_callable
def init(time_zone):
  """Runs upon initializing app
  
  Side effects: prunes old proposals/matches,
                updates expire_date if currently requesting/ping
  """
  init_dict = _init_before_tests(time_zone)
  # if p.DEBUG_MODE and trust_level >= sm.TEST_TRUST_LEVEL:
  #   from . import server_auto_test
  #   server_auto_test.server_auto_tests()
  #   #anvil.server.launch_background_task('server_auto_tests')
  return init_dict


@timed
def _init_before_tests(time_zone):
  user, trust_level = accounts.initialize_session(time_zone)
  return _init_matcher(user, trust_level)


def _init_matcher(user, trust_level):
  partial_state_if_unchanged = _init_user_status(user)
  state = _get_state(user, partial_state_if_unchanged)
  propagate_update_needed(user)
  return {'trust_level': trust_level,
          'test_mode': trust_level >= sm.TEST_TRUST_LEVEL,
          'name': user['first_name'],
          'state': state,
         }


def _prune_all_expired_items():
  #Proposal.prune_all() # Not needed because this is done with every get_proposals
  _prune_newer_matches()
  #sm.prune_chat_messages() # moved to scheduled task


@anvil.tables.in_transaction
def _init_user_status(user):
  with TimerLogger("  _init_user_status", format="{name}: {elapsed:6.3f} s | {msg}") as timer:
    _prune_all_expired_items()
    timer.check("_prune_all_expired_items")
    partial_state = get_partial_state(user)
    timer.check("get_partial_state")
    if partial_state['status'] == 'pinging' and partial_state['seconds_left'] <= 0:
      _cancel_other(user)
    elif partial_state['status'] in ['pinged', 'requesting'] and partial_state['seconds_left'] <= 0:
      _cancel(user)
    elif partial_state['status'] == 'pinged':
      _match_commit(user)
      confirm_wait_helper(user)
    elif partial_state['status'] in ['requesting', 'pinging']:
      confirm_wait_helper(user)
    else:
      return partial_state
    return None

  
def confirm_wait_helper(user):
  """updates expire_date for current request"""
  if sm.DEBUG:
    print("confirm_wait_helper")
  current_proptime = ProposalTime.get_now_proposing(user)
  if current_proptime:
    current_proptime.confirm_wait()


@anvil.tables.in_transaction(relaxed=True)
def _get_proposals_upcomings(user):
  print("                      _get_proposals_upcomings")
  proposals = Proposal.get_port_view_items(user)
  upcomings = _get_upcomings(user)
  return proposals, upcomings


def propagate_update_needed(user=None):
  all_users = app_tables.users.search(update_needed=False)
  for u in all_users:
    if u != user:
      u['update_needed'] = True

      
@authenticated_callable
def get_state(user_id="", force_refresh=False):
  user = sm.get_acting_user(user_id)
  saved_state = anvil.server.session.get('state')
  if user['update_needed'] or not saved_state or force_refresh:
    _get_state(user)
  return anvil.server.session['state']


def _get_state(user, partial_state_if_known=None):
  """Returns state dict
  
  Side effects: prune proposals when status in [None]
  """
  with TimerLogger("          _get_state", format="{name}: {elapsed:6.3f} s | {msg}") as timer:
    state = partial_state_if_known if partial_state_if_known else get_partial_state(user)
    timer.check("get_partial_state")
    if state['status']:
      state['proposals'], state['upcomings'] = ([], [])
      state['prompts'] = []
    else:
      state['proposals'], state['upcomings'] = _get_proposals_upcomings(user)
      timer.check("_get_proposals_upcomings")
      state['prompts'] = sm.get_prompts(user)
      timer.check("get_prompts")
    anvil.server.session['state'] = state
    user['update_needed'] = False
    return state
  

def get_partial_state(user):
  """Returns status dict (only 'status' and 'seconds_left')
  ping_start: accept_date or, for "matched", match_commence
  assumes 2-person matches only
  """
  expire_date = None
  ping_start = None
  current_proptime = ProposalTime.get_now_proposing(user)
  if current_proptime:
    expire_date = current_proptime['expire_date']
    if current_proptime['fully_accepted']:
      status = "pinged"
      ping_start = current_proptime.ping_start
    else:
      status = "requesting"
  else:
    current_accept_time = ProposalTime.get_now_accepting(user)
    if current_accept_time:
      status = "pinging"
      ping_start = current_accept_time.ping_start
      expire_date = current_accept_time['expire_date']
    else:
      from .exchange_gateway import ExchangeRepository
      from .exceptions import RowMissingError
      try:
        this_exchange = ExchangeRepository().get_exchange(user.get_id())
        status = "matched"
        ping_start = this_exchange.start_dt
      except RowMissingError:
        status = None
  return {'status': status, 
          'seconds_left': _seconds_left(status, expire_date, ping_start), 
         }


def _get_upcomings(user):
  """Return list of user's upcoming matches"""
  match_dicts = []
  now = sm.now()
  for match in app_tables.matches.search(users=[user], 
                                         match_commence=q.greater_than(now)):
    port_users = [port.User(user_id=u.get_id(), name=u['first_name']) for u in match['users']
                   if u != user]
    match_dict = {'port_users': port_users,
                  'start_date': match['match_commence'],
                  'duration_minutes': ProposalTime(match['proposal_time'])['duration'],
                  'match_id': match.get_id(),
                 }
    match_dicts.append(match_dict)
  return match_dicts


@anvil.tables.in_transaction(relaxed=True)
def _cancel_match(user, match_id):
  if sm.DEBUG:
    print(f"_cancel_match, {match_id}")
  match = app_tables.matches.get_by_id(match_id)
  if match:
    users_to_notify = [u for u in match['users'] if u != user]    
    match_commence = match['match_commence']
    match.delete()
    return users_to_notify, match_commence
  else:
    return [], None
    

  
@authenticated_callable
def cancel_match(match_id, user_id=""):
  """Cancel pending match"""
  print(f"cancel_match, {match_id}, {user_id}")
  user = sm.get_acting_user(user_id)
  propagate_update_needed(user)
  users_to_notify, match_commence = _cancel_match(user, match_id)
  for u in users_to_notify:
    n.notify_match_cancel(u, start=match_commence, canceler_name=sm.name(user, to_user=u))
  return _get_state(user)


@authenticated_callable
def accept_proposal(proptime_id, user_id=""):
  """Add user_accepting
  
  Side effect: update proptime table with acceptance, if available
  """
  print(f"accept_proposal, {proptime_id}, {user_id}")
  user = sm.get_acting_user(user_id)
  proptime = ProposalTime.get_by_id(proptime_id)
  ping_needed = _accept_proposal(proptime, user)
  if ping_needed:
    proptime.ping()
  propagate_update_needed(user)
  return _get_state(user)


@anvil.tables.in_transaction
@timed
def _accept_proposal(proptime, user):
  partial_state = get_partial_state(user)
  ping_needed = proptime.attempt_accept(user, partial_state)
  return ping_needed


@authenticated_callable
def add_proposal(proposal, link_key="", user_id=""):
  """Return state, prop_id (None if cancelled or matching with another proposal)
  
  Side effects: Update proposal tables with additions, if valid; match if appropriate; notify
  """
  print(f"add_proposal, {user_id}")
  user = sm.get_acting_user(user_id)
  propagate_update_needed(user)
  prop_id = _add_proposal(user, proposal, link_key)
  return _get_state(user), prop_id


@timed
def _add_proposal(user, port_prop, link_key=""):
  """Return prop_id (None if cancelled or matching with another proposal)
  
  Side effects: Update proposal tables with additions, if valid; match if appropriate; notify
  """
  prop, other_prop_time_to_ping = _save_new_proposal(user, port_prop, link_key)
  if other_prop_time_to_ping:
    other_prop_time_to_ping.ping()
  if prop:
    prop.notify_add()
    return prop.get_id()
  else:
    return None


@anvil.tables.in_transaction
def _save_new_proposal(user, port_prop, link_key):
  """Return prop (None if cancelled or matching with another proposal), other_prop_to_ping (if applicable)
  
  Side effects: Update proposal tables with additions, if valid; match if appropriate
  """
  prop = Proposal.add(user, port_prop)
  if port_prop.start_now:
    prop, other_prop_time_to_ping = _process_now_proposal_edit(user, port_prop, prop)
  else:
    other_prop_time_to_ping = None
  if prop and link_key:
    prop.add_to_invite(link_key)
  return prop, other_prop_time_to_ping


def _overlapping_others_now_proposal(user, my_now_proposal, my_now_port_prop):
  my_duration = my_now_port_prop.times[0].duration
  current_port_props = Proposal.get_port_proposals(user)
  now_port_props = [p for p in current_port_props if p.start_now and not p.own]
  for other_port_prop in now_port_props:
    if (my_now_proposal.is_visible(sm.get_other_user(other_port_prop.user.user_id))
        and my_duration == other_port_prop.times[0].duration):
      other_prop_time = ProposalTime.get_by_id(other_port_prop.times[0].time_id)
      return other_prop_time
  return None
  

@authenticated_callable
def edit_proposal(port_prop, user_id=""):
  """Return state, prop_id (None if cancelled or matching with another proposal)
  
  Side effects: Update proposal tables with revision, if valid; match if appropriate; notify
  """
  print(f"edit_proposal, {user_id}")
  user = sm.get_acting_user(user_id)
  propagate_update_needed(user)
  prop_id = _edit_proposal(user, port_prop)
  return _get_state(user), prop_id


@timed
def _edit_proposal(user, port_prop):
  """Return prop_id (None if cancelled or matching with another proposal)
  
  Side effects: Update proposal tables with revision, if valid; match if appropriate; notify
  """
  prop = Proposal.get_by_id(port_prop.prop_id)
  old_port_prop = prop.portable(user)
  prop, other_prop_time_to_ping = _save_proposal_edit(user, port_prop, prop)
  if other_prop_time_to_ping:
    other_prop_time_to_ping.ping()
  if prop:
    prop.notify_edit(port_prop, old_port_prop)
    return prop.get_id()
  else:
    return None


@anvil.tables.in_transaction
def _save_proposal_edit(user, port_prop, prop):
  """Return prop (None if cancelled or matching with another proposal), other_prop_time_to_ping (if applicable)
  
  Side effects: Update proposal tables with revision, if valid; match if appropriate
  """
  prop.update(port_prop)
  if port_prop.start_now:
    return _process_now_proposal_edit(user, port_prop, prop)
  else:
    return prop, None
  


def _process_now_proposal_edit(user, port_prop, prop):
  """Return prop (None if cancelled or matching with another proposal), other_prop_time_to_ping (if applicable)
  
  Side effects: Update proposal tables with additional revisions, if any; match if appropriate
  """
  status = get_partial_state(user)['status']
  available_for_now_proposal = (status is None)
  if available_for_now_proposal:
    return _process_now_proposal_edit_available(user, port_prop, prop)
  else:
    prop.cancel_all_times()
    return None, None
  


def _process_now_proposal_edit_available(user, port_prop, prop):
  """Return prop (None if matching with another proposal), other_prop_time_to_ping (if applicable)
  
  Side effects: Update proposal tables with additional revisions, if any; match if appropriate
  """
  overlapping_prop_time = _overlapping_others_now_proposal(user, prop, port_prop)
  if overlapping_prop_time:
    prop.cancel_all_times()
    other_prop_time_to_ping = _accept_overlapping_proposal(user, overlapping_prop_time)
    return None, other_prop_time_to_ping
  else:
    return prop, None
  

def _accept_overlapping_proposal(user, overlapping_prop_time):
  """Return overlapping proposal if ping needed (else None)
  
  Side effects: match
  """
  ping_needed = overlapping_prop_time.accept(user, status=None)
  return overlapping_prop_time if ping_needed else None

  
@authenticated_callable
def cancel_time(proptime_id, user_id=""):
  """Remove proptime"""
  print(f"cancel_time, {proptime_id}, {user_id}")
  user = sm.get_acting_user(user_id)
  propagate_update_needed(user)
  proptime = ProposalTime.get_by_id(proptime_id)
  port_prop = proptime.proposal.portable(user)
  if len(port_prop.times) > 1:
    [port_time_to_cancel] = [port_time for port_time in port_prop.times if port_time.time_id == proptime_id]
    port_prop.times.remove(port_time_to_cancel)
    prop_id = _edit_proposal(user, port_prop) # can ignore prop_id because not port_prop.start_now
  else:
    proptime.notify_cancel()
    _cancel_in_transaction(user, proptime_id)
  return _get_state(user)


def _cancel(user, proptime_id=None):
  if sm.DEBUG:
    print(f"_cancel, {proptime_id}")
  if proptime_id:
    proptime = ProposalTime.get_by_id(proptime_id)
  else:
    proptime = ProposalTime.get_now(user)
  if proptime:
    proptime.cancel_this(user)


@anvil.tables.in_transaction
@timed
def _cancel_in_transaction(user, proptime_id=None):
  return _cancel(user, proptime_id)


@authenticated_callable
def cancel_accept(proptime_id=None, user_id=""):
  """Remove user accepting"""
  print(f"cancel_accept, {proptime_id}, {user_id}")
  user = sm.get_acting_user(user_id)
  propagate_update_needed(user)
  _cancel_in_transaction(user, proptime_id)
  return _get_state(user)


@authenticated_callable
def cancel_now(proptime_id=None, user_id=""):
  """Remove proptime and cancel pending match (if applicable)"""
  print(f"cancel_now, {proptime_id}, {user_id}")
  user = sm.get_acting_user(user_id)
  if proptime_id:
    proptime = ProposalTime.get_by_id(proptime_id)
    if proptime:
      proptime.notify_cancel()
  propagate_update_needed()
  _cancel_in_transaction(user, proptime_id)
  return _get_state(user)


def _cancel_other(user, proptime_id=None):
  if sm.DEBUG:
    print("_cancel_other", proptime_id)
  if proptime_id:
    proptime = ProposalTime.get_by_id(proptime_id)
  else:
    proptime = ProposalTime.get_now(user)
  if proptime:
    proptime.cancel_other(user)

    
# @anvil.tables.in_transaction
# @timed
# def _cancel_other_in_transaction(user, proptime_id=None):
#   return _cancel_other(user, proptime_id)


# @authenticated_callable
# def cancel_other(proptime_id=None, user_id=""):
#   """Upon failure of other to confirm match
#   cancel match (if applicable)--and cancel their request
#   """
#   print(f"cancel_other, {proptime_id}, {user_id}")
#   user = sm.get_acting_user(user_id)
#   propagate_update_needed()
#   _cancel_other_in_transaction(user, proptime_id)
#   return _get_state(user)


@authenticated_callable
def match_commit(proptime_id=None, user_id=""):
  """Upon first commence of "now", copy row over and delete "matching" row.
  Should not cause error if already commenced
  """
  print(f"match_commit, {proptime_id}, {user_id}")
  user = sm.get_acting_user(user_id)
  propagate_update_needed(user)
  _match_commit_in_transaction(user, proptime_id)
  return _get_state(user)


@anvil.tables.in_transaction
@timed
def _match_commit_in_transaction(user, proptime_id=None):
  return _match_commit(user, proptime_id)


def _match_commit(user, proptime_id=None):
  if sm.DEBUG:
    print("_match_commit")
  if proptime_id:
    print("proptime_id")
    current_proptime = ProposalTime.get_by_id(proptime_id)
  else:
    current_proptime = ProposalTime.get_now(user)
  if current_proptime:
    if current_proptime['fully_accepted']:
      if current_proptime['start_now']:
        match_start = sm.now()
      else:
        match_start = current_proptime['start_date']
      users = current_proptime.all_users()
      new_match = app_tables.matches.add_row(users=users,
                                             proposal_time=current_proptime._row,
                                             match_commence=match_start,
                                             present=[0]*len(users),
                                             complete=[0]*len(users),
                                             slider_values=[""]*len(users),
                                             external=[0]*len(users),
                                             late_notified=[0]*len(users),
                                            )
      # Note: 0 used for 'complete' b/c False not allowed in SimpleObjects
      proposal = current_proptime.proposal
      proposal.cancel_all_times()
      if not current_proptime['start_now']:
        current_proptime.ping()
