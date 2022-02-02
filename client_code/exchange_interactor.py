from . import server_misc as sm
from .exchange_gateway import ExchangeRepository
from .exceptions import RowMissingError
import anvil.secrets


def add_chat_message(user_id, message):
  user = sm.get_user(user_id)
  repo = ExchangeRepository(user)
  repo.add_chat(message=anvil.secrets.encrypt_with_key("new_key", message),
                now=sm.now(),
               )
  return update_match_form(user_id, repo=repo)


def update_my_external(my_external, user_id):
  user = sm.get_user(user_id)
  repo = ExchangeRepository(user)
  repo.update_my_external(my_external)

  
def submit_slider(value, user_id):
  user = sm.get_user(user_id)
  repo = ExchangeRepository(user)
  this_match, i = repo.submit_slider(value)
  return their_value(this_match['slider_values'], i)

    
def update_match_form(user_id, repo=None):
  """Return match_state dict
  
  Side effect: Update match['present']"""
  user = sm.get_user(user_id)
  if not repo:
    try:
      repo = ExchangeRepository(user)
    except RowMissingError as err:
      from . import matcher
      matcher.confirm_wait_helper(user)
      partial_state = matcher.get_status(user)
      matcher.propagate_update_needed(user)
      return dict(
        status=partial_state['status'],
        how_empathy_list=[],
        their_name="",
        message_items=[],
        their_value=None,
        their_external=None,
        their_complete=None,
      )
  repo.mark_present()
  this_match, i = repo.exchange_i()
  other_user = their_value(this_match['users'], i)
  _their_value = their_value(this_match['slider_values'], i)
  their_external = their_value(this_match['external'], i)
  their_complete = their_value(this_match['complete'], i)
  how_empathy_list = ([user['how_empathy']]
                      + [u['how_empathy'] for u in this_match['users']
                         if u != user]
                     )
  messages = repo.chat_messages()
  messages_out = [{'me': (user == m['user']),
                   'message': anvil.secrets.decrypt_with_key("new_key", m['message'])}
                  for m in messages]
  their_name = other_user['first_name']
  return dict(
    status="matched",
    how_empathy_list=how_empathy_list,
    their_name=their_name,
    message_items=messages_out,
    their_value=_their_value,
    their_external=their_external,
    their_complete=their_complete,
  )
  
def their_value(values, my_i):
  temp_values = [value for value in values]
  temp_values.pop(my_i)
  if len(temp_values) != 1:
    sm.warning(f"len(temp_values) != 1, but this function assumes dyads only")
  return temp_values[0]                     # return the remaining value
