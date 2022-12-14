from anvil.server import portable_class


UNLINKED = 99


@portable_class
class Relationship:
  LAST_NAME_NOTE = ("Only your close links and group hosts (and members of any groups you host) will be able to see your full last name. "
                    "Otherwise, only 2nd degree links (that is, friends of friends) will be able to see your last initial."
                   )
  PROFILE_URL_NOTE = "Only close links are allowed to see this profile URL, aside from the empathy.chat admin."
  
  def __init__(self, distance=UNLINKED, degree=UNLINKED, group_host=False, my_group_member=False):
    self.distance = distance
    self.degree = degree if degree < UNLINKED else distance
    self.group_host = group_host
    self.my_group_member = my_group_member
    
  def __repr__(self):
    return f"Relationship({self.distance}, {self.degree}, {self.group_host}, {self.my_group_member})"
    
  @property
  def last_name_visible(self):
    return self.distance <= 1 or self.group_host or self.my_group_member
    
  @property
  def last_initial_visible(self):
    return self.distance <= 2 or self.last_name_visible
  
  @property
  def profile_url_visible(self):
    return self.distance <= 1
