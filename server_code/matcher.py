import anvil.server
from . import parameters as p
from . import notifies as n
from . import accounts
from . import server_misc as sm
from . import exchange_interactor as ei
from . import request_interactor as ri
from .requests import Requests, prop_to_requests
from .server_misc import authenticated_callable
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


@authenticated_callable
def init(time_zone):
  """Runs upon initializing app
  
  Side effects: prunes old proposals/matches,
                updates expire_date if currently requesting/ping
                clears cached session['state']
  """
  user = anvil.users.get_user()
  task = anvil.server.launch_background_task('_init_bg', time_zone, user)
  anvil.server.session['state'] = None
  return task


@sm.background_task_with_reporting
@timed
def _init_bg(time_zone, user):
  import anvil.users
  from . import network_interactor as ni
  user['confirmed_email'] = True # because login (either Google or via password reset email) required to get here
  anvil.users.force_login(user)
  trust_level = accounts.initialize_session(time_zone, user)
  anvil.server.task_state['init_dict'] = _init_matcher(user, trust_level)
  propagate_update_needed(user)
  anvil.server.task_state['out'] = ni.init_cache(user)


def _init_matcher(user, trust_level):
  _init_user_status(user)
  state = _get_state(user)
  return {'trust_level': trust_level,
          'test_mode': trust_level >= sm.TEST_TRUST_LEVEL,
          'name': user['first_name'],
          'state': state,
          'default_request': user['default_request'],
         }


@anvil.tables.in_transaction
def _init_user_status(user):
  with TimerLogger("  _init_user_status", format="{name}: {elapsed:6.3f} s | {msg}") as timer:
    ei.prune_no_show_exchanges()
    timer.check("prune_no_show_exchanges")
    status = user['status']
    if status == "pinged":
      ei.commence_user_exchange(user)
    # if partial_state['status'] == 'pinging' and partial_state['seconds_left'] <= 0:
    #   _cancel_other(user)
    if status == "requesting":
      request_record = ri.now_request(user, record=True)
      expire_dt = request_record.entity.expire_dt
      if _seconds_left("requesting", expire_date=expire_dt) <= 0:
        request_record.cancel()
        user.update()
      else:
        ri.confirm_wait(request_record)


@anvil.tables.in_transaction(relaxed=True)
def _get_proposals_upcomings(user):
  print("                      _get_proposals_upcomings")
  proposals = ri.get_visible_requests_as_port_view_items(user)
  upcomings = _get_upcomings(user)
  return proposals, upcomings


def propagate_update_needed(user=None):
  from anvil.tables import app_tables
  import anvil.tables
  all_users = app_tables.users.search(update_needed=False)
  with anvil.tables.batch_update:
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
    if anvil.server.context.client.type == 'browser':
      anvil.server.session['state'] = state
      user['update_needed'] = False
    return state
  

def get_partial_state(user):
  """Returns status dict (only 'status' and 'seconds_left')
  ping_start: accept_date or, for "matched", match_commence
  assumes 2-person matches only
  """
  status = user['status']
  return {'status': status, 
         }


def _get_upcomings(user):
  """Return list of user's upcoming matches"""
  return ei.upcoming_match_dicts(user)

  
@authenticated_callable
def cancel_match(match_id, user_id=""):
  """Cancel pending match"""
  print(f"cancel_match, {match_id}, {user_id}")
  user = sm.get_acting_user(user_id)
  users_to_notify, start_dt = ei.cancel_exchange(user, match_id)
  for u in users_to_notify:
    n.notify_match_cancel_bg(u, start=start_dt, canceler_name=sm.name(user, to_user=u))
  propagate_update_needed(user)
  return _get_state(user)


@authenticated_callable
def accept_proposal(proptime_id, user_id=""):
  """Add user_accepting
  
  Side effect: update proptime table with acceptance, if available
  """
  print(f"accept_proposal, {proptime_id}, {user_id}")
  user = sm.get_acting_user(user_id)
  ri.accept_pair_request(user, request_id=proptime_id)
  propagate_update_needed(user)
  return _get_state(user)


@authenticated_callable
def add_proposal(port_prop, invite_link_key="", user_id=""):
  """Return state, prop_id (None if cancelled or matching with another proposal)
  
  Side effects: Update proposal tables with additions, if valid; match if appropriate; notify
  """
  print(f"add_proposal, {user_id}")
  user = sm.get_acting_user(user_id)
  accounts.update_default_request(port_prop, user)
  requests = Requests(prop_to_requests(port_prop, user_id=user.get_id()))
  prop_id = ri.add_requests(user, requests, invite_link_key)
  propagate_update_needed(user)
  return _get_state(user), prop_id
  

@authenticated_callable
def edit_proposal(port_prop, user_id=""):
  """Return state, prop_id (None if cancelled or matching with another proposal)
  
  Side effects: Update proposal tables with revision, if valid; match if appropriate; notify
  """
  print(f"edit_proposal, {user_id}")
  user = sm.get_acting_user(user_id)
  accounts.update_default_request(port_prop, user)
  requests = Requests(prop_to_requests(port_prop, user_id=user.get_id()))
  prop_id = ri.edit_requests(user, requests)
  propagate_update_needed(user)
  return _get_state(user), prop_id

  
@authenticated_callable
def cancel_time(proptime_id, user_id=""):
  """Remove proptime"""
  print(f"cancel_time, {proptime_id}, {user_id}")
  user = sm.get_acting_user(user_id)
  ri.cancel_request(user, proptime_id)
  propagate_update_needed(user)
  return _get_state(user)


@authenticated_callable
def cancel_accept(proptime_id=None, user_id=""):
  """Remove user accepting"""
  print(f"cancel_accept, {proptime_id}, {user_id}")
  user = sm.get_acting_user(user_id)
  ri.cancel_now(user)
  propagate_update_needed(user)
  return _get_state(user)


@authenticated_callable
def cancel_now(proptime_id=None, user_id=""):
  """Remove proptime and cancel pending match (if applicable)"""
  print(f"cancel_now, {proptime_id}, {user_id}")
  user = sm.get_acting_user(user_id)
  ri.cancel_now(user, proptime_id)
  propagate_update_needed()
  return _get_state(user)


@authenticated_callable
def match_commence(proptime_id=None, user_id=""):
  """
  Upon first commence of 'now', copy row over and delete 'matching' row.
  Should not cause error if already commenced
  """
  print(f"match_commence, {proptime_id}, {user_id}")
  user = sm.get_acting_user(user_id)
  ei.commence_user_exchange(user)
  propagate_update_needed(user)
  return _get_state(user)
