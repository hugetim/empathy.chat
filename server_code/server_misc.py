import anvil.users
import anvil.server
import anvil.tables
from anvil.tables import app_tables
import anvil.secrets
import anvil.email
import datetime
import random
import re
from . import parameters as p
from . import helper as h
from . import matcher


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


def get_user(user_id=""):
  if matcher.DEBUG:
    print("get_user", user_id)
  if user_id == "" or anvil.server.session['user_id'] == user_id:
    return anvil.server.session['user']
  else:
    assert anvil.server.session['trust_level'] >= matcher.TEST_TRUST_LEVEL
    return app_tables.users.get_by_id(user_id)


def is_visible(user2, user1=None):
  """Is user2 visible to user1?"""
  if matcher.DEBUG:
    print("server_misc.is_visible")
  if user1 is None:
    user1 = anvil.server.session['user']
  trust1 = user1['trust_level']
  trust2 = user2['trust_level']
  if trust1 is None:
    return False
  elif trust2 is None:
    return False
  else:
    return trust1 > 0 and trust2 > 0

  
def port_eligible_users(others=[]):
  if others:
    return [(other['first_name'], other.get_id()) for other in others]
  else:
    return []


@authenticated_callable
def get_port_eligible_users(user_id=""):
  user = get_user(user_id)
  others = [other for other in app_tables.users.search()
            if (is_visible(other, user) and user['first_name'] is not None)]
  return port_eligible_users(others)


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


def _degree(user2, user1_id=""):
  print("Warning: sm._degree not yet implemented")
  user1 = get_user(user1_id)
  return 0 if user2 == user1 else 1


def _full_name(first, last, degree=3):
  return first + (" " + last if degree <= 2 else "")
    

@authenticated_callable
def get_connections(user_id=""):
  print("get_connections: only direct currently implemented")
  user = get_user(user_id)
  direct_users = [row['user2']
                  for row in app_tables.connections.search(user1=user)]
  return [_connection_record(user2, user_id) for user2 in direct_users]


def _connection_record(user2, user_id=""):
  degree = _degree(user2, user1_id=user_id)
  return {'user_id': user2.get_id(),
          'name': _full_name(user2['first_name'], user2['last_name'], degree),
          'degree': degree,
          'seeking': user2['seeking_buddy'],
          'confirmed': bool(user2['confirmed_url']),
          'last_active': user2['last_login'].strftime("%m/%d/%Y"),
          'starred': None, #True/False
          'status': "", # invited, invite
          'unread_message': None, # True/False
         }


@authenticated_callable
def init_profile(user_id=""):
  user = get_user(user_id)
  record = _connection_record(user)
  confirmed_url_date = (
    user['confirmed_url_date'].strftime("%m/%d/%Y") if user['confirmed_url']
    else ""
  )
  record.update({'me': user == anvil.server.session['user'],
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
  if matcher.DEBUG:
    print("server_misc.new_jitsi_code()")
  num_chars = 5
  charset = "abcdefghijkmnopqrstuvwxyz23456789"
  random.seed()
  rand_code = "".join([random.choice(charset) for i in range(num_chars)])
  code = "empathyspot-" + rand_code
  return code


def prune_messages():
  """Prune messages from fully completed matches"""
  if matcher.DEBUG:
    print("server_misc.prune_messages()")
  all_messages = app_tables.chat.search()
  matches = {message['match'] for message in all_messages}
  for match in matches:
    if min(match['complete']) == 1:
      for row in app_tables.chat.search(match=match):
        row.delete()


@authenticated_callable
def add_message(user_id="", message="[blank]"):
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
def get_settings():
  """Return user settings displayed on SettingsForm"""
  user = get_user()
  re_opts = user['request_em_settings']
  if (user['request_em'] == True and re_opts["fixed"]
      and h.re_hours(re_opts["hours"], user['request_em_set_time']) <= 0):
    user['request_em'] = False
  return (user['request_em'], user['request_em_settings'],
          user['request_em_set_time'])


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
#  user = anvil.server.session['user']
#  user['pinged_em'] = pinged_em_checked
#  return matcher.confirm_wait_helper(user)


@authenticated_callable
@anvil.tables.in_transaction
def set_request_em(request_em_checked):
  print("set_request_em", request_em_checked)
  user = anvil.server.session['user']
  user['request_em'] = request_em_checked
  if request_em_checked:
    user['request_em_set_time'] = now()
  return user['request_em_set_time']


@authenticated_callable
@anvil.tables.in_transaction
def set_request_em_opts(fixed, hours):
  print("set_request_em_opts", fixed, hours)
  user = anvil.server.session['user']
  re_opts = user['request_em_settings']
  re_opts["fixed"] = int(fixed)
  re_opts["hours"] = hours
  user['request_em_settings'] = re_opts
  user['request_em_set_time'] = now()
  return user['request_em_set_time']


@authenticated_callable
def send_sample_sms():
  from twilio.rest import Client

  account_sid = anvil.secrets.get_secret('account_sid')
  auth_token = anvil.secrets.get_secret('auth_token')

  client = Client(account_sid, auth_token)

  message = client.messages.create(
    body="Join Earth's mightiest heroes. Like Kevin Bacon.",
    from_='+12312905138',
    to='+13145706688',
  )

  print(message.sid)


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
  #                    and is_visible(u, user)
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
