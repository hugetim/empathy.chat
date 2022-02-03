class DataTableFlatSO:
  def __init__(self, row, field):
    self._row = row
    self._field = field

  def __len__(self):
    return len(self._row[self._field])  
    
  def __getitem__(self, key):
    return self._row[self._field][key]
  
  def __setitem__(self, key, value):
    temp_object = self._row[self._field]
    temp_object[key] = value
    self._row[self._field] = temp_object
