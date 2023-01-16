import anvil.server
from .requests import Request, Eformat


def reset_repo():
  global repo
  repo = None


repo = None
reset_repo()


def _add_request(user, port_prop, link_key=""):
  """Return prop_id (None if cancelled or matching with another proposal)
  
  Side effects: Update proposal tables with additions, if valid; match if appropriate; notify
  """
  return True


def _new_request(user, port_prop):
  """Return request"""
  port_time = port_prop.times[0]
  return Request(id=port_time.time_id,
                 or_group_id=port_prop.prop_id,
                 eformat=Eformat(port_time.duration),
                 expire_dt=port_time.expire_date,
                 user=port_prop.user,
                 
                )
