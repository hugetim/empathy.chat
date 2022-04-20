import unittest
from .relationship import Relationship


class TestRelationshipName(unittest.TestCase):
  def test_last_name_note(self):
    self.assertTrue(Relationship.LAST_NAME_NOTE)
    
  def test_last_name_invisible_by_default(self):
    rel_none = Relationship()
    self.assertFalse(rel_none.last_name_visible)
    self.assertFalse(rel_none.last_initial_visible)
    
  def test_last_name_visible_to_only_close_links(self):
    self.assertFalse(Relationship(distance=1.1).last_name_visible)
    self.assertTrue(Relationship(distance=1).last_name_visible)
    
  def test_last_name_visible_between_host_and_member(self):
    self.assertTrue(Relationship(group_host=True).last_name_visible)
    self.assertTrue(Relationship(my_group_member=True).last_name_visible)
    
  def test_last_initial_visible_to_2nd(self):
    rel2 = Relationship(distance=2)
    self.assertFalse(rel2.last_name_visible)
    self.assertTrue(rel2.last_initial_visible)


class TestRelationshipProfile(unittest.TestCase):
  def test_profile_url_note(self):
    self.assertTrue(Relationship.PROFILE_URL_NOTE)
    
  def test_profile_url_invisible_by_default(self):
    self.assertFalse(Relationship().profile_url_visible)
    
  def test_profile_url_visible_to_close_only(self):
    self.assertTrue(Relationship(distance=1).profile_url_visible)
    self.assertFalse(Relationship(distance=1.1).profile_url_visible)
    self.assertFalse(Relationship(group_host=True).profile_url_visible)
    self.assertFalse(Relationship(my_group_member=True).profile_url_visible)
    