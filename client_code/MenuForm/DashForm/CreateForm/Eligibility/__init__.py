from ._anvil_designer import EligibilityTemplate
from anvil import *
from ..... import glob
from ..... import helper as h
from ..... import relationship as rel


class Eligibility(EligibilityTemplate):
  export_item_keys = ['eligible_all', 'eligible', 'eligible_users', 'eligible_groups', 'eligible_starred']
  
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
    network_size = len(self.item['user_items'])
    all_names_str = h.series_str([item['key'] for item in self.item['user_items']])
    if 0 < network_size <= 2 or len(all_names_str) < 30:
      self.all_radio_button.text += f" (currently: {all_names_str})"
    else:
      self.all_radio_button.text += f" (currently: {network_size} users)"
      self.all_radio_button.tooltip = all_names_str
    self.all_radio_button.selected = self.item.get('eligible_all')
    self.limited_radio_button.selected = not self.all_radio_button.selected
    self.all_radio_button_change()
    self.specific_users_flow_panel.visible = network_size > 1
    self.specific_users_check_box.checked = self.item['eligible_users']
    self.user_multi_select_drop_down.enable_select_all = network_size >= 4
    self.user_multi_select_drop_down.enable_filtering = network_size >= 8
    self.user_multi_select_drop_down.selected = self.item['eligible_users']
    self.starred_check_box.visible = bool(self.item['user_items']) and (self.item['eligible_starred'] or self.item['starred_name_list'] or network_size >= 8)
    if self.starred_check_box.visible:
      if self.item['starred_name_list']:
        name_list_str = h.series_str(list(self.item['starred_name_list']))
        abbrev_list_str = name_list_str if len(name_list_str) < 34 else name_list_str[:30] + "..."
        self.starred_check_box.text = f"My Starred list (currently: {abbrev_list_str})"
        if abbrev_list_str != name_list_str:
          self.starred_check_box.tooltip = f"currently: {name_list_str}"
      else:
        self.starred_check_box.text = 'My Starred list (to add users, go to "My Network" and click the stars by their names)'
    else:
      self.item['eligible_starred'] = False
    has_connections = self.item['user_items'] and self.item['user_items'][0]['value'].distance < rel.UNLINKED
    self.network_check_box.checked = self.item.get('eligible')
    self.network_flow_panel.visible = self.trust_level >= 2 and has_connections and self.network_check_box.checked 
    if self.trust_level >= 3:
      self.drop_down_eligible.items = [("all connections (up to 3 degrees)", 3),
                                       ('"friends of friends" (up to 2 degrees)', 2),
                                      ]
    else: 
      self.drop_down_eligible.items = []
      self.item['eligible'] = min(self.item.get('eligible', 0), 1)
    self.drop_down_eligible.items += [("close connections (1st degree only)", 1),
                                     ]
    self.drop_down_eligible.selected_value = self.item.get('eligible') if self.item.get('eligible') else 1
    n_groups = len(self.item['group_items'])
    self.groups_flow_panel.visible = self.item['group_items'] and (n_groups > 1 or has_connections)
    self.groups_check_box.checked = self.item['eligible_groups']
    self.group_multi_select_drop_down.enable_select_all = n_groups >= 4
    self.group_multi_select_drop_down.enable_filtering = n_groups >= 8
    if not self.item['eligible_groups'] and n_groups == 1:
      self.group_multi_select_drop_down.selected = [self.item['group_items'][0]['value']]
    else:
      self.group_multi_select_drop_down.selected = self.item['eligible_groups']
    if not self.any_visible():
      self.no_one_label.visible = True
    
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

  def all_radio_button_change(self, **event_args):
    """This method is called when this radio button is selected (but not deselected)"""
    self.item['eligible_all'] = self.all_radio_button.selected
    self.limited_flow_panel.visible = not self.item['eligible_all']
