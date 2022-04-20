import unittest
from .relationship import Relationship
from . import portable as port


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


class TestLastName(unittest.TestCase):
  def test_last_name(self):
    test_name = "Smith"
    rel_none = Relationship()
    rel1 = Relationship(distance=1)
    rel2 = Relationship(distance=2)
    self.assertEqual(port.last_name(test_name, rel_none), "")
    self.assertEqual(port.last_name(test_name, rel1), "Smith")
    self.assertEqual(port.last_name(test_name, rel2), "S.")
    
  def test_no_last_name(self):
    test_name = ""
    rel_none = Relationship()
    rel1 = Relationship(distance=1)
    rel2 = Relationship(distance=2)
    self.assertEqual(port.last_name(test_name, rel_none), "")
    self.assertEqual(port.last_name(test_name, rel1), "")
    self.assertEqual(port.last_name(test_name, rel2), "")

    
class FullNameTest(unittest.TestCase):
  def test_distance(self):
    for distance in range(1, 5):
      self.assertEqual(
        port.full_name("first", "last", distance),
        "first last" if distance <= 1 else ("first" if distance > 2 else "first l.")
      )


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
    