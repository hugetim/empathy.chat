import anvil.users
import anvil.server
from . import parameters as p
from . import invites
from . import groups


MOBILE = None
trust_level = 0
name = ""
invites = invites.Invites()
my_groups = groups.MyGroups()
