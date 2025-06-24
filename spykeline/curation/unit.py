from collections import Counter

from ..config import op

class Unit:

    def __init__(self,
                 unit_id,
                 nb_spikes,
                 main_ch,
                 group, 
                 probe,
                 mother = None):
        
        self.id = unit_id
        self.nb_spikes = nb_spikes
        self.main_ch = main_ch
        self.group = group
        self.probe = probe
        self.mother = mother
    
        self.label = None
        self.remove = list()
        self.split = list()
        self.center = None
        self.channels = list()
    
    def labelize(self, label):
        self.label = label

    def add(self, key, data):
        assert key in dir(Unit), f"The provided key isn't an attribute of this class, correct attributes are: {repr(dir(Unit))}"
        setattr(self, key, data)

    def add_channel(self, channel):
        self.channels.append(channel)
        channel.add_unit(self.id)

    def get_indices_list(self):
        """
        Creates a list as long as the unit's spike train. It assigns a number to each spike,
        ranging from 0 to len(self.split) + 1.
        This way all the spikes that are part of the unit will get the number 0,
        the spikes of the units to split out will get the following numbers, and
        the spikes to delete have the last assigned number.


        Returns
        -------
        indices_list : list
            List that shall be used for splitting

        """
        indices_list = op.zeros(self.nb_spikes)

        assert self.label is not None
        
        if self.label == 'mua':
            if isinstance(self.split[0], list):
                nb_split = len(self.split)
                for j in range(nb_split, 0, -1):
                    for i in self.split[j - 1]:
                        if indices_list[i] == 0:
                            indices_list[i] = j
            elif isinstance(self.split[0], int):
                for i in self.split:
                    nb_split = 1
                    indices_list[i] = nb_split
            else :
                raise TypeError('Unit\' splitting list not in the correct format, should either be a list of int or a list of list of int')
            
            for i in self.remove:
                indices_list[i] = nb_split + 1
        else:
            for i in self.remove:
                indices_list[i] = 1

        return [indices_list]
    
    def complete_from_channels(self):
        """
        Completes the unit's information (spike to remove or split out) from its channels.

        """

        if 'mua' in [channel.label for channel in self.channels]:
            self.label = 'mua'

            remove = []
            for channel in self.channels:
                remove.extend(channel.remove)

            for nb_split in range(max([len(channel.split) for channel in self.channels])):
                tmp = []
                for channel in self.channels:
                    try:
                        tmp.extend(channel.split[nb_split])
                    except IndexError:
                        pass
                self.split.append(list(set(tmp)))

            self.remove = [i for i in remove if i not in self.split[0]]

        else:
            self.label = self.channels[self.main_ch].label

            remove, split = [], []
            for channel in self.channels:
                remove.extend(channel.remove)
                split.extend(channel.split)

            self.remove = list(set(remove))
            self.split = [spike_id for spike_id in split if spike_id not in self.remove]

        _count = Counter([channel.center for channel in self.channels])
        self.center = _count.most_common(1)[0][0]


class Channel(Unit):
    def __init__(self,
                 id, 
                 unit,
                 center):
        
        self.id = id
        self.center = center

        self.label = None
        self.remove = None
        self.split = None
        self.threshold = None
        self.units = list()

        unit.add_channel(self)

    def add_unit(self, unit_id):
        self.units.append(unit_id)

    def add(self, key, data):
        assert key in dir(Channel), f"The provided key isn't an attribute of this class, correct attributes are: {repr(dir(Channel))}"
        setattr(self, key, data)