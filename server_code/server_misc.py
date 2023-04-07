import anvil.users
import anvil.server
import anvil.tables
from anvil.tables import app_tables, order_by
import anvil.tables.query as q
from abc import ABC, abstractproperty, abstractmethod
from anvil import secrets
from . import parameters as p
from . import portable as port
from .relationship import Relationship
from .exceptions import RowMissingError
from anvil_extras.server_utils import timed
from functools import wraps 


DEBUG = False #p.DEBUG_MODE
TEST_TRUST_LEVEL = 10
authenticated_callable = anvil.server.callable(require_user=True)


def background_task_with_reporting(func):
   return anvil.server.background_task(with_error_reporting(func))


def with_error_reporting(func):
  @wraps(func)
  def out_function(*args, **kwargs):
    try:
      func(*args, **kwargs)
    except Exception as err:
      import traceback
      app_info_dict = {'id': anvil.app.id,
            'branch': anvil.app.branch,
            'environment.name': anvil.app.environment.name,
          }
      context = anvil.server.context
      report_error(traceback.format_exc(), app_info_dict, repr(context))
      raise err
  return out_function


def now():
  """Return utcnow"""
  import datetime
  return datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc())

    
def get_acting_user(user_id="", require_auth=True):
  if DEBUG:
    print("get_acting_user", user_id)
  logged_in_user = anvil.users.get_user()
  if user_id == "" or (logged_in_user and logged_in_user.get_id() == user_id):
    return logged_in_user
  elif (require_auth and (not logged_in_user or logged_in_user['trust_level'] < TEST_TRUST_LEVEL)):
    raise RuntimeError("User not authorized to access this information")
  else:
    return get_other_user(user_id)


def get_other_user(user_id):
  if user_id:
    return app_tables.users.get_by_id(user_id)
  else:
    return anvil.users.get_user()


@anvil.server.callable
def report_error(err_repr, app_info_dict, context_str):
  from . import notifies as n
  admin = app_tables.users.get(email=secrets.get_secret('admin_email'))
  current_user = anvil.users.get_user()
  if admin != current_user:
    current_user_email = current_user['email'] if current_user else ""
    content = (
      f"""{err_repr}
      user: {current_user_email}
      app: {app_info_dict}
      context: {context_str}
      app_origin: {anvil.server.get_app_origin()}
      """
    )
    print(f"Reporting error: {content}")
    n.email_send(admin, subject="empathy.chat error", text=content, from_name="empathy.chat error handling")


@anvil.server.callable
def warning(warning_str, app_info_dict=None, from_client=False):
  from . import notifies as n
  admin = app_tables.users.get(email=secrets.get_secret('admin_email'))
  current_user = anvil.users.get_user()
  if admin != current_user:
    current_user_email = current_user['email'] if current_user else ""
    content = (
      f"""{warning_str}
      user: {current_user_email}
      app: {app_info_dict}
      context: {repr(anvil.server.context)}
      app_origin: {anvil.server.get_app_origin()}
      """
    )
    if not from_client:
      print(f"Reporting warning: {warning_str}")
    n.email_send(admin, subject="empathy.chat warning", text=content, from_name="empathy.chat warning handling")


def my_assert(statement, id_str):
  if not statement:
    warning(f"{id_str}: bool({statement}) is not True")
  
    
def as_user_tz(dt, user):
  import pytz
  time_zone = user['time_zone'] if user['time_zone'] else "America/Chicago"
  tz_user = pytz.timezone(time_zone)
  return dt.astimezone(tz_user)


def phone(user):
  return secrets.decrypt_with_key("new_key", user['phone']) if user['phone'] else ""
  

def name(user, to_user=None, distance=None, rel=None):
  if rel is None and distance is None:
    if to_user:
      from . import connections as c
      distance = c.distance(user, to_user, up_to_distance=2)
    else:
      distance = port.UNLINKED
  return port.full_name(user['first_name'], user['last_name'], distance, rel)  


def get_simple_port_user(user2, distance=None, user1=None):
  if not user2:
    return None
  if distance is not None:
    _name = name(user2, distance=distance)
  else:
    explicit_user1 = True
    if not user1:
      explicit_user1 = False
      user1 = get_acting_user()
    if user1 == user2:
      distance = 0
    _name = name(user2, user1 if explicit_user1 else None, distance)
  return port.User(user2.get_id(), _name)


def get_port_user(user2, distance=None, user1=None, simple=False, starred=None):
  from . import network_gateway as ng
  if not user2:
    return None
  explicit_user1 = True
  if not user1:
    explicit_user1 = False
    user1 = get_acting_user()
  if user1 == user2:
    distance = 0
  _name = name(user2, user1 if explicit_user1 else None, distance)
  if simple:
    return port.User(user2.get_id(), _name)
  else:
    if starred is None:
      starred = bool(ng.star_row(user2, user1)) if user2 != user1 else None
    return port.User(user_id=user2.get_id(),
                     name=_name,
                     url_confirmed=bool(user2['url_confirmed_date']),
                     distance=distance,
                     seeking=user2['seeking_buddy'],
                     starred=starred, #True/False
                    )

  
def _latest_invited(user):
  _inviteds = inviteds(user)
  if len(_inviteds) == 0:
    return None
  else:
    return _inviteds[0]

  
def inviteds(user):
  return app_tables.invites.search(order_by("date", ascending=False), origin=True, user2=user, current=True)


@anvil.tables.in_transaction(relaxed=True)
def get_prompts(user):
  print("                      get_prompts")
  import datetime
  out = []
  other_prompts = app_tables.prompts.search(q.fetch_only('spec'), user=user, dismissed=q.not_(True))
  if len(other_prompts) > 0:
    for prompt in other_prompts:
      spec = prompt['spec']
      spec['prompt_id'] = prompt.get_id() 
      out.append(spec)
  invited = _latest_invited(user)
  if not user['phone']:
    if invited:
      out.append({"name": "phone-invited", "inviter": name(invited['user1'], to_user=user)})
    else:
      out.append({"name": "phone"})
  else:
    if invited:
      for invite in inviteds(user):
        out.append({"name": "invited", "inviter": name(invite['user1'], to_user=user), 
                    "inviter_id": invite['user1'].get_id(), "rel": invite['relationship2to1']})
    if user['trust_level'] == 2:
      import connections as c
      members = c.member_close_connections(user)
      if members:
        out.append({"name": "member-chat", "members": [get_port_user(m, distance=1, user1=user, simple=True) for m in members]})
#       else:
#         out.append({"name": "invite-close"})
    elif (not invited and not [s for s in out if s['name'] == "connected"]
          and (not user['last_invite'] or user['last_invite'] < now() - datetime.timedelta(days=90))):
      out.append({"name": "invite-close"})
  return out


@authenticated_callable
def dismiss_prompt(prompt_id):
  from . import matcher
  prompt = app_tables.prompts.get_by_id(prompt_id)
  prompt['dismissed'] = True
  matcher.propagate_update_needed()
  

@authenticated_callable
def invited_item(inviter_id, user_id=""):
  user = get_acting_user(user_id)
  inviter_user = get_other_user(inviter_id)
  _inviteds = app_tables.invites.search(order_by("date", ascending=False), origin=True, user1=inviter_user, user2=user, current=True)
  return {"inviter": name(inviter_user, to_user=user), "link_key": _inviteds[0]['link_key'],
          "inviter_id": inviter_id, "rel": _inviteds[0]['relationship2to1']}


def add_invite_guess_fail_prompt(s_invite):
  prompt_dict = _invite_guess_fail_prompt(s_invite)
  _add_invite_guess_fail_prompt(prompt_dict)


def _add_invite_guess_fail_prompt(prompt_dict):
  if not app_tables.prompts.get(user=prompt_dict['user'], spec={"name": "invite_guess_fail", 
                                                                "guess": prompt_dict['spec']['guess'],
                                                                "to_id": prompt_dict['spec']['to_id']}):
    app_tables.prompts.add_row(**prompt_dict)


def _invite_guess_fail_prompt(s_invite):
  return dict(user=s_invite.inviter,
              spec={"name": "invite_guess_fail", "rel": s_invite.rel_to_inviter, "guess": s_invite.inviter_guess,
                    "to_name": name(s_invite.invitee), "to_id": s_invite.invitee.get_id(), },
              date=now(),
              dismissed=False,
             )


@background_task_with_reporting
def add_message_prompt(user2, user1):
  such_prompts = app_tables.prompts.search(q.fetch_only('dismissed'), user=user2, dismissed=False, spec={"name": "message", "from_id": user1.get_id()})
  if len(such_prompts) == 0:
    from_name = name(user1, to_user=user2)
    app_tables.prompts.add_row(user=user2, date=now(), dismissed=False,
                             spec={"name": "message", "from_name": from_name, "from_id": user1.get_id()}
                            )
    from . import notifies as n
    n.notify_message(user2, from_name)
  from . import matcher
  matcher.propagate_update_needed(user1)


class ServerItem:
  def relay(self, method, kwargs=None):
    if not kwargs:
      kwargs = {}
    return getattr(self, method)(**kwargs)


class Record(ABC):
  @abstractmethod
  def __init__(self, entity, record_id=None, row=None):
    pass

  @abstractmethod
  def save(self):
    pass
  
  @abstractproperty
  def record_id(self):
    pass

  @classmethod
  @abstractmethod
  def from_row(cls, row):
    pass

  @classmethod
  @abstractmethod
  def from_id(cls, record_id):
    pass


class SimpleRecord(Record):
  @abstractproperty
  def _table_name(self):
    pass

  @staticmethod
  @abstractmethod
  def _row_to_entity(row):
    pass

  @staticmethod
  @abstractmethod
  def _entity_to_fields(entity):
    pass
  
  @property
  def _table(self):
    return getattr(app_tables, self._table_name)
  
  def __init__(self, entity, record_id=None, row=None):
    self.entity = entity
    if record_id is None and row:
      record_id = row.get_id()
    self._row_id = record_id
    self.__row = row
    try:
      _record_id = getattr(entity, self.__class__.__name__.lower()[:-6] + "_id")
    except AttributeError:
      pass
    else:
      my_assert(not (_record_id and not self._row_id), "entity row should not be present if record_id not supplied")
      my_assert(_record_id == self._row_id, "entity row id should be equal to record_id")

  @property
  def _row(self):
    if self.__row is None and self._row_id is not None:
      self.__row = self._table.get_by_id(self._row_id)
    if self.__row is None:
      raise RowMissingError(f"No {self._table_name} database row known for this record")
    return self.__row

  def _add(self):
    self.__row = self._table.add_row(**self._entity_to_fields(self.entity))
    self._row_id = self.__row.get_id()
  
  def _update(self):
    self._row.update(**self._entity_to_fields(self.entity))
  
  def save(self):
    if self._row_id is None:
      self._add()
      return
    self._update()
  
  @property
  def record_id(self):
    return self._row_id

  @classmethod
  def from_row(cls, row):
    entity = cls._row_to_entity(row)
    return cls(entity, row.get_id(), row)

  @classmethod
  def from_id(cls, record_id):
    row = getattr(app_tables, cls._table_name).get_by_id(record_id)
    return cls.from_row(row)


@anvil.server.callable
def get_url(name):
  media = app_tables.files.get(name=name)['file']
  return media.url


@anvil.server.callable
def get_urls(names):
  return [get_url(name) for name in names]
