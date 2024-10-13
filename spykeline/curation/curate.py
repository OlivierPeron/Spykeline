import os
import pickle

import numpy as np
import cupy as cp

import spikeinterface.core as si
import spikeinterface.curation as sc

from collections import Counter, defaultdict
from typing import Dict, Any, Union, Tuple

from .. import spykeparams
from ..config import op
from ..tools import loader
from .classifier import classify_obvious_units
from .identifier import clean_units, identify
from .unit import Unit, Channel
from .functions import find_shank, split_unit

def analyze_channel(id: int, unit: Unit, spikes: Union[np.ndarray, cp.ndarray], sorting_analyzer: si.BaseSortingAnalyzer) -> None:
    """
    Analyze a unit's channel.

    Parameters
    ----------
    id : int
        Id of the channel to analyze.
    unit : Unit
        Instance of the Unit class, unit that is being analyzed, channel by channel.
    spikes : Array
        Array with all the spikes from the unit.
    sorting_analyzer : sorting_analyzer
        A spikeinterface's object. Containing information about the sorting.

    Returns
    -------
    raw_units : dict
        Dict of instances of Unit, with all the required information for the curation.

    """

    spikes = spikes[:, :, id]
    _count = Counter(list(map(lambda x : op.argmax(abs(x)), spikes)))
    center = _count.most_common(1)[0][0]

    channel = Channel(id, unit, center)

    tmp = loader(sorting_analyzer, "templates")
    templates = tmp.get_data()
    label, remove, split = identify(channel, spikes, templates[unit.id, :, id])

    if spykeparams['curation']['recursive']:
        try:
            # Putting back the ids to their originals
            if isinstance(remove[0], list): # If the unit is an mua
                tmp_split = [split[0]]
                for j in range(1, len(split)):
                    tmp_split.append([tmp_split[j-1][i] for i in split[j]]) # expending with a list of ids, each id is from the main ch
                split = tmp_split
                
                # then need to modify remove
                tmp_remove = []
                for j in range(1, len(remove)):
                    tmp_remove.extend([split[j-1][i] for i in remove[j]]) 
                remove = tmp_remove
        except:
            pass

    channel.labelize(label)
    channel.add('remove', remove)
    channel.add('split', split)
            

def analyze_units(sorting_analyzer: si.BaseSortingAnalyzer, metadata: Dict[str, Any]) -> Dict[int, Unit]:
    """
    Analyze units, classify them, and identify spikes to remove.

    Parameters
    ----------
    sorting_analyzer : sorting_analyzer
        A spikeinterface's object. Containing information about the sorting.
    metadata : dict
        Dict with channel map information.

    Returns
    -------
    raw_units : dict
        Dict of instances of Unit, with all the required information for the curation.

    """

    raw_units = defaultdict(Unit)

    waveform = loader(sorting_analyzer, 'waveforms')
    qms = loader(sorting_analyzer, 'quality_metrics')

    max_amp_ch = si.get_template_extremum_channel(sorting_analyzer, 
                                                  peak_sign='both', 
                                                  mode='extremum')
    
    labels = classify_obvious_units(sorting_analyzer, qms.get_data())

    for u_id in sorting_analyzer.unit_ids:

        for i in metadata['Shanks_groups']:
            if max_amp_ch[u_id] in i:
                max_ch = i.index(str(max_amp_ch[u_id]))

        shank_id = find_shank(str(max_amp_ch[u_id]), metadata['Shanks_groups'])

        spikes = waveform.get_waveforms_one_unit(u_id)

        if labels[u_id] != 0:
            raw_units[u_id] = Unit(u_id, len(spikes), max_ch, shank_id)
            raw_units[u_id].labelize(labels[u_id])
            continue
        
        raw_units[u_id] = Unit(u_id, len(spikes), max_ch, shank_id)

        for channel in metadata['Shanks_groups'][shank_id]:
            analyze_channel(channel, raw_units[u_id], spikes, sorting_analyzer)

        raw_units[u_id].complete_from_channels()

    assert len(raw_units) == len(sorting_analyzer.unit_ids)

    print('All Units have been analyzed, saving ...')

    return raw_units

def apply_curation(sorting: si.BaseSorting, units: Dict[int, Unit]) -> Tuple[si.BaseSorting, Dict[int, Unit]]:
    """
    Apply the curation on each unit as presented in units.

    Parameters
    ----------
    sorting : sorting
        A spikeinterface's object. The sorting to update.
    units : dict
        Dict of instances of Unit, with all the required information for the curation.

    Returns
    -------
    cs.sorting : 
        The updated sorting
    units_tmp : 
        The updated dict of units within the new sorting.

    """

    cs = sc.CurationSorting(parent_sorting = sorting)

    for u_id in list(units.keys()):
        print(u_id)
        tmp_sorting = cs.sorting
        cs = sc.CurationSorting(parent_sorting = tmp_sorting)
        units_tmp = split_unit(int(u_id), units, cs)
    
    merge_list = []
    for u_id in list(units_tmp.keys()):
        if units_tmp[u_id].label == 'trash':
            merge_list.append(u_id)

    merge_id = cs._get_unused_id()[0]
    cs.merge(merge_list)
    units_tmp[merge_id] = Unit(merge_id, 'trash')
    for trash in merge_list:
        del units_tmp[trash]

    return cs.sorting, units_tmp


def run_curation(data: Dict[str, Any], metadata: Dict[str, Any], paths: Dict[str, str]) -> Tuple[Dict[str, Any], Dict[int, Unit]]:
    """
    Run the curation pipeline.


    Parameters
    ----------
    data : dict
        Contains at least 3 keys that are, with their value:
            - 'recording' : a spikeinterface recording object
            - 'sorting' : a spikeinterface sorting object
            - 'sorting_analyzer' : a spikeinterface sorting_analyzer object.

    Returns
    -------
    Sorting_cured

    """   

    recording = data['recording']

    print('Your data has been properly loaded, the curation will start !')

    # cleaning step, removing obvious noise from units
    sorting_cleaned = clean_units(data)
    
    # Updating the sorting_analyzer
    sorting_analyzer = si.create_sorting_analyzer(sorting_cleaned,
                                                  recording,
                                                  folder = os.path.join(paths['Metadata'], 'Final_analyzer_sparsed'),
                                                  format = 'binary_folder',
                                                  sparse = True,
                                                  method = 'by_property',
                                                  peak_sign = 'both',
                                                  by_property = 'group')

    # curating step, removing/splitting spikes based on the pearson distrib
    if os.path.exists(paths['units']):
        # Reading Pickle data
        with open(paths['units'], 'rb') as pickle_file:
            raw_units = pickle.load(pickle_file)
    else:
        raw_units = analyze_units(sorting_analyzer, metadata)

        os.makedirs(paths['metadata'], exist_ok = True)
        with open(paths['units'], 'wb') as pickle_file:
            pickle.dump(raw_units, pickle_file)
    
    final_sorting, final_units = apply_curation(sorting_cleaned, raw_units)

    with open(paths['units_final'], 'wb') as pickle_file:
        pickle.dump(final_units, pickle_file)

    sorting_analyzer = si.create_sorting_analyzer(final_sorting,
                                                  recording,
                                                  folder = paths['final'],
                                                  format = 'binary_folder',
                                                  sparse = True,
                                                  method = 'by_property',
                                                  peak_sign = 'both',
                                                  by_property = 'group')
    
    final_sorting.save(format = 'npz_folder', 
                       folder = paths['final'], 
                       overwrite = True)
    
    data = {
            'recording' : recording,
            'sorting' : final_sorting,
            'sorting_analyzer' : sorting_analyzer
            }

    return data, final_units