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


DEBUG = False #p.DEBUG_MODE
TEST_TRUST_LEVEL = 10
authenticated_callable = anvil.server.callable(require_user=True)


def now():
  """Return utcnow"""
  return datetime.datetime.utcnow().replace(tzinfo=anvil.tz.tzutc())


def initialize_session(browser_now):
  """initialize session state: user_id, user, and current_row"""
  user = anvil.users.get_user()
  user['browser_now'] = browser_now
  if p.DEBUG_MODE and user['trust_level'] >= TEST_TRUST_LEVEL:
    from . import server_auto_test
    server_auto_test.server_auto_tests()


@anvil.server.callable
def remove_user(user):
  """Remove new user created via Google sign-in"""
  if user and (not user['password_hash']) and (not user['browser_now']):
    user.delete()

    
def get_user(user_id="", require_auth=True):
  if DEBUG:
    print("get_user", user_id)
  logged_in_user = anvil.users.get_user()
  if user_id == "" or logged_in_user.get_id() == user_id:
    return anvil.users.get_user()
  elif (require_auth and logged_in_user['trust_level'] < TEST_TRUST_LEVEL):
    raise RuntimeError("User not authorized to access this information")
  else:
    return app_tables.users.get_by_id(user_id)


def init_user_info(user):
  """Return trust, initializing info for new users & updating trust_level"""
  if user['trust_level'] is None:
    user['request_em'] = False
    user['pinged_sms'] = True
    user['request_em_settings'] = {"fixed": 0, "hours": 2}
    user['first_name'] = ""
    user['last_name'] = ""
    user['how_empathy'] = ""
    user['profile'] = ""
    user['phone'] = ""
    user['confirmed_url'] = ""
  return update_trust_level(user)


def update_trust_level(user):
  """Return trust level based on other info
  
  Side-effect: update user['trust_level']"""
  def matched_with_distance1_member():
    import connections as c
    for user2 in c.member_close_connections(user):
      user2_matches = app_tables.matches.search(users=[user,user2])
      for match in user2_matches:
        both_present = 1
        for i, u in enumerate(match['users']):
          if u in [user, user2] and match['present'][i] == 0:
            both_present = 0
            break
        if both_present:
          return True
    return False
  trust = user['trust_level']
  if not trust:
    trust = 0
  if trust < 1 and user['confirmed_email']:
    trust = 1 # Guest
  if (trust < 2) and user['phone']: # even if not yet confirmed email
    trust = 2 # Confirmed
  if (trust >= 2 and trust < 3) and matched_with_distance1_member():
    trust = 3 # Member
  if (trust >= 3 and trust < 4) and user['confirmed_url']:
    trust = 4 # Partner
  if not user['trust_level'] or trust > user['trust_level']:
    user['trust_level'] = trust
  return user['trust_level']

trust_label = {0: "Visitor",
               1: "Guest",
               2: "Confirmed",
               3: "Member",
               4: "Partner",
               10: "Admin",
              }


def name(user, to_user=None, distance=None):
  if not distance:
    if to_user:
      from . import connections as c
      distance = c.distance(user, to_user)
    else:
      distance = 99
  return port.full_name(user['first_name'], user['last_name'], distance)  


@authenticated_callable
def get_port_user(user2, distance=None, user1_id="", simple=False):
  if user2:
    _name = name(user2, get_user(user1_id) if user1_id else None, distance)
    if simple:
      return port.User(user2.get_id(), _name)
    else:
      return port.User(user2.get_id(), 
                       _name,
                       confirmed_url=bool(user2['confirmed_url']),
                       distance=distance,
                       seeking=user2['seeking_buddy'],
                       starred=None, #True/False
                      )
  else:
    return None

  
def _latest_invited(user):
  inviteds = _inviteds(user)
  if len(inviteds) == 0:
    return None
  else:
    return inviteds[0]

  
def _inviteds(user):
  return app_tables.invites.search(order_by("date", ascending=False), origin=True, user2=user)


def get_prompts(user):
  out = []
  other_prompts = app_tables.prompts.search(user=user)
  if len(other_prompts) > 0:
    for prompt in other_prompts:
      if prompt['dismissed']: continue
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
      for invite in _inviteds(user):
        out.append({"name": "invited", "inviter": name(invite['user1'], to_user=user), 
                    "inviter_id": invite['user1'].get_id(), "rel": invite['relationship2to1']})
    if user['trust_level'] == 2:
      import connections as c
      members = c.member_close_connections(user)
      if members:
        out.append({"name": "member-chat", "members": [get_port_user(m, distance=1, simple=True) for m in members]})
#       else:
#         out.append({"name": "invite-close"})
    elif not invited and not [s for s in out if s['name'] == "connected"]:
      out.append({"name": "invite-close"})
  return out


@authenticated_callable
@anvil.tables.in_transaction
def dismiss_prompt(prompt_id):
  from . import matcher
  matcher.propagate_update_needed()
  prompt = app_tables.prompts.get_by_id(prompt_id)
  prompt['dismissed'] = True
  

@authenticated_callable
def invited_item(inviter_id, user_id=""):
  user = get_user(user_id)
  inviter_user = get_user(inviter_id, require_auth=False)
  inviteds = app_tables.invites.search(order_by("date", ascending=False), origin=True, user1=inviter_user, user2=user)
  return {"inviter": name(inviter_user, to_user=user), "link_key": inviteds[0]['link_key'],
          "inviter_id": inviter_id, "rel": inviteds[0]['relationship2to1']}


@authenticated_callable
def init_profile(user_id=""):
  from . import connections as c
  user = get_user(user_id, require_auth=False)
  record = c.connection_record(user, get_user())
  confirmed_url_date = user['confirmed_url_date'] if user['confirmed_url'] else None
  is_me = user == anvil.users.get_user()
  record.update({'me': is_me,
                 'first': user['first_name'],
                 'last': port.last_name(user['last_name'], record['degree']),
                 'relationships': [] if is_me else c.get_relationships(user),
                 'confirmed_url': user['confirmed_url'],
                 'confirmed_date': confirmed_url_date,
                 'how_empathy': user['how_empathy'],
                 'profile': user['profile'],
                 'trust_label': trust_label[user['trust_level']],
                })
  return record
    
  
@authenticated_callable
def set_seeking_buddy(seeking, user_id=""):
  user = get_user(user_id)
  from . import matcher
  matcher.propagate_update_needed(user)
  user['seeking_buddy'] = seeking
  
  
@authenticated_callable
def save_name(name_item, user_id=""):
  user = get_user(user_id)
  from . import matcher
  matcher.propagate_update_needed(user)
  user['first_name'] = name_item['first']
  user['last_name'] = name_item['last']
  
  
@authenticated_callable
def save_user_item(item_name, text, user_id=""):
  user = get_user(user_id)
  user[item_name] = text
  

def new_jitsi_code():
  if DEBUG:
    print("server_misc.new_jitsi_code()")
  return "empathy-chat-" + random_code()


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
def update_history_form(user2_id, user_id=""):
  """
  Return (iterable of dictionaries with keys: 'me', 'message'), their_value
  """
  user = get_user(user_id)
  user2 = get_user(user2_id, require_auth=False)
  return _update_history_form(user2, user)


def _update_history_form(user2, user1):
  messages = app_tables.messages.search(
    anvil.tables.order_by("time_stamp", ascending=True),
    q.any_of(q.all_of(from_user=user2, to_user=user1),
             q.all_of(from_user=user1, to_user=user2),
            )
  )
  if messages:
    return [{'me': (user1 == m['from_user']),
             'message': anvil.secrets.decrypt_with_key("new_key", m['message']),
             'time_stamp': m['time_stamp'],
            } for m in messages]
  else:
    return []

  
@authenticated_callable
def add_message(user2_id, user_id="", message="[blank test message]"):
  print("add_message", "[redacted]", user_id)
  user = get_user(user_id)
  user2 = get_user(user2_id, require_auth=False)
  app_tables.messages.add_row(from_user=user,
                              to_user=user2,
                              message=anvil.secrets.encrypt_with_key("new_key", message),
                              time_stamp=now())
  _add_message_prompt(user2, user)
  from . import matcher
  matcher.propagate_update_needed(user)
  return _update_history_form(user2, user)

  
def _add_message_prompt(user2, user1):
  such_prompts = app_tables.prompts.search(user=user2, dismissed=False, spec={"name": "message", "from_id": user1.get_id()})
  if len(such_prompts) == 0:
    from_name = name(user1, to_user=user2)
    app_tables.prompts.add_row(user=user2, date=now(), dismissed=False,
                             spec={"name": "message", "from_name": from_name, "from_id": user1.get_id()}
                            )
    _notify_message(user2, from_name)
    

def _connected_prompt(invite, invite_reply):
  return dict(user=invite['user1'],
              spec={"name": "connected", "to_name": name(invite['user2'], distance=invite['distance']), 
                    "to_id": invite['user2'].get_id(), "rel": invite_reply['relationship2to1'],},
              date=now(),
              dismissed=False,
             )


def add_invite_guess_fail_prompt(s_invite):
  prompt_dict = _invite_guess_fail_prompt(s_invite)
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


@authenticated_callable
def add_chat_message(user_id="", message="[blank test message]"):
  from . import matcher
  print("add_chat_message", "[redacted]", user_id)
  user = get_user(user_id)
  this_match = matcher.current_match(user)
  app_tables.chat.add_row(match=this_match,
                          user=user,
                          message=anvil.secrets.encrypt_with_key("new_key", message),
                          time_stamp=now())
  return _update_match_form(user)


@authenticated_callable
def update_match_form(user_id=""):
  """
  Return how_empathy_list, their_name, (iterable of dictionaries with keys: 'me', 'message'), their_value
  """
  user = get_user(user_id)
  return _update_match_form(user)


def _update_match_form(user):
  from . import matcher
  this_match, i = matcher.current_match_i(user)
  if this_match:
    their_value = _their_value(this_match['slider_values'], i)
    how_empathy_list = ([user['how_empathy']]
                        + [u['how_empathy'] for u in this_match['users']
                           if u != user]
                       )
    messages = app_tables.chat.search(anvil.tables.order_by("time_stamp", ascending=True), match=this_match)
    messages_out = [{'me': (user == m['user']),
                     'message': anvil.secrets.decrypt_with_key("new_key", m['message'])}
                    for m in messages]
    [their_name] = [u['first_name'] for u in this_match['users'] if u != user]
    return "matched", how_empathy_list, their_name, messages_out, their_value
  else:
    state = matcher.confirm_wait_helper(user)
    matcher.propagate_update_needed(user)
    return state['status'], [], "", [], None

  
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
  if len(temp_values) != 1:
   print("Warning: len(temp_values) != 1, but this function assumes dyads only")
  return temp_values[0]                     # return the remaining value


def _emails_equal(a, b):
  em_re = re.compile(r"^([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)$")
  a_match = em_re.search(a)
  b_match = em_re.search(b)
  return a_match.group(1) == b_match.group(1) and a_match.group(2).lower() == b_match.group(2).lower()


@authenticated_callable
def get_settings(user_id=""):
  """Return user settings displayed on SettingsForm"""
  user = get_user(user_id)
#   re_opts = user['request_em_settings']
#   if (user['request_em'] == True and re_opts["fixed"]
#       and h.re_hours(re_opts["hours"], user['request_em_set_time']) <= 0):
#     user['request_em'] = False
  return (user['phone'], user['pinged_sms'], user['message_sms']) #user['request_em'], user['request_em_settings'], user['request_em_set_time'], 


def _prune_request_em():
  """Switch expired request_em to false"""
  expired_rem_users = []
  for u in app_tables.users.search(request_em=True):
    if (u['request_em_settings']['fixed']
        and h.re_hours(u['request_em_settings']['hours'], u['request_em_set_time']) <= 0):
      u['request_em'] = False


@authenticated_callable
@anvil.tables.in_transaction
def set_pinged_sms(pinged_sms_checked, user_id=""):
  print("set_pinged_sms", pinged_sms_checked)
  user = get_user(user_id)
  user['pinged_sms'] = pinged_sms_checked

  
@authenticated_callable
@anvil.tables.in_transaction
def set_message_sms(message_sms_checked, user_id=""):
  print("set_message_sms", message_sms_checked)
  user = get_user(user_id)
  user['message_sms'] = message_sms_checked


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


def _number_already_taken(number):
  return bool(len(app_tables.users.search(phone=number)))


def _send_sms(to_number, text):
  account_sid = anvil.secrets.get_secret('account_sid')
  auth_token = anvil.secrets.get_secret('auth_token')
  from twilio.rest import Client
  client = Client(account_sid, auth_token)
  try:
    message = client.messages.create(
      body=text,
      from_='+12312905138',
      to=to_number,
    )
    print("send_sms sid", message.sid)
    return None
  except Exception as exc:
    print(repr(exc))
    return str(exc)
  
    
@authenticated_callable
def send_verification_sms(number, user_id=""):
  if _number_already_taken(number):
    return "number unavailable"
  else:
    user = get_user()
    code = random_code(num_chars=6, digits_only=True)
    error_message = _send_sms(
      number, 
      f"{code} is your empathy.chat verification code. It expires in 10 minutes."
    )
    if error_message:
      return error_message
    else:
      app_tables.codes.add_row(
        type="phone",
        address=number,
        code=code,
        user=user,
        date=now()
      )
      return "code sent"
  
  
@authenticated_callable
@anvil.tables.in_transaction
def check_phone_code(code, user_id=""):
  user = get_user(user_id)
  from . import matcher
  matcher.propagate_update_needed()
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
      any_confirmed = _check_for_confirmed_invites(user)
    return code_matches
  else:
    return None
 

def _check_for_confirmed_invites(user):
  any_confirmed = False
  for invite in _inviteds(user):
    invite_reply = app_tables.invites.get(origin=False, user1=user, link_key=invite['link_key'])
    if invite_reply:
      from . import connections as c
      if c.try_connect(invite, invite_reply):
        any_confirmed = True
      else:
        c.remove_invite_pair(invite, invite_reply, user)
        print("Warning: remove_invite_pair without notifying invited")
    else:
      print("Warning: invite_reply not found", dict(invite))
  return any_confirmed

    
def _addressee_name(user):
  name = user['first_name']
  return name if name else "empathy.chat user"


def _other_name(name):
  return name if name else "Another empathy.chat user"

  
def _message_when(start):
  if start: 
    time_in_words = h.seconds_to_words((start-now()).total_seconds(), include_seconds=False)
    return f"in {time_in_words} (from the time of this message)" 
  else: 
    return "now"

  
def _email_send(to_user, subject, text, from_name="empathy.chat"):
  return anvil.email.send(
    from_name=from_name, 
    to=to_user['email'], 
    subject=subject,
    text=text
  )


def ping(user, start, duration):
  """Notify pinged user"""
  print("'ping'", start, duration)
  subject = "empathy.chat - match confirmed"
  content1 = f"Your proposal for a {duration} minute empathy match, starting {_message_when(start)}, has been accepted."
  content2 = f"Go to {p.URL_WITH_ALT} to be connected for the empathy exchange."
  if user['phone'] and user['pinged_sms']:
    _send_sms(user['phone'], f"{subject}: {content1} {content2}")
  else:
    _email_send(
      to_user=user, 
      subject=subject,
      text=f'''Dear {_addressee_name(user)},

{content1}

{content2}

Thanks!
-empathy.chat
'''
    )
  #p.s. You are receiving this email because you checked the box: "Notify me by email when a match is found." To stop receiving these emails, ensure this option is unchecked when requesting empathy.

  
def notify_cancel(user, start, canceler_name=""):
  """Notify canceled-on user"""
  print("'notify_cancel'", start, canceler_name)
  subject = "empathy.chat - upcoming match canceled"
  content = f"{_other_name(canceler_name)} has canceled your empathy match, previously scheduled to start {_message_when(start)}."
  if user['phone'] and user['pinged_sms']:
    _send_sms(user['phone'], f"{subject}: {content}")
  else:
    _email_send(
      to_user=user, 
      subject=subject,
      text=f'''Dear {_addressee_name(user)},

{content}

-empathy.chat
''')

    
def _notify_message(user, from_name=""):
  """Notify messaged user"""
  print("'_notify_message'", user.get_id(), from_name)
  subject = f"empathy.chat - {_other_name(from_name)} sent you a message"
  content = f"{_other_name(from_name)} has sent you a message on {p.URL}"
  if user['phone'] and user['message_sms']:
    _send_sms(user['phone'], f"empathy.chat - {content}")
  else:
    _email_send(
      to_user=user, 
      subject=subject,
      text=f'''Dear {_addressee_name(user)},

{content}

-empathy.chat
'''
    )
    
  
@anvil.server.http_endpoint('/:name')
def get_doc(name):
  return app_tables.files.get(name=name)['file']


@anvil.server.callable
def get_url(name):
  url = anvil.server.get_api_origin() +'/'+name
  return url


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
  #                if (u['browser_now'] > cutoff_e
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
#     #                       subject="empathy.chat - Request active",
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
