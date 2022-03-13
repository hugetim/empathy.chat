import unittest
from . import exchange_controller as ec
from . import glob


class MockServer:
  def __init__(self, return_values):
    self.return_values = return_values
    self.call_args = {}
    self.call_kwargs = {}

  def call(self, method, *args, **kwargs):
    self.call_args[method] = args
    self.call_kwargs[method] = kwargs
    return self.return_values[method]
   
    
class ExchangeControllerTest(unittest.TestCase):
  def test_messages_plus(self):
    save_glob_name = glob.name
    glob.name = "Tim"
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
    glob.name = save_glob_name

  def test_slider_status_waiting(self):
    mock_server = MockServer(return_values={'init_match_form': ("prop_id", "jitsi_code", 25, "")})
    ec.server = mock_server
    state = ec.ExchangeState.init_exchange("waiting")
    self.assertEqual(state.slider_status, "waiting")
    self.assertFalse(mock_server.call_args['init_match_form'])
    self.assertEqual(mock_server.call_kwargs['init_match_form'], {})
    
  def test_slider_status_none(self):
    mock_server = MockServer(return_values={'init_match_form': ("prop_id", "jitsi_code", 25, "")})
    ec.server = mock_server
    state = ec.ExchangeState.init_exchange("matched")
    self.assertEqual(state.slider_status, None)
    state.their_slider_value = 7
    self.assertEqual(state.slider_status, None)
   
  def test_slider_status_submitted(self):
    mock_server = MockServer(return_values={'init_match_form': ("prop_id", "jitsi_code", 25, 3)})
    ec.server = mock_server
    state = ec.ExchangeState.init_exchange("matched")
    self.assertEqual(state.slider_status, "submitted")
    
  def test_slider_status_received(self):
    mock_server = MockServer(return_values={'init_match_form': ("prop_id", "jitsi_code", 25, 3)})
    ec.server = mock_server
    state = ec.ExchangeState.init_exchange("matched")
    state.their_slider_value = 7
    self.assertEqual(state.slider_status, "received")

  def tearDown(self):
    import anvil.server
    ec.server = anvil.server