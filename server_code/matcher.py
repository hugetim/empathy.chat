import anvil.users
import anvil.tables
from anvil.tables import app_tables
import anvil.tables.query as q
import anvil.server
from . import parameters as p
from . import notifies as n
from . import server_misc as sm
from .server_misc import authenticated_callable
from . import portable as port
from .proposals import Proposal, ProposalTime
from anvil_extras.server_utils import timed


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

       
def _prune_matches():
  """Complete old commenced matches for all users"""
  import datetime
  if sm.DEBUG:
    print("_prune_matches")
  assume_complete = datetime.timedelta(hours=p.ASSUME_COMPLETE_HOURS)
  cutoff_m = sm.now() - assume_complete
  # Note: 0 used for 'complete' field b/c False not allowed in SimpleObjects
  old_matches = app_tables.matches.search(complete=[0],
                                          match_commence=q.less_than(cutoff_m),
                                         )
  for row in old_matches:
    temp = row['complete']
    for i in range(len(temp)):
      # Note: 1 used for 'complete' field b/c True not allowed in SimpleObjects
      temp[i] = 1
    row['complete'] = temp


@authenticated_callable
@timed
def init(time_zone):
  """
  Runs upon initializing app
  Side effects: prunes old proposals/matches,
                updates expire_date if currently requesting/ping
  """
  print("('init')")
  # Initialize user info
  user = sm.initialize_session(time_zone)
  return _init(user)


def _init(user):
  _prune_all_expired_items()
  _init_user_status(user)
  state = _init_get_final_state(user)
  propagate_update_needed(user)
  return {'trust_level': user['trust_level'],
          'test_mode': user['trust_level'] >= sm.TEST_TRUST_LEVEL,
          'name': user['first_name'],
          'state': state,
         }


@anvil.tables.in_transaction
def _prune_all_expired_items():
  #Proposal.prune_all() # Not needed because this is done with every get_proposals
  _prune_matches()
  sm.prune_chat_messages()


@anvil.tables.in_transaction
@timed
def _init_user_status(user):
  partial_state = get_status(user)
  if partial_state['status'] == 'pinging' and partial_state['seconds_left'] <= 0:
    _cancel_other(user)
  elif partial_state['status'] in ['pinged', 'requesting'] and partial_state['seconds_left'] <= 0:
    _cancel(user)
  elif partial_state['status'] == 'pinged':
    _match_commit(user)
    confirm_wait_helper(user)
  elif partial_state['status'] in ['requesting', 'pinging']:
    confirm_wait_helper(user)

    
@anvil.tables.in_transaction
def _init_get_final_state(user):
  anvil.server.session['state'] = _get_state(user)
  user['update_needed'] = False
  return anvil.server.session['state']

  
def confirm_wait_helper(user):
  """updates expire_date for current request"""
  if sm.DEBUG:
    print("confirm_wait_helper")
  current_proptime = ProposalTime.get_now_proposing(user)
  if current_proptime:
    current_proptime.confirm_wait()


@authenticated_callable
@anvil.tables.in_transaction
def get_proposals_upcomings(user_id=""):
  user = sm.get_user(user_id)
  proposals = Proposal.get_port_view_items(user)
  upcomings = _get_upcomings(user)
  return proposals, upcomings


def propagate_update_needed(user=None):
  all_users = app_tables.users.search()
  for u in all_users:
    if u != user:
      u['update_needed'] = True

      
@authenticated_callable
@anvil.tables.in_transaction
def get_state(user_id="", force_refresh=False):
  user = sm.get_user(user_id)
  saved_state = anvil.server.session.get('state')
  if user['update_needed'] or not saved_state or force_refresh:
    anvil.server.session['state'] = _get_state(user)
    user['update_needed'] = False
  return anvil.server.session['state']


def _get_state(user):
  """Returns state dict
  
  Side effects: prune proposals when status in [None]
  """
  state = get_status(user)
  state['proposals'] = [] if state['status'] else Proposal.get_port_view_items(user)
  state['upcomings'] = [] if state['status'] else _get_upcomings(user)
  state['prompts'] = [] if state['status'] else sm.get_prompts(user)
  return state
  

def get_status(user):
  """Returns status dict (only 'status' and 'seconds_left')
  ping_start: accept_date or, for "matched", match_commence
  assumes 2-person matches only
  """
  if sm.DEBUG:
    print("_get_status")
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
        this_match = ExchangeRepository(user).exchange
        status = "matched"
        ping_start = this_match['match_commence']
      except RowMissingError:
        status = None
  return {'status': status, 
          'seconds_left': _seconds_left(status, expire_date, ping_start), 
         }


def _get_upcomings(user):
    """Return list of user's upcoming matches"""
    if sm.DEBUG:
      print("_get_upcomings")
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

 
def _cancel_match(user, match_id):
  if sm.DEBUG:
    print(f"_cancel_match, {match_id}")
  match = app_tables.matches.get_by_id(match_id)
  if match:
    for u in match['users']:
      if u != user:
        n.notify_match_cancel(u, start=match['match_commence'], canceler_name=sm.name(user, to_user=u))
    match.delete()

  
@authenticated_callable
@anvil.tables.in_transaction
def cancel_match(match_id, user_id=""):
  """Cancel pending match"""
  print(f"cancel_match, {match_id}, {user_id}")
  user = sm.get_user(user_id)
  propagate_update_needed()
  _cancel_match(user, match_id)
  return _get_state(user)


@authenticated_callable
@anvil.tables.in_transaction
def accept_proposal(proptime_id, user_id=""):
  """Add user_accepting
  
  Side effect: update proptime table with acceptance, if available
  """
  print(f"accept_proposal, {proptime_id}, {user_id}")
  user = sm.get_user(user_id)
  partial_state = get_status(user)
  ProposalTime.get_by_id(proptime_id).attempt_accept(user, partial_state)
  propagate_update_needed()
  return _get_state(user)


@authenticated_callable
@anvil.tables.in_transaction
def add_proposal(proposal, link_key="", user_id=""):
  """Return state, prop_id (none if matching with another proposal)
  
  Side effects: Update proposal tables with additions, if valid; match if appropriate
  """
  print(f"add_proposal, {user_id}")
  user = sm.get_user(user_id)
  propagate_update_needed()
  prop_id = _add_proposal(user, proposal, link_key)
  return _get_state(user), prop_id


def _add_proposal(user, port_prop, link_key=""):
  partial_state = get_status(user)
  status = partial_state['status']
  prop = Proposal.add(user, port_prop)
  if port_prop.start_now:
    duration = port_prop.times[0].duration
    if (status is not None or _match_overlapping_now_proposal(user, prop, duration, partial_state)):
      prop.cancel_all_times()
      return None
  prop.notify_add()
  if link_key:
    prop.add_to_invite(link_key)
  return prop.get_id()


def _match_overlapping_now_proposal(user, my_now_proposal, my_duration, state):
  current_port_props = Proposal.get_port_proposals(user)
  now_port_props = [p for p in current_port_props if p.start_now and not p.own]
  for other_port_prop in now_port_props:
    if (my_now_proposal.is_visible(other_port_prop.user.s_user)
        and my_duration == other_port_prop.times[0].duration):
      other_prop_time = ProposalTime.get_by_id(other_port_prop.times[0].time_id)
      other_prop_time.accept(user, state['status'])
      return True
  return False
  

@authenticated_callable
@anvil.tables.in_transaction
def edit_proposal(proposal, user_id=""):
  """Return state, prop_id (none if matching with another proposal)
  
  Side effects: Update proposal tables with revision, if valid; match if appropriate
  """
  print(f"edit_proposal, {user_id}")
  user = sm.get_user(user_id)
  propagate_update_needed()
  prop_id = _edit_proposal(user, proposal)
  return _get_state(user), prop_id

    
def _edit_proposal(user, port_prop):
  partial_state = get_status(user)
  status = partial_state['status']
  prop = Proposal.get_by_id(port_prop.prop_id)
  old_port_prop = prop.portable(user)
  prop.update(port_prop)
  if port_prop.start_now:
    duration = port_prop.times[0].duration
    if (status is not None or _match_overlapping_now_proposal(user, prop, duration, partial_state)):
      prop.cancel_all_times()
      return None
  prop.notify_edit(port_prop, old_port_prop)
  return prop.get_id()

  
@authenticated_callable
@anvil.tables.in_transaction
def cancel_time(proptime_id, user_id=""):
  """Remove proptime"""
  print(f"cancel_time, {proptime_id}, {user_id}")
  user = sm.get_user(user_id)
  propagate_update_needed()
  proptime = ProposalTime.get_by_id(proptime_id)
  port_prop = proptime.proposal.portable(user)
  if len(port_prop.times) > 1:
    [port_time_to_cancel] = [port_time for port_time in port_prop.times if port_time.time_id == proptime_id]
    port_prop.times.remove(port_time_to_cancel)
    prop_id = _edit_proposal(user, port_prop) # can ignore prop_id because not port_prop.start_now
  else:
    proptime.notify_cancel()
    _cancel(user, proptime_id)
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


@authenticated_callable
@anvil.tables.in_transaction
def cancel_accept(proptime_id=None, user_id=""):
  """Remove user accepting"""
  print(f"cancel_accept, {proptime_id}, {user_id}")
  user = sm.get_user(user_id)
  propagate_update_needed()
  _cancel(user, proptime_id)
  return _get_state(user)


@authenticated_callable
@anvil.tables.in_transaction
def cancel_now(proptime_id=None, user_id=""):
  """Remove proptime and cancel pending match (if applicable)"""
  print(f"cancel_now, {proptime_id}, {user_id}")
  user = sm.get_user(user_id)
  if proptime_id:
    proptime = ProposalTime.get_by_id(proptime_id)
    if proptime:
      proptime.notify_cancel()
  propagate_update_needed()
  _cancel(user, proptime_id)
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


@authenticated_callable
@anvil.tables.in_transaction
def cancel_other(proptime_id=None, user_id=""):
  """Upon failure of other to confirm match
  cancel match (if applicable)--and cancel their request
  """
  print(f"cancel_other, {proptime_id}, {user_id}")
  user = sm.get_user(user_id)
  propagate_update_needed()
  _cancel_other(user, proptime_id)
  return _get_state(user)


@authenticated_callable
@anvil.tables.in_transaction
def match_commit(proptime_id=None, user_id=""):
  """Upon first commence of "now", copy row over and delete "matching" row.
  Should not cause error if already commenced
  """
  print(f"match_commit, {proptime_id}, {user_id}")
  user = sm.get_user(user_id)
  propagate_update_needed()
  _match_commit(user, proptime_id)
  return _get_state(user)


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
