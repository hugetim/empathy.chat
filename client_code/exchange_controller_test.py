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
    return self.return_values.get(method)

  def call_s(self, method, *args, **kwargs):
    return self.call(method, *args, **kwargs)


class DispatchCollector:
  def __init__(self):
    self.dispatches = []
    
  def catch_dispatches(self, dispatch):
    self.dispatches.append(dispatch)


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

  def get_mock_server_without_my_slider_value(self):
    mock_server = MockServer(return_values={'init_match_form': ("prop_id", "jitsi_code", 25, "")})
    ec.server = mock_server
    return mock_server
  
  def test_slider_status_waiting(self):
    mock_server = self.get_mock_server_without_my_slider_value()
    state = ec.ExchangeState.initialized_state("waiting")
    self.assertEqual(state.slider_status, "waiting")
    self.assertFalse(mock_server.call_args['init_match_form'])
    self.assertEqual(mock_server.call_kwargs['init_match_form'], {})
    
  def test_slider_status_none(self):
    mock_server = self.get_mock_server_without_my_slider_value()
    state = ec.ExchangeState.initialized_state("matched")
    self.assertEqual(state.slider_status, None)
    state.their_slider_value = 7
    self.assertEqual(state.slider_status, None)

  def get_state_with_my_slider_value(self):
    mock_server = MockServer(return_values={'init_match_form': ("prop_id", "jitsi_code", 25, 3)})
    ec.server = mock_server
    return ec.ExchangeState.initialized_state("matched")
    
  def test_slider_status_submitted(self):
    state = self.get_state_with_my_slider_value()
    self.assertEqual(state.slider_status, "submitted")
    
  def test_slider_status_received(self):
    state = self.get_state_with_my_slider_value()
    state.their_slider_value = 7
    self.assertEqual(state.slider_status, "received")
  
  def get_update_setup(self, update_value):
    mock_server = MockServer(return_values = {
      'init_match_form': ("prop_id", "jitsi_code", 25, 3),
      'update_match_form': update_value,
    })
    ec.server = mock_server
    state = ec.ExchangeState.initialized_state("matched")
    collector = DispatchCollector()
    for channel in ec.ExchangeState.channels: 
      glob.publisher.subscribe(channel, self, collector.catch_dispatches)
    state.update()
    return state, collector

  def get_baseline_update_value(self):
    return dict(status="matched",
                how_empathy_list=[],
                their_name="",
                message_items=[],
                my_slider_value=3,
                their_slider_value="",
                their_external=False,
                their_complete=False,
               )

  def test_update_baseline(self):
    update_value = self.get_baseline_update_value()
    state, collector = self.get_update_setup(update_value)
    self.assertEqual(len(collector.dispatches), 0)
    state.exit()
  
  def test_update_slider_name(self):
    update_value = self.get_baseline_update_value()
    update_value['their_name'] = "their_name"
    state, collector = self.get_update_setup(update_value)
    self.assertEqual(len(collector.dispatches), 1)
    self.assertEqual(collector.dispatches[0].title, "slider_update")
    self.assertEqual(state.their_name, "their_name")
    state.exit()

  def test_update_slider_value(self):
    update_value = self.get_baseline_update_value()
    update_value['their_slider_value'] = 5
    state, collector = self.get_update_setup(update_value)
    self.assertEqual(len(collector.dispatches), 1)
    self.assertEqual(collector.dispatches[0].title, "slider_update")
    self.assertEqual(state.their_slider_value, 5)
    state.exit()

  def test_update_external(self):
    update_value = self.get_baseline_update_value()
    update_value['their_external'] = True
    state, collector = self.get_update_setup(update_value)
    self.assertEqual(len(collector.dispatches), 1)
    self.assertEqual(collector.dispatches[0].title, "their_external_change"")
    state.exit()

  def test_update_complete(self):
    update_value = self.get_baseline_update_value()
    update_value['their_complete'] = True
    state, collector = self.get_update_setup(update_value)
    self.assertEqual(len(collector.dispatches), 1)
    self.assertEqual(collector.dispatches[0].title, "their_complete_change"")
    state.exit()
  
  def tearDown(self):
    import anvil.server
    ec.server = anvil.server