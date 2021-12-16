import anvil.users
import anvil.tables
from anvil.tables import app_tables, order_by
import anvil.tables.query as q
import unittest
from . import matcher as m
from . import parameters as p
from . import connections as c
from . import invites
from . import invites_server
from . import server_misc as sm


class InvitesBasicTest(unittest.TestCase):
  def test_conversion(self):
    invite1 = invites.Invite(rel_to_inviter='test subject 1', inviter_guess="6666")
    s_invite1 = invites_server.Invite(invite1)
    self.assertEqual(s_invite1.inviter_guess, "6666")
    invite2 = s_invite1.portable()
    self.assertEqual(invite2.rel_to_inviter, 'test subject 1')


class InvitesTest(unittest.TestCase):
  def setUp(self):
    self.start_time = sm.now()
    self.user = anvil.users.get_user()
    self.poptibo = app_tables.users.get(email="poptibo@yahoo.com")

  def test_invalid_add(self):
    invite1 = invites.Invite(inviter_guess="6666")
    s_invite1 = invites_server.Invite(invite1)
    errors = s_invite1.add()
    self.assertTrue(errors)
    
  def add_link_invite(self):
    self.invite1 = invites.Invite(rel_to_inviter='test subject 1', inviter_guess="6666")
    self.s_invite1 = invites_server.Invite(self.invite1)
    #self.invite1.relay('add')
    errors = self.s_invite1.add()
    self.assertFalse(errors)
    self.invite1 = self.s_invite1.portable()

  def cancel_link_invite(self): 
    self.s_invite1.cancel()
    self.assertFalse(self.s_invite1.inviter)
    
  def add_connect_invite(self):
    port_invitee = sm.get_port_user(self.poptibo, user1_id=self.user.get_id())
    self.invite2 = invites.Invite(rel_to_inviter='test subject 1', inviter_guess="5555", invitee=port_invitee)
    self.s_invite2 = invites_server.Invite(self.invite2)
    errors = self.s_invite2.add()
    self.assertFalse(errors)
    self.invite2 = self.s_invite2.portable()    
 
  def cancel_connect_invite(self): 
    self.s_invite2.cancel()
    self.assertFalse(self.s_invite2.inviter)

  def test_new_link(self):
    self.add_link_invite()
    self.assertEqual(self.invite1.inviter.user_id, self.user.get_id())
    self.assertTrue(self.invite1.link_key)
    self.cancel_link_invite()

  def test_new_link2(self):
    self.test_new_link()

  def test_new_connect1(self):
    self.add_connect_invite()
    self.assertEqual(self.invite2.inviter.user_id, self.user.get_id())
    self.assertFalse(self.invite2.link_key)
    self.assertTrue(self.invite2.invitee)
    self.cancel_connect_invite()   
 
  def test_new_connect2(self):
    self.test_new_connect1()
  
  def test_new_connect_dup(self):
    self.add_connect_invite()
    port_invitee = sm.get_port_user(self.poptibo, user1_id=self.user.get_id())
    invite2dup = invites.Invite(rel_to_inviter='test subject 1 dup', inviter_guess="5555", invitee=port_invitee)
    s_invite2dup = invites_server.Invite(invite2dup)
    errors = s_invite2dup.add()
    self.assertTrue(errors)
    self.cancel_connect_invite()   
    
  def test_new_connect_failed_guess(self):
    port_invitee = sm.get_port_user(self.poptibo, user1_id=self.user.get_id())
    invite2 = invites.Invite(rel_to_inviter='test subject 1 dup', inviter_guess="6666", invitee=port_invitee)
    s_invite2 = invites_server.Invite(invite2)
    errors = s_invite2.add()
    self.assertTrue(errors)
     
  def test_logged_in_visit1(self):
    self.add_link_invite()
    invite2a = invites.Invite(link_key=self.invite1.link_key)
#     s_invite2a = invites_server.Invite(invite2a)
#     errors = s_invite2a.visit(user=self.poptibo)
    errors = invite2a.relay('visit', {'user': self.poptibo}, auth=False)
    self.assertTrue(errors)
    self.assertEqual(errors[0], "The inviter did not accurately provide the last 4 digits of your phone number.")

  def test_logged_in_visit2(self):
    self.add_link_invite()
    self.s_invite1.inviter_guess = self.poptibo['phone'][-4:]
    self.s_invite1.edit_invite()
    invite2b = invites.Invite(link_key=self.s_invite1.link_key)
    errors = invite2b.relay('visit', {'user': self.poptibo}, auth=False)
    self.assertFalse(errors)
    self.assertEqual(invite2b.invitee.user_id, self.poptibo.get_id())
#     errors = invite2b.relay('cancel_response')
#     invite2b.assertFalse(invite2b.invitee)
#     self.assertFalse(errors)

#   def test_new_visit(self):
#     invite2c = invites.Invite(link_key=self.invite1.link_key)
#     errors = invite2c.relay('visit', {'user': None})
#     self.assertFalse(errors)
#     self.assertFalse(invite2c.invitee)
#     errors = invite2c.relay('cancel_response')
#     self.assertFalse(errors)
    
#   def test_connect_invite(self):
#     port_user = anvil.server.call('get_port_user', self.user, 0)
#     port_invitee = anvil.server.call('get_port_user', self.poptibo, user1_id=self.user.get_id())
#     invite3 = invites.Invite(inviter=port_user, rel_to_inviter='test subject 3', inviter_guess="5555", invitee=port_invitee)
#     errors = invite3.relay()
#     self.assertFalse(errors)
#     return port_user, port_invitee
    
#   def test_connect_response(self):
#     port_user, port_invitee = self.test_connect_invite()
#     invite3 = invites.Invite(inviter=port_user, invitee=port_invitee)
#     errors = invite3.relay()
#     self.assertFalse(errors)
#     invite3['invitee_guess'] = "6688"
#     invite3['rel_to_invitee'] = "tester 3"
#     errors = invite3.relay()
#     self.assertFalse(errors)
#     connection_records = anvil.server.call('get_connections')
#     self.assertTrue([r for r in connection_records if r.user_id == self.poptibo.get_id()])
#     anvil.server.call('disconnect', self.poptibo.get_id())

  def tearDown(self):
    test_invites = app_tables.invites.search(user1=q.any_of(self.user, self.poptibo), date=q.greater_than(self.start_time))
    for test_invite in test_invites:
      test_invite.delete()

class SecondsLeftTest(unittest.TestCase):
  def test_initial_requesting(self):
    self.assertEqual(m._seconds_left("requesting"), p.WAIT_SECONDS)
 

class NotifyConnectedTest(unittest.TestCase):
  def test_notify_connected(self):
    class FakeUser(dict):
      def get_id(self):
        return [42,42]
    invite_dict = {'user1': FakeUser(), 'user2': FakeUser(first_name="first", last_name="last"), 'distance': 1}
    invite_reply_dict = {'relationship2to1': "spouse"}
    self.assertEqual(c._connected_prompt(invite_dict, invite_reply_dict)['spec'], 
                     dict(name="connected", to_name="first last", to_id=[42,42], rel="spouse"),
                    )

    
def server_auto_tests(verbosity=2):
  #unittest.main(exit=False)
  import sys
  test_modules = ['auto_test', 'server_auto_test']
  test = unittest.TestLoader().loadTestsFromNames(test_modules)
  unittest.TextTestRunner(stream=sys.stdout, verbosity=verbosity).run(test)
    