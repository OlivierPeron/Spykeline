import os

import spikeinterface.core as si
import spikeinterface.sorters as ss

from pathlib import Path

from .. import spykeparams
from ..config import job_kwargs
from ..tools import loader, get_group_property

from .sorter_params import sorter_dict

def sorter(sorter_name, s_folder, recording_loaded, job_kwargs):
    """
    Run sorting algorithm.

    Parameters
    ----------
    sorter_name : str
        Which sorter to use.
    s_folder : str
        Where to save the output.
    recording_loaded : recording
        A spikeinterface object. The recording to spikesort.
    job_kwargs : dict
        Information about the number of jobs and so on.

    Returns
    -------
    sorting : sorting
        Spikes in cluster.
    """
    
    # These 2 sorters are SI based, and not implemented to use the GPU, therefore we parallelize with n_jobs on CPU
    if sorter_name in ['spykingcircus2', 'tridesclous2']:
        full_time = recording_loaded.get_duration()
        sorter_dict[sorter_name]['params']['selection']['n_peaks_per_channel'] = 0.1 * full_time
        sorter_dict[sorter_name]['params']['selection']['min_n_peaks'] = 0.02 * full_time
        sorter_dict[sorter_name]['params']['job_kwargs'] = job_kwargs
    
    if sorter_name == 'mountainsort4':
        sorter_dict[sorter_name]['params']['num_workers'] = job_kwargs['n_jobs']
     
    if sorter_dict[sorter_name]['docker_image'] is None:
        sorting = ss.run_sorter(sorter_name,
                                recording_loaded,
                                s_folder,
                                **sorter_dict[sorter_name]['params'], 
                                verbose=True)
    else:
        sorting = ss.run_sorter(sorter_name, 
                                recording_loaded,
                                s_folder,
                                docker_image=sorter_dict[sorter_name]['docker_image'],
                                **sorter_dict[sorter_name]['params'],
                                extra_requirements=["numpy==1.26.1"],
                                verbose=True)
            
    return sorting

def exporter(recording, sorting, paths, metadata):
    """
    Export the sorting into a sorting analyzer sparse, with required properties.

    Parameters
    ----------
    recording : recording
        A spikeinterface object. The recording to spikesort.
    sorting : sorting
        A spikeinterface sorting object.
    paths : dict
        Dict with all the required paths.
    metadata : dict
        Dict with channel map information.

    Returns
    -------
    recording : 
        A spikeinterface recording object.
    sorting : 
        A spikeinterface sorting object.
    sorting_analyzer : 
        A spikeinterface sorting_analyzer object.
    """

    if 'ch' in sorting.get_property_keys():
        group_prop = get_group_property(sorting, 
                                        metadata['Shanks_groups'])

        sorting.set_property('group', 
                             group_prop)

        dense_analyzer = si.create_sorting_analyzer(sorting, 
                                                    recording,
                                                    folder=os.path.join(paths['Metadata'], 'Analyzer_dense'),
                                                    format='binary_folder',
                                                    sparse=False)
        
    else:
        dense_analyzer = si.create_sorting_analyzer(sorting, 
                                                    recording,
                                                    folder=os.path.join(paths['Metadata'], 'Analyzer_dense'),
                                                    format='binary_folder',
                                                    sparse=False)
        
        loader(dense_analyzer, 'waveforms')
        loader(dense_analyzer, 'fast_templates')
        max_amp_ch = si.get_template_extremum_channel(dense_analyzer, 
                                                      peak_sign='both', 
                                                      mode='extremum')
        
        group_prop = get_group_property(max_amp_ch,
                                        metadata['Shanks_groups'])
        sorting.set_property('group', 
                             group_prop)

    dense_analyzer.sorting.set_property('group', group_prop)
    new_group_prop = get_group_property(recording,
                                        metadata['Shanks_groups'])
    dense_analyzer.recording.set_property('group', new_group_prop)

    sparsity = si.compute_sparsity(dense_analyzer,
                                   method='by_property',
                                   peak_sign='both',
                                   by_property='group')
    
    sorting_analyzer = si.create_sorting_analyzer(sorting,
                                                  recording,
                                                  folder=os.path.join(paths['Metadata'], 'Analyzer_sparsed'),
                                                  format='binary_folder',
                                                  sparsity=sparsity)
    
    loader(sorting_analyzer, 'waveforms')
    
    return recording, sorting, sorting_analyzer


def run_sorting(recording, paths, metadata):
    """
    Run sorting pipeline.

    Parameters
    ----------
    recording : recording
        A spikeinterface object. The recording to spikesort.
    paths : dict
        Dict with all the required paths.
    metadata : dict
        Dict with channel map information.

    Returns
    -------
    data : dict
        Contains at least 3 keys that are, with their value:
            - 'recording' : a spikeinterface recording object
            - 'sorting' : a spikeinterface sorting object
            - 'sorting_analyzer' : a spikeinterface sorting_analyzer object.
    """
    
    sorter_name = spykeparams['spikesorting']['sorter']
    sorting_folder = os.path.join(paths['working_folder'], 'Sorting')

    if Path(sorting_folder).is_dir():
        sorting = sorter_dict[sorter_name]['extractor'](os.path.join(sorting_folder, sorter_dict[sorter_name]['path']))
    else:
        sorting = sorter(sorter_name,
                         sorting_folder,
                         recording,
                         job_kwargs)
        
    print('SpikeSorting step went well, performing post-processing steps ..')

    if not sorting.has_recording():
        sorting.register_recording(recording)

    if spykeparams['general']['export_to_phy'] or spykeparams['general']['do_curation']:
        recording, sorting, sorting_analyzer = exporter(recording,
                                                        sorting,
                                                        paths,
                                                        metadata)
    else: 
        sorting_analyzer = None 

    data = {
            'recording': recording,
            'sorting': sorting,
            'sorting_analyzer': sorting_analyzer
            }

    return data