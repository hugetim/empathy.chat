import anvil.server
import anvil.users
import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
from . import portable as port
from . import helper as h





@anvil.server.portable_class 
class MyRequest(h.PortItem, h.AttributeToKey):

  def __init__(self, request_id=None, start_now=False, start_dt=None, expire_dt=None,
               chat_format=port.DURATION_DEFAULT_MINUTES, min_size=2, max_size=2,
               eligible_distance=2, eligible_users=[], eligible_group_ids=[], eligible_starred=True,):
    import datetime
#     self.request_id = request_id
    self.start_now = start_now 
    self.start_dt = (start_dt if (start_dt or start_now)
                       else h.round_up_datetime(h.now() + datetime.timedelta(minutes=port.DEFAULT_NEXT_MINUTES)))
#     self.chat_format = chat_format
#     if expire_dt or start_now:
#       self.expire_dt = expire_dt
#     else:
#       self.expire_dt = (self.start_dt
#                         - datetime.timedelta(minutes=port.CANCEL_DEFAULT_MINUTES))
#     self.min_size = min_size
#     self.max_size = max_size
#     self.eligible_distance = eligible_distance
#     self.eligible_users = eligible_users
#     self.eligible_group_ids = eligible_group_ids
#     self.eligible_starred = eligible_starred
  
  def get_errors(self):
    """Return a dictionary of errors"""
    now = h.now()
    messages = {}
    return messages
  
  def alternative_my_request(self):
    pass