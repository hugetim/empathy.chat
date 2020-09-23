from .MenuForm.DashForm import DashForm
from .MenuForm.WaitForm import WaitForm
from .MenuForm.MatchForm import MatchForm
from .MenuForm.SettingsForm import SettingsForm


def go_dash(top_form):
  top_form.test_link.visible = True 
  top_form.settings_button.visible = True
  content = DashForm(top_form.name,
                     top_form.tallies)
  top_form.load_component(content)
  
 
def go_match(top_form):
  top_form.test_link.visible = False
  top_form.settings_button.visible = False
  content = MatchForm()
  top_form.load_component(content)
  
  
def go_wait(top_form):
  top_form.test_link.visible = False
  top_form.settings_button.visible = False
  content = WaitForm(top_form.pinged_em_checked)
  top_form.load_component(content)
  
  
def go_settings(top_form):
  top_form.test_link.visible = True
  top_form.settings_button.visible = True
  content = SettingsForm(top_form.re, top_form.re_opts, top_form.re_st)
  top_form.load_component(content)