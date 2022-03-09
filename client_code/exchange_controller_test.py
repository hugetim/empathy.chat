import unittest
from . import exchange_controller as ec

   
# class Mock():
#   pass


# glob = Mock()
# glob.name = "Tim"


class ExchangeControllerTest(unittest.TestCase):
  def test_messages_plus(self):
    state = ec.ExchangeState(
      status="matched", proptime_id=None, jitsi_code=None, duration=45,
      how_empathy_list=["my how_empathy", "their how_empathy"],
      message_items=[dict(me=True, message="my first"), 
                     dict(me=False, message="their first"),
                     dict(me=False, message="their second"),
                     dict(me=True, message="my second"),
                    ],
      their_name="Sam"
    )
    self.assertEqual(
      state.messages_plus,
      [dict(me=True, message=f"How Tim likes to receive empathy:\nmy how_empathy", label=f"[from Tim's profile]"),
       dict(me=False, message=f"How Sam likes to receive empathy:\ntheir how_empathy", label=f"[from Sam's profile]"),
       dict(me=True, message="my first", label="Tim"), 
       dict(me=False, message="their first", label="Sam"),
       dict(me=False, message="their second"),
       dict(me=True, message="my second"),
      ],
    )
