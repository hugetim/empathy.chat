from ._anvil_designer import EligibilityTemplate
from anvil import *
from ..... import glob
from ..... import helper as h


class Eligibility(EligibilityTemplate):
  export_item_keys = ['eligible', 'eligible_users', 'eligible_groups', 'eligible_starred']
  
  def __init__(self, item, **properties):
    # Set Form properties and Data Bindings.
    self.trust_level = glob.trust_level
    if not item.get('user_items'):
      if 'user_items' not in item:
        item['user_items'] = glob.user_items
      if 'group_items' not in item:
        item['group_items'] = glob.group_items
      item['starred_name_list'] = glob.starred_name_list
    self.init_components(item=item, **properties)
    #alert title: New Empathy Chat Proposal
    #alert buttons: OK, Cancel

    # Any code you write here will run when the form opens.
    self.init()
    
  def init(self):
    self.specific_users_check_box.checked = self.item['eligible_users']
    self.user_multi_select_drop_down.enable_select_all = len(self.item['user_items']) >= 4
    self.user_multi_select_drop_down.enable_filtering = len(self.item['user_items']) >= 8
    if not self.item['eligible_users'] and len(self.item['user_items']) == 1:
      self.user_multi_select_drop_down.selected = [self.item['user_items'][0]['value']]
    else:
      self.user_multi_select_drop_down.selected = self.item['eligible_users']
    self.starred_check_box.visible = bool(self.item['user_items'])
    if self.starred_check_box.visible:
      if self.item['starred_name_list']:
        name_list_str = h.series_str(list(self.item['starred_name_list']))
        abbrev_list_str = name_list_str if len(name_list_str) < 34 else name_list_str[:30] + "..."
        self.starred_check_box.text = f"My Starred list (currently: {abbrev_list_str})"
        if abbrev_list_str != name_list_str:
          self.starred_check_box.tooltip = f"currently: {name_list_str}"
      else:
        self.starred_check_box.text = 'My Starred list (to add users, go to "My Network" and click the stars by their names)'
    has_phone_buddy = self.item['user_items'] and self.item['user_items'][0]['value'].distance == 1
    self.network_flow_panel.visible = self.trust_level >= 2 and has_phone_buddy
    self.network_check_box.checked = self.item['eligible']
    if self.trust_level >= 3:
      self.drop_down_eligible.items = [("all buddies (up to 3 degrees)", 3),
                                       ('"buddies of buddies" (up to 2 degrees)', 2),
                                      ]
    else: 
      self.drop_down_eligible.items = []
      self.item['eligible'] = min(self.item['eligible'], 1)
    self.drop_down_eligible.items += [("close connections (1st degree only)", 1),
                                     ]
    self.drop_down_eligible.selected_value = self.item['eligible'] if self.item['eligible'] else 1
    self.groups_check_box.checked = self.item['eligible_groups']
    self.group_multi_select_drop_down.enable_select_all = len(self.item['group_items']) >= 4
    self.group_multi_select_drop_down.enable_filtering = len(self.item['group_items']) >= 8
    if not self.item['eligible_groups'] and len(self.item['group_items']) == 1:
      self.group_multi_select_drop_down.selected = [self.item['group_items'][0]['value']]
    else:
      self.group_multi_select_drop_down.selected = self.item['eligible_groups']
    
  def form_show(self, **event_args):
    """This method is called when the column panel is shown on the screen"""
    self.user_multi_select_drop_down.add_event_handler('change', self.user_multi_select_drop_down_change)
    self.group_multi_select_drop_down.add_event_handler('change', self.group_multi_select_drop_down_change)    
    
  def any_visible(self):
    return (self.specific_users_flow_panel.visible
            or self.starred_check_box.visible
            or self.network_flow_panel.visible
            or self.groups_flow_panel.visible
           )
    
  def specific_users_check_box_change(self, **event_args):
    """This method is called when this checkbox is checked or unchecked"""
    checked = self.specific_users_check_box.checked
    self.item['eligible_users'] = (
      self.user_multi_select_drop_down.selected if checked else []
    )

  def user_multi_select_drop_down_change(self, **event_args):
    """This method is called when the selected values change"""
    self.specific_users_check_box.checked = self.user_multi_select_drop_down.selected
    self.item['eligible_users'] = self.user_multi_select_drop_down.selected

  def network_check_box_change(self, **event_args):
    """This method is called when this checkbox is checked or unchecked"""
    checked = self.network_check_box.checked
    self.item['eligible'] = self.drop_down_eligible.selected_value if checked else 0  
    
  def drop_down_eligible_change(self, **event_args):
    """This method is called when an item is selected"""
    self.network_check_box.checked = True
    self.item['eligible'] = self.drop_down_eligible.selected_value
 
  def groups_check_box_change(self, **event_args):
    """This method is called when this checkbox is checked or unchecked"""
    checked = self.groups_check_box.checked
    self.item['eligible_groups'] = (
      self.group_multi_select_drop_down.selected if checked else []
    )

  def group_multi_select_drop_down_change(self, **event_args):
    """This method is called when the selected values change"""
    self.groups_check_box.checked = self.group_multi_select_drop_down.selected
    self.item['eligible_groups'] = self.group_multi_select_drop_down.selected
