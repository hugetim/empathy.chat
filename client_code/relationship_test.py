import unittest
from .relationship import Relationship


class TestRelationshipName(unittest.TestCase):
  def test_last_name_note(self):
    self.assertTrue(Relationship.last_name_note)
    
  def test_last_name_visible(self):
    self.assertTrue(False)