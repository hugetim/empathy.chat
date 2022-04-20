UNLINKED = 99


class Relationship:
  LAST_NAME_NOTE = ("Only your close links and group hosts (and members of any groups you host) will be able to see your full last name. "
                    "Otherwise, only 2nd degree links (that is, friends of friends) will be able to see your last initial."
                   )
  
  def __init__(self, distance=UNLINKED, degree=UNLINKED, group_host=False, my_group_member=False):
    self.distance = distance
    self.degree = degree
    self.host = group_host
    self.member = my_group_member
    
  @property
  def last_name_visible(self):
    return self.distance <= 1 or self.host or self.member
    
  @property
  def last_initial_visible(self):
    return self.distance <= 2 or self.last_name_visible
  
  @property
  def profile_url_visible(self):
    return self.last_name_visible
