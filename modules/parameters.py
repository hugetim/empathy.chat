import anvil.google.auth, anvil.google.drive
from anvil.google.drive import app_files
import anvil.server
import anvil.tables as tables
from anvil.tables import app_tables
import anvil.users
# This is a module.
# You can define variables and functions here, and use them from any form. For example:
#
#    import Module1
#
#    Module1.say_hello()
#

BUFFER_SECONDS = 7
CONFIRM_MATCH_SECONDS = 15 #60
CONFIRM_WAIT_SECONDS = 30 #60*10
WAIT_SECONDS = 55 #60*20
ASSUME_INACTIVE_DAYS = 60 #30 day persistent login + 30 days
TEST_TRUST_LEVEL = 10
