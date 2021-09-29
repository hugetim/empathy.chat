import anvil.users
import anvil.server
import anvil.tables
from anvil.tables import app_tables, order_by
import anvil.tables.query as q
import anvil.secrets
import anvil.email
import datetime
import random
import re
from . import parameters as p
from . import helper as h
from . import portable as port


DEBUG = False
TEST_TRUST_LEVEL = 10
authenticated_callable = anvil.server.callable(require_user=True)


def now():
  """Return utcnow"""
  return datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc())


def initialize_session():
  """initialize session state: user_id, user, and current_row"""
  user_id = anvil.users.get_user().get_id()
  anvil.server.session['user_id'] = user_id
  user = app_tables.users.get_by_id(user_id)
  anvil.server.session['user'] = user
  anvil.server.session['trust_level'] = user['trust_level']
  anvil.server.session['test_record'] = None


def get_user(user_id="", require_auth=True):
  if DEBUG:
    print("get_user", user_id)
  if user_id == "" or anvil.server.session['user_id'] == user_id:
    return anvil.server.session['user']
  elif (require_auth and anvil.server.session['trust_level'] < TEST_TRUST_LEVEL):
    raise RuntimeError("User not authorized to access this information")
  else:
    return app_tables.users.get_by_id(user_id)


def get_user_info(user):
  """Return user info, initializing info for new users"""
  trust = user['trust_level']
  if trust is None:
    user['trust_level'] = 1
    user['request_em'] = False
    user['pinged_em'] = False
    user['request_em_settings'] = {"fixed": 0, "hours": 2}
    user['first_name'] = ""
    user['last_name'] = ""
    user['how_empathy'] = ""
    user['profile'] = ""
    user['phone'] = ""
    user['confirmed_url'] = ""
  return user['trust_level']


def get_port_user(user2, distance=None, user1_id="", simple=False):
  if not distance:
    from . import connections as c
    user1 = get_user(user1_id)
    distance = c.distance(user2, user1)
  name = port.full_name(user2['first_name'], user2['last_name'], distance)
  if simple:
    return port.User(user2.get_id(), name)
  else:
    return port.User(user2.get_id(), 
                     name,
                     confirmed=bool(user2['confirmed_url']),
                     distance=distance,
                     seeking=user2['seeking_buddy'],
                     starred=None, #True/False
                    )


def get_prompts(user):
  out = []
  if not user['phone']:
    out.append({"name": "phone"})
  else:
    out.append({"name": "invite_close"})
  return out


@authenticated_callable
def init_profile(user_id=""):
  from . import connections as c
  user = get_user(user_id, require_auth=False)
  record = c.connection_record(user, get_user())
  confirmed_url_date = (
    user['confirmed_url_date'].strftime(p.DATE_FORMAT) if user['confirmed_url']
    else ""
  )
  is_me = user == anvil.server.session['user']
  record.update({'me': is_me,
                 'first': user['first_name'],
                 'last': port.last_name(user['last_name'], record['degree']),
                 'relationships': [] if is_me else c.get_relationships(user),
                 'confirmed_url': user['confirmed_url'],
                 'confirmed_date': confirmed_url_date,
                 'how_empathy': user['how_empathy'],
                 'profile': user['profile'],
                })
  return record
    
  
@authenticated_callable
def set_seeking_buddy(seeking, user_id=""):
  user = get_user(user_id)
  user['seeking_buddy'] = seeking
  
  
@authenticated_callable
def save_name(name_item, user_id=""):
  user = get_user(user_id)
  user['first_name'] = name_item['first']
  user['last_name'] = name_item['last']
  
  
@authenticated_callable
def save_user_item(item_name, text, user_id=""):
  user = get_user(user_id)
  user[item_name] = text
  

def new_jitsi_code():
  if DEBUG:
    print("server_misc.new_jitsi_code()")
  return "empathyspot-" + random_code()


def random_code(num_chars=5, digits_only=False):
  if digits_only:
    charset = "1234567890"
  else:
    charset = "abcdefghijkmnopqrstuvwxyz23456789"
  random.seed()
  return "".join([random.choice(charset) for i in range(num_chars)])


def prune_messages():
  """Prune messages from fully completed matches"""
  if DEBUG:
    print("server_misc.prune_messages()")
  all_messages = app_tables.chat.search()
  matches = {message['match'] for message in all_messages}
  for match in matches:
    if min(match['complete']) == 1:
      for row in app_tables.chat.search(match=match):
        row.delete()


@authenticated_callable
def add_message(user_id="", message="[blank]"):
  from . import matcher
  print("add_message", "[redacted]", user_id)
  user = get_user(user_id)
  this_match = matcher.current_match(user)
  app_tables.chat.add_row(match=this_match,
                          user=user,
                          message=anvil.secrets.encrypt_with_key("new_key", message),
                          time_stamp=now())
  return _get_messages(user)


@authenticated_callable
def get_messages(user_id=""):
  """
  Return (iterable of dictionaries with keys: 'me', 'message'), their_value
  """
  user = get_user(user_id)
  return _get_messages(user)


def _get_messages(user):
  from . import matcher
  this_match, i = matcher.current_match_i(user)
  if this_match:
    their_value = _their_value(this_match['slider_values'], i)
    messages = app_tables.chat.search(match=this_match)
    if messages:
      return ([{'me': (user == m['user']),
                'message': anvil.secrets.decrypt_with_key("new_key", m['message'])}
               for m in messages],
              their_value)

  
@authenticated_callable
def submit_slider(value, user_id=""):
  """Return their_value"""
  from . import matcher
  print("submit_slider", "[redacted]", user_id)
  user = get_user(user_id)
  this_match, i = matcher.current_match_i(user)
  temp_values = this_match['slider_values']
  temp_values[i] = value
  this_match['slider_values'] = temp_values 
  return _their_value(this_match['slider_values'], i)


def _their_value(values, my_i):
  temp_values = [value for value in values]
  temp_values.pop(my_i)
  assert len(temp_values) == 1              # assumes dyads only
  return temp_values[0]                     # return the remaining value


def _emails_equal(a, b):
  em_re = re.compile(r"^([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)$")
  a_match = em_re.search(a)
  b_match = em_re.search(b)
  return a_match.group(1) == b_match.group(1) and a_match.group(2).lower() == b_match.group(2).lower()


@authenticated_callable
def get_settings(user1_id=""):
  """Return user settings displayed on SettingsForm"""
  user = get_user(user1_id)
  re_opts = user['request_em_settings']
  if (user['request_em'] == True and re_opts["fixed"]
      and h.re_hours(re_opts["hours"], user['request_em_set_time']) <= 0):
    user['request_em'] = False
  return (user['request_em'], user['request_em_settings'],
          user['request_em_set_time'], user['phone'])


def _prune_request_em():
  """Switch expired request_em to false"""
  expired_rem_users = []
  for u in app_tables.users.search(request_em=True):
    if (u['request_em_settings']['fixed']
        and h.re_hours(u['request_em_settings']['hours'], u['request_em_set_time']) <= 0):
      u['request_em'] = False


#@authenticated_callable
#@anvil.tables.in_transaction
#def set_pinged_em(pinged_em_checked):
#  print("set_pinged_em", pinged_em_checked)
#  from . import matcher
#  user = anvil.server.session['user']
#  user['pinged_em'] = pinged_em_checked
#  return matcher.confirm_wait_helper(user)


@authenticated_callable
@anvil.tables.in_transaction
def set_request_em(request_em_checked, user_id=""):
  print("set_request_em", request_em_checked)
  user = get_user(user_id)
  user['request_em'] = request_em_checked
  if request_em_checked:
    user['request_em_set_time'] = now()
  return user['request_em_set_time']


@authenticated_callable
@anvil.tables.in_transaction
def set_request_em_opts(fixed, hours, user_id=""):
  print("set_request_em_opts", fixed, hours)
  user = get_user(user_id)
  re_opts = user['request_em_settings']
  re_opts["fixed"] = int(fixed)
  re_opts["hours"] = hours
  user['request_em_settings'] = re_opts
  user['request_em_set_time'] = now()
  return user['request_em_set_time']


@authenticated_callable
def send_verification_sms(number, user_id=""):
  user = get_user()
  account_sid = anvil.secrets.get_secret('account_sid')
  auth_token = anvil.secrets.get_secret('auth_token')
  from twilio.rest import Client
  client = Client(account_sid, auth_token)
  code = random_code(num_chars=6, digits_only=True)
  message = client.messages.create(
    body=f"{code} is your empathy.chat verification code. It expires in 10 minutes.",
    from_='+12312905138',
    to=number,
  )
  app_tables.codes.add_row(
    type="phone",
    address=number,
    code=code,
    user=user,
    date=now()
  )
  print(message.sid)
  
  
@authenticated_callable
def check_phone_code(code, user_id=""):
  user = get_user(user_id)
  # first expunge old codes
  _now = now()
  for code_row in app_tables.codes.search():
    if _now - code_row['date'] > datetime.timedelta(minutes=10):
      code_row.delete()
  current_code_rows = app_tables.codes.search(order_by("date", ascending=False), user=user, type="phone")
  if len(current_code_rows) > 0:
    latest_code_row = current_code_rows[0]
    code_matches = code == latest_code_row['code']
    if code_matches:
      user['phone'] = latest_code_row['address']
    return code_matches
  else:
    return None
  

def pinged_email(user, start, duration):
  """Email pinged user, if settings allow"""
  print("'pinged_email'")
  if user['pinged_em']:
    name = user['first_name']
    if not name:
      name = "empathy.chat user"
    when = (f"in {h.seconds_to_words((start-now()).seconds)} (from the time of this email)" 
            if start else "now")
    anvil.email.send(
      from_name="empathy.chat", 
      to=user['email'], 
      subject="empathy.chat - match confirmed",
      text=(f'''Dear {name},

Your proposal for a {duration} minute empathy match, starting {when}, has been accepted.

Go to {p.URL_WITH_ALT} to be connected for the empathy exchange.

Thanks!
Tim
empathy.chat
'''
           )
    )
  #p.s. You are receiving this email because you checked the box: "Notify me by email when a match is found." To stop receiving these emails, ensure this option is unchecked when requesting empathy.


# def users_to_email_re_notif(user=None):
#   """Return list of users to email notifications triggered by user

#   Side effect: prune request_em (i.e. switch expired request_em to false)
#   """
#   return []
  #from . import matcher
  #now = now()
  #_prune_request_em()
  #assume_inactive = datetime.timedelta(days=p.ASSUME_INACTIVE_DAYS)
  #min_between = datetime.timedelta(minutes=p.MIN_BETWEEN_R_EM)
  #cutoff_e = now - assume_inactive
  #### comprehension below should probably be converted to loop
  #return [u for u in app_tables.users.search(enabled=True, request_em=True)
  #                if (u['last_login'] > cutoff_e
  #                    and ((not u['last_request_em']) or now > u['last_request_em'] + min_between)
  #                    and u != user
  #                    and c.is_visible(u, user)
  #                    and not matcher.has_status(u))]


# def request_emails(request_type, user):
#   """Email non-active with request_em_check_box checked who logged in recently

#   Non-active means not requesting or matched currently"""
#   if request_type == "receive_first":
#     request_type_text = 'an empathy exchange with someone willing to offer empathy first.'
#   else:
#     assert request_type == "will_offer_first"
#     request_type_text = 'an empathy exchange.'
#   users_to_email = users_to_email_re_notif(user)
#   for u in users_to_email:
#     name = u['name']
#     if not name:
#       name = "empathy.chat user"
#     #anvil.google.mail.send(to=u['email'],
#     #                       subject="Empathy Spot - Request active",
#     text=(
# "Dear " + name + ''',

# Someone has requested ''' + request_type_text + '''

# Return to ''' + p.URL_WITH_ALT + ''' and request empathy to be connected for an empathy exchange (if you are first to do so).

# Thanks!
# Tim
# empathy.chat

# p.s. You are receiving this email because you checked the box: "Notify me of requests by email." To stop receiving these emails, return to the link above and change this setting.
# ''')
#   return len(users_to_email)
