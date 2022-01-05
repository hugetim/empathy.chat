import anvil.users
import anvil.tables
from anvil.tables import app_tables
import anvil.tables.query as q
import anvil.server
import datetime
import anvil.tz
from . import parameters as p
from . import server_misc as sm
from .server_misc import authenticated_callable
from . import portable as port
from .proposals import Proposal, ProposalTime


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


@anvil.tables.in_transaction
def _init(user):
  _prune_all_expired_items()
  state = _init_user_status(user)
  return {'trust_level': user['trust_level'],
          'test_mode': user['trust_level'] >= sm.TEST_TRUST_LEVEL,
          'name': user['first_name'],
          'state': state,
         }


def _prune_all_expired_items():
  Proposal.prune_all()
  _prune_matches()
  sm.prune_messages()

  
def _init_user_status(user):
  state = _get_status(user)
  if state['status'] == 'pinged' and state['seconds_left'] <= 0:
    state = _cancel(user)
  elif state['status'] == 'pinged':
    state = _match_commit(user)
  elif state['status'] == 'pinging' and state['seconds_left'] <= 0:
    state = _cancel_other(user)
  if state['status'] in ('requesting', 'pinged', 'pinging'):
    state = confirm_wait_helper(user)
  anvil.server.session['status'] = state
  propagate_update_needed(user)
  return state

  
def confirm_wait_helper(user):
  """updates expire_date for current request, returns _get_status(user)"""
  if sm.DEBUG:
    print("confirm_wait_helper")
  current_proptime = ProposalTime.get_now_proposing(user)
  if current_proptime:
    current_proptime.confirm_wait()
  return _get_status(user) if user else None


@authenticated_callable
@anvil.tables.in_transaction
def get_proposals_upcomings(user_id=""):
  user = sm.get_user(user_id)
  proposals = Proposal.get_port_proposals(user)
  upcomings = _get_upcomings(user)
  return proposals, upcomings


def propagate_update_needed(user=None):
  all_users = app_tables.users.search()
  for u in all_users:
    if u != user:
      u['update_needed'] = True

      
@authenticated_callable
@anvil.tables.in_transaction
def get_status(user_id=""):
  user = sm.get_user(user_id)
  saved_status = anvil.server.session.get('status')
  if user['update_needed'] or not saved_status:
    anvil.server.session['status'] = _get_status(user)
    user['update_needed'] = False
  return anvil.server.session['status']


def _get_status(user):
  """Returns status dict
  ping_start: accept_date or, for "matched", match_commence
  assumes 2-person matches only
  Side effects: prune proposals when status in [None]
  """
  if sm.DEBUG:
    print("_get_status")
  expire_date = None
  ping_start = None
  proposals = []
  upcomings = []
  prompts = []
  current_proptime = ProposalTime.get_now_proposing(user)
  if current_proptime:
    expire_date = current_proptime.expire_date
    if current_proptime.is_accepted():
      status = "pinged"
      ping_start = current_proptime.ping_start
    else:
      status = "requesting"
  else:
    current_accept_time = ProposalTime.get_now_accepting(user)
    if current_accept_time:
      status = "pinging"
      ping_start = current_accept_time.ping_start
      expire_date = current_accept_time.expire_date
    else:
      this_match = current_match(user)
      if this_match:
        status = "matched"
        ping_start = this_match['match_commence']
      else:
        status = None
        proposals = Proposal.get_port_proposals(user)
        upcomings = _get_upcomings(user)
        prompts = sm.get_prompts(user)
  return {'status': status, 
          'seconds_left': _seconds_left(status, expire_date, ping_start), 
          'proposals': proposals,
          'upcomings': upcomings,
          'prompts': prompts,
         }


def _get_upcomings(user):
    """Return list of user's upcoming matches
    
    Side effects: prune proposals
    """
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
                    'duration_minutes': ProposalTime(match['proposal_time']).duration,
                    'match_id': match.get_id(),
                   }
      match_dicts.append(match_dict)
    return match_dicts

 
def _cancel_match(user, match_id):
  if sm.DEBUG:
    print("_cancel_match", match_id)
  match = app_tables.matches.get_by_id(match_id)
  if match:
    for u in match['users']:
      if u != user:
        sm.notify_cancel(u, start=match['match_commence'], canceler_name=sm.name(user, to_user=u))
    match.delete()
  return _get_status(user)

  
@authenticated_callable
@anvil.tables.in_transaction
def cancel_match(match_id, user_id=""):
  """Cancel pending match
  Return _get_status
  """
  print("cancel", match_id, user_id)
  user = sm.get_user(user_id)
  propagate_update_needed()
  return _cancel_match(user, match_id)  
  
  
@authenticated_callable
@anvil.tables.in_transaction
def init_match_form(user_id=""):
  """Return jitsi_code, duration (or Nones), my_slider_value
  
  Side effect: set this_match['present']"""
  print("init_match_form", user_id)
  user = sm.get_user(user_id)
  current_proptime = ProposalTime.get_now(user)
  if current_proptime:
    jitsi_code, duration = current_proptime.get_match_info()
    return jitsi_code, duration, None
  else:
    this_match, i = current_match_i(user)
    if this_match:
      temp = this_match['present']
      temp[i] = 1
      this_match['present'] = temp
      jitsi_code, duration = ProposalTime(this_match['proposal_time']).get_match_info()
      propagate_update_needed()
      return jitsi_code, duration, this_match['slider_values'][i]
  return None, None, None


@authenticated_callable
@anvil.tables.in_transaction
def accept_proposal(proptime_id, user_id=""):
  """Return _get_status
  
  Side effect: update proptime table with acceptance, if available
  """
  print("accept_proposal", proptime_id, user_id)
  user = sm.get_user(user_id)
  state = _get_status(user)
  ProposalTime.get_by_id(proptime_id).attempt_accept(user, state)
  propagate_update_needed()
  return _get_status(user)


@authenticated_callable
@anvil.tables.in_transaction
def add_proposal(proposal, link_key="", user_id=""):
  """Return _get_status, prop_id (none if matching with another proposal)
  
  Side effects: Update proposal tables with additions, if valid; match if appropriate
  """
  print("add_proposal", user_id)
  user = sm.get_user(user_id)
  propagate_update_needed()
  return _add_proposal(user, proposal, link_key)


def _add_proposal(user, port_prop, link_key=""):
  state = _get_status(user)
  status = state['status']
  prop = Proposal.add(user, port_prop)
  if port_prop.start_now:
    duration = port_prop.times[0].duration
    if (status is not None or _match_overlapping_now_proposal(user, prop, duration, state)):
      prop.cancel_all_times()
      return _get_status(user), None
  prop.notify_add()
  if link_key:
    prop.add_to_invite(link_key)
  return _get_status(user), prop.get_id()


def _match_overlapping_now_proposal(user, my_now_proposal, my_duration, state):
  current_port_props = port.Proposal.props_from_view_items(state['proposals'])
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
  """Return _get_status, prop_id (none if matching with another proposal)
  
  Side effects: Update proposal tables with revision, if valid; match if appropriate
  """
  print("edit_proposal", user_id)
  user = sm.get_user(user_id)
  propagate_update_needed()
  return _edit_proposal(user, proposal)

    
def _edit_proposal(user, port_prop):
  state = _get_status(user)
  status = state['status']
  prop = Proposal.get_by_id(port_prop.prop_id)
  old_port_prop = prop.portable(user)
  prop.update(port_prop)
  if port_prop.start_now:
    duration = port_prop.times[0].duration
    if (status is not None or _match_overlapping_now_proposal(user, prop, duration, state)):
      prop.cancel_all_times()
      return _get_status(user), None
  prop.notify_edit(port_prop, old_port_prop)
  return _get_status(user), prop.get_id()


def _cancel(user, proptime_id=None):
  if sm.DEBUG:
    print("_cancel", proptime_id)
  if proptime_id:
    proptime = ProposalTime.get_by_id(proptime_id)
  else:
    proptime = ProposalTime.get_now(user)
  if proptime:
    proptime.cancel_this(user)
  return _get_status(user)

  
@authenticated_callable
@anvil.tables.in_transaction
def cancel(proptime_id=None, user_id=""):
  """Remove proptime and cancel pending match (if applicable)
  Return _get_status
  """
  print("cancel", proptime_id, user_id)
  user = sm.get_user(user_id)
  propagate_update_needed()
  return _cancel(user, proptime_id)


def _cancel_other(user, proptime_id=None):
  if sm.DEBUG:
    print("_cancel_other", proptime_id)
  if proptime_id:
    proptime = ProposalTime.get_by_id(proptime_id)
  else:
    proptime = ProposalTime.get_now(user)
  if proptime:
    proptime.cancel_other(user)
  return _get_status(user)


@authenticated_callable
@anvil.tables.in_transaction
def cancel_other(proptime_id=None, user_id=""):
  """Return new _get_status
  Upon failure of other to confirm match
  cancel match (if applicable)--and cancel their request
  """
  print("cancel_other", proptime_id, user_id)
  user = sm.get_user(user_id)
  propagate_update_needed()
  return _cancel_other(user, proptime_id)


@authenticated_callable
@anvil.tables.in_transaction
def match_commit(proptime_id=None, user_id=""):
  """Return _get_status(user)
  Upon first commence of "now", copy row over and delete "matching" row.
  Should not cause error if already commenced
  """
  print("match_commit", proptime_id, user_id)
  user = sm.get_user(user_id)
  propagate_update_needed()
  return _match_commit(user, proptime_id)


def _match_commit(user, proptime_id=None):
  """Return _get_status(user)"""
  if sm.DEBUG:
    print("_match_commit")
  if proptime_id:
    print("proptime_id")
    current_proptime = ProposalTime.get_by_id(proptime_id)
  else:
    current_proptime = ProposalTime.get_now(user)
  if current_proptime:
    print("current_proptime")
    if current_proptime.is_accepted():
      print("'accepted'")
      if current_proptime.start_now:
        match_start = sm.now()
      else:
        match_start = current_proptime.start_date
      users = current_proptime.all_users()
      new_match = app_tables.matches.add_row(users=users,
                                             proposal_time=current_proptime._row,
                                             match_commence=match_start,
                                             present=[0]*len(users),
                                             complete=[0]*len(users),
                                             slider_values=[""]*len(users))
      # Note: 0 used for 'complete' b/c False not allowed in SimpleObjects
      proposal = current_proptime.proposal
      proposal.cancel_all_times()
      if not current_proptime.start_now:
        current_proptime.ping()
  return _get_status(user)


@authenticated_callable
@anvil.tables.in_transaction
def match_complete(user_id=""):
  """Switch 'complete' to true in matches table for user, return status."""
  print("match_complete", user_id)
  user = sm.get_user(user_id)
  # Note: 0/1 used for 'complete' b/c Booleans not allowed in SimpleObjects
  this_match, i = current_match_i(user)
  if this_match:
    temp = this_match['complete']
    temp[i] = 1
    this_match['complete'] = temp
  else:
    current_proptime = ProposalTime.get_now(user)
    if current_proptime:
      _cancel(user, current_proptime.get_id())
  propagate_update_needed()
  return _get_status(user)


def current_match(user):
  this_match = None
  now_plus = sm.now() + datetime.timedelta(minutes=p.START_EARLY_MINUTES)
  current_matches = app_tables.matches.search(users=[user], complete=[0],
                                              match_commence=q.less_than_or_equal_to(now_plus))
  for row in current_matches:
    i = row['users'].index(user)
    # Note: 0 used for 'complete' field b/c False not allowed in SimpleObjects
    if row['complete'][i] == 0:
      this_match = row
  return this_match


def current_match_i(user):
  this_match, i = None, None
  now_plus = sm.now() + datetime.timedelta(minutes=p.START_EARLY_MINUTES)
  current_matches = app_tables.matches.search(users=[user], complete=[0],
                                              match_commence=q.less_than_or_equal_to(now_plus))
  for row in current_matches:
    i = row['users'].index(user)
    # Note: 0 used for 'complete' field b/c False not allowed in SimpleObjects
    if row['complete'][i] == 0:
      this_match = row
  return this_match, i
