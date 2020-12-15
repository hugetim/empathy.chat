import anvil.server


@anvil.server.portable_class
class DashProposal():

    def __init__(self, prop_id=None, time_id=None, own=None, name=None, 
                 start_now=None, start_date=None, duration=None, expire_date=None):
        self.prop_id = prop_id
        self.time_id = time_id
        self.own = own
        self.name = name
        self.start_now = start_now
        self.start_date = start_date
        self.duration = duration
        self.expire_date = expire_date

    def __serialize__(self, global_data):
        dict_rep = self.__dict__
        dict_rep['own'] = int(self.own)
        dict_rep['start_now'] = int(self.start_now)
        return dict_rep

    def __deserialize__(self, data, global_data):
        self.__dict__.update(data)
        self.own = bool(self.own)
        self.start_now = bool(self.start_now)