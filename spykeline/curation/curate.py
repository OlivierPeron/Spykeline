import os
import pickle
import shutil

import spikeinterface.core as si
import spikeinterface.curation as sc

from collections import Counter, defaultdict
from typing import Dict, Any, Union, Tuple

from ..config import op
from ..tools import loader, exporter
from .classifier import classify_obvious_units, identify
from .unit import Unit, Channel
from .functions import split_unit, spikes_pearson

def analyze_channel(id: int, 
                    templates,
                    unit: Unit, 
                    spikes: op.ndarray) -> None: # type: ignore
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
    from .. import spykeparams

    raw_spikes = spikes[:, :, id]
    mask = op.max(abs(raw_spikes), axis = 1) < spykeparams['curation']['amplitude_threshold'].astype(int)
    clean_spikes = raw_spikes[mask, :]

    raw_remove = op.where(~mask)[0]
    original_ids = op.where(mask)[0]

    _count = Counter(list(map(lambda x : op.argmax(abs(x)), clean_spikes)))
    center = _count.most_common(1)[0][0]

    channel = Channel(id, unit, center)

    label, threshold, remove, split = identify(channel, clean_spikes, templates[unit.id, :, id])

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
    
    raw_remove += original_ids[remove]
    raw_split = original_ids[split]

    channel.labelize(label)
    channel.add('remove', raw_remove)
    channel.add('split', raw_split)
    channel.add('threshold', threshold)
            

def analyze_units(sorting_analyzer: si.AnalyzerExtension, metadata: Dict[str, Any]) -> Dict[int, Unit]:
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
    assert sorting_analyzer.is_sparse(), "The sorting analyzer provided to 'analyze_units()' must be sparsed."

    raw_units = defaultdict(Unit)

    waveform = loader(sorting_analyzer, 'waveforms')
    qms = loader(sorting_analyzer, 'quality_metrics')
    tmp = loader(sorting_analyzer, "templates")
    templates = tmp.get_data()

    groups = sorting_analyzer.sparsity.unit_id_to_channel_ids

    max_amp_ch = si.get_template_extremum_channel(sorting_analyzer, 
                                                  peak_sign='both', 
                                                  mode='extremum')
    
    labels = classify_obvious_units(sorting_analyzer, qms.get_data())

    for u_id in range(len(sorting_analyzer.unit_ids)):
        # Getting the channel index according to the shank, as the sorting is sparsed
        for shank, channels in enumerate(groups[u_id]):
            if max_amp_ch[u_id] in channels:
                max_ch = channels.index(max_amp_ch[u_id]) # Getting the channel index in the shank

        spikes = waveform.get_waveforms_one_unit(u_id)

        probe_id = [probe_id for probe_id, probe in enumerate(metadata['Anatomical_groups']) if max_amp_ch[u_id] in probe][0]

        if labels[u_id] != 0:
            raw_units[u_id] = Unit(u_id, len(spikes), max_ch, groups[u_id], probe_id)
            raw_units[u_id].labelize(labels[u_id])
            continue
        
        raw_units[u_id] = Unit(u_id, len(spikes), max_ch, groups[u_id], probe_id)

        for channel in groups[u_id]:
            analyze_channel(channel, templates, raw_units[u_id], spikes, sorting_analyzer)

        raw_units[u_id].complete_from_channels()

    assert len(raw_units) == len(sorting_analyzer.unit_ids)

    print('All Units have been analyzed, saving ...')

    return raw_units

def apply_curation(data: Dict[str, Union[si.BaseSorting, si.SortingAnalyzer]], 
                   units: Dict[int, Unit], 
                   folder: str) -> Tuple[si.BaseSorting, Dict[int, Unit]]:
    """
    Apply the curation on each unit as presented in units.

    Parameters
    ----------
    data : dict
        Contains:
            - 'sorting' : a spikeinterface sorting object
            - 'sorting_analyzer' : a spikeinterface sorting_analyzer object.
    units : dict
        Dict of instances of Unit, with all the required information for the curation.
    paths : dict
        Dict with the paths to the metadata and the units.
    metadata : dict
        Dict with channel map information.

    Returns
    -------
    cs.sorting : 
        The updated sorting
    units_tmp :
        The updated dict of units within the new sorting.

    """
    print("Applying the curation...")
    final_units = units.copy()
    cs = sc.CurationSorting(parent_sorting = data['sorting'])

    # Actual step where the curation is applied
    for u_id in list(units.keys()):
        final_units, cs = split_unit(int(u_id), final_units, cs)

    # creating a dense analyzer of the curated sorting
    dense_analyzer = si.create_sorting_analyzer(cs.sorting, 
                                                data['sorting']._recording,
                                                folder=os.path.join(folder['tmp'], 'Curated_dense'),
                                                format='binary_folder',
                                                sparse=False)
    
    # Applying the curation on the trash units to get the final units
    print('Re-assigning spikes to their respective units...')
    sorting, final_units = assign_trash(cs,
                                        dense_analyzer, 
                                        final_units)
    
    return sorting, final_units

def assign_trash(cs: sc.CurationSorting,
                 analyzer: si.AnalyzerExtension,
                 units: Dict[int, Unit]) -> Tuple[si.BaseSorting, Dict[int, Unit]]:
    """
    Assign the spikes from the trash units to the units with the highest correlation above the threshold.

    Parameters
    ----------
    sorting : sorting
        A spikeinterface's object. The sorting to update.
    units : dict
        Dict of instances of Unit, with all the required information for the curation.

    Returns
    -------
    sorting : 
        The updated sorting
    units : 
        The updated dict of units within the new sorting.

    """

    from .. import spykeparams

    waveforms = loader(analyzer, 'waveforms')
    tmp = loader(analyzer, "templates")
    templates = tmp.get_data()
    del tmp

    assert len(units) == len(templates)
    # Selecting the units of interest
    groups = [units[u_id].group for u_id in units.keys()]
    processed_groups = []

    for ch_group in groups:
        if ch_group in processed_groups:
            continue
        else:
            processed_groups.append(ch_group)

        group_units = [u_id for u_id in units.keys() if units[u_id].group == ch_group]
        # Finding all trash units of this shank
        trash_units = [unit for unit in group_units if units[unit].label == 'trash']

        if len(trash_units) == 0:
            continue

        merges = defaultdict(defaultdict(list))
        nb_spikes = defaultdict(int)
        
        # Computing the correlation between the spikes of the trash units and the templates of the other units
        for trash_unit in trash_units:
            spikes = waveforms.get_waveforms_one_unit(trash_unit)
            nb_spikes[trash_unit] = len(spikes)
            for spike_id, spike in enumerate(spikes): # For each spike of the trash unit
                correlations = defaultdict(list)
                for unit in group_units: # Comparing with all the other units of the group
                    if unit in trash_unit: # If the unit isn't trash
                        continue
                    else:
                        correlations[unit] = spikes_pearson(spike, templates, units[unit].center)[1]
                max_corr = max(correlations, key=correlations.get)
                if correlations[max_corr] > spykeparams['curation']['correlation_threshold']:   
                    merges[trash_unit][max_corr].append(spike_id)
                else:
                    continue
                    
            del correlations

        # Splitting the trash units according to the correlations
        for trash_unit in trash_units:
            indices_list = op.zeros(nb_spikes[trash_unit])
            id = 1
            for unit, spikes_ls in merges[trash_unit].items():
                if len(spikes_ls) > 0:
                    for spike_id in spikes_ls:
                        assert indices_list[spike_id] == 0, "A spike has been assigned to multiple units"
                        indices_list[spike_id] = id
                    id += 1
            nb_new = int(op.max([op.max(v) for v in indices_list]))
            childs = cs._get_unused_id(nb_new)
            cs.split(trash_unit, indices_list)

            # Merging the splitted trash unit into their respective units with highest correlation above threshold
            merge_id = 0
            for unit, spikes_ls in merges[trash_unit].items():
                if len(spikes_ls) > 0:
                    cs.merge([unit, childs[merge_id]],
                            new_unit_id=unit)
                    merge_id += 1
                units[unit].add('nb_spikes', units[unit].nb_spikes + len(spikes_ls))

            # Handling the current trash unit
            if indices_list.count(0) == 0:
                cs.remove_unit(trash_unit)
                del units[trash_unit]
            else:
                units[trash_unit].add('nb_spikes', indices_list.count(0))

            for i, trash in enumerate(trash_units):
                try:
                    units[trash]
                except:
                    del trash_units[i]

            cs.merge(trash_units, new_unit_id = min(trash_units))
    
    return cs.sorting, units


def run_curation(data: list, metadata: list, folder: str) -> Tuple[Dict[str, Any], Dict[int, Unit]]:
    """
    Run the curation pipeline:
        - Clean the units
        - Analyze the units
        - Apply the curation

    Parameters
    ----------
    data : list
        List of dict where each contains:
            - 'sorting' : a spikeinterface sorting object
            - 'sorting_analyzer' : a spikeinterface sorting_analyzer object.

    Returns
    -------
    Sorting_cured

    """   
    print('The curation is starting !')

    sorting = data['sorting']
    recording = sorting._recording
    sorting_analyzer = data['sorting_analyzer']

    # cleaning step, removing obvious noise from units
    raw_units = analyze_units(sorting_analyzer, metadata)

    os.makedirs(folder['metadata'], exist_ok = True)
    with open(folder['units'], 'wb') as pickle_file:
        pickle.dump(raw_units, pickle_file)
    
    f_sorting, final_units = apply_curation(data, raw_units, folder)

    with open(folder['units_final'], 'wb') as pickle_file:
        pickle.dump(final_units, pickle_file)

    # exporter needed to get the sparsity for each sorting
    final_recording, final_sorting, sorting_analyzer = exporter(recording,
                                                                f_sorting,
                                                                folder,
                                                                metadata,
                                                                mode=1)
    
    if not final_sorting.has_recording():
        final_sorting.register_recording(final_recording)
    
    data = {
            'sorting' : final_sorting,
            'sorting_analyzer' : sorting_analyzer
            }

    return data, final_units