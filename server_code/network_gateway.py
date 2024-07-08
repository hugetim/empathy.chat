import auto_batch.tables as tables
import auto_batch.tables.query as q
from auto_batch.tables import app_tables


def add_message(from_user, to_user, message, time_stamp):
  app_tables.messages.add_row(from_user=from_user,
                              to_user=to_user,
                              message=message,
                              time_stamp=time_stamp)


def _get_messages(user2, user1):
  message_rows = app_tables.messages.search(
    q.fetch_only('message', 'time_stamp', from_user=q.fetch_only('first_name')),
    tables.order_by("time_stamp", ascending=True),
    q.any_of(q.all_of(from_user=user2, to_user=user1),
              q.all_of(from_user=user1, to_user=user2),
            )
  )
  for message_row in message_rows:
    yield dict(from_user=message_row['from_user'], message=message_row['message'], time_stamp=message_row['time_stamp'])


def _get_chat_messages(user2, user1):
  matches = app_tables.matches.search(users=[user2, user1])  # maybe change to normal messages
  chat_rows = app_tables.chat.search(tables.order_by("time_stamp", ascending=True), match=q.any_of(*list(matches)))
  for chat_row in chat_rows:
    yield dict(from_user=chat_row['user'], message=chat_row['message'], time_stamp=chat_row['time_stamp'])


def get_messages(user2, user1):
  messages = list(_get_messages(user2, user1)) + list(_get_chat_messages(user2, user1))
  return sorted(messages, key=lambda m: m['time_stamp'])


def star_row(user2, user1):
  return app_tables.stars.get(user1=user1, user2=user2)


def starred_users(user):
  for row in app_tables.stars.search(q.fetch_only(user2=q.fetch_only('first_name')), user1=user):
    yield row['user2']
  