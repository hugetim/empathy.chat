import anvil.server
from anvil import tables
import uuid
from .requests import Request, Eformat
from . import server_misc as sm
from . import accounts
from . import request_gateway


def reset_repo():
  global repo
  repo = request_gateway


repo = None
reset_repo()


def _add_request(user, port_prop, link_key=""):
  """Return prop_id (None if cancelled or matching with another proposal)
  
  Side effects: Update proposal tables with additions, if valid; match if appropriate; notify
  """
  accounts.update_default_request(port_prop, user)
  requests = tuple(_new_requests(user, port_prop))
  # get this user's other requests (and status) to confirm validity
  status = get_partial_state(user)['status']
  # confirm validity
  # get requests that might match with one of these
  
  _save_new_requests(requests)
  # ping other request if match
  # otherwise notify invited
  return requests[0].or_group_id


def _check_valid_requests(requests):
  pass
      # if user['trust_level'] < 3:
      # new_prop_row['eligible'] = min(2, new_prop_row['eligible'])


@tables.in_transaction(relaxed=True)
def _save_new_requests(requests):
  for request in requests:
      new_request_record = repo.RequestRecord(request)
      new_request_record.save()
      request.request_id = new_request_record.record_id


def _new_requests(user, port_prop):
  """Return request"""
  now = sm.now()
  or_group_id = str(uuid.uuid4())
  for port_time in port_prop.times:
    start_dt = port_time.start_date
    expire_dt = port_time.expire_date
    if port_time.start_now:
      start_dt = now
      expire_dt = now + datetime.timedelta(seconds=p.WAIT_SECONDS)
    yield Request(or_group_id=or_group_id,                  
                  user=port_prop.user,
                  start_dt=start_dt,
                  expire_dt=expire_dt,
                  eformat=Eformat(port_time.duration),
                  create_dt=now,
                  edit_dt=now,
                  min_size=port_prop.min_size,
                  max_size=port_prop.max_size,
                  eligible=port_prop.eligible,
                  eligible_users=port_prop.eligible_users,
                  eligible_groups=port_prop.eligible_groups,
                  eligible_starred=port_prop.eligible_starred,
                  current=True,
                 )

    # yield Request(request_id=port_time.time_id,
    #               or_group_id=port_prop.prop_id,
    #               eformat=Eformat(port_time.duration),
    #               expire_dt=port_time.expire_date,
    #               user=port_prop.user,
    #               start_dt=port_time.start_date,
    #               create_dt=now,
    #               edit_dt=now,
    #               min_size=port_prop.min_size,
    #               max_size=port_prop.max_size,
    #               eligible=port_prop.eligible,
    #               eligible_users=port_prop.eligible_users,
    #               eligible_groups=port_prop.eligible_groups,
    #               eligible_starred=port_prop.eligible_starred,
    #               current=True,
    #              )
