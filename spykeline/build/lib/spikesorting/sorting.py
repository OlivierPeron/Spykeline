import os

import spikeinterface.core as si
import spikeinterface.sorters as ss
import spikeinterface.exporters as sexp 

from pathlib import Path

from config import op, parameters, job_kwargs
from tools import loader, get_group_property
from sorter_params import sorter_dict


def sorter(sorter_name, s_folder, recording_loaded, job_kwargs):
    """
    Run sorting algorithme.

    Parameters
    ----------
    sorter_name : str
        Which sorter to use.
    s_folder : str
        where to save the output.
    recording_loaded : recording
        Recording used in the algorithme of the sorter.
    job_kwargs : dict
        information about the number of jobs and so on.

    Returns
    -------
    sorting : sorting
        Spikes in cluster.

    """
    
    # These 2 sorter are SI based, and not implemented to use the GPU, therefore we parallelise with n_jobs on CPU
    if sorter_name in ['spykingcircus2', 'tridesclous2']:
        full_time = recording_loaded.get_duration()
        sorter_dict[sorter_name]['params']['selection']['n_peaks_per_channel'] = 0.1 * full_time
        sorter_dict[sorter_name]['params']['selection']['min_n_peaks'] = 0.02 * full_time
        sorter_dict[sorter_name]['params']['job_kwargs'] = job_kwargs
    
    if sorter_name == 'mountainsort4':
        sorter_dict[sorter_name]['params']['num_workers'] = job_kwargs['n_jobs']
     
    if sorter_dict[sorter_name]['docker_image'] is None :
        sorting = ss.run_sorter(sorter_name,
                                recording_loaded,
                                s_folder,
                                **sorter_dict[sorter_name]['params'], 
                                verbose = True)

    else :
        sorting = ss.run_sorter(sorter_name, 
                                recording_loaded,
                                s_folder,
                                docker_image = sorter_dict[sorter_name]['docker_image'],
                                **sorter_dict[sorter_name]['params'],
                                verbose = True)
            
    return sorting

def phy_exporter(recording, sorting, paths, metadata):

    if 'ch' in sorting.get_property_keys():
        group_prop = get_group_property(sorting, 
                                        metadata['Shanks_groups'])

        sorting.set_property('group', 
                             group_prop)

        dense_analyzer = si.create_sorting_analyzer(sorting, 
                                                    recording,
                                                    folder = os.path.join(paths['Metadata'], 'Analyzer_dense'),
                                                    format = 'binary_folder',
                                                    sparse = False)
        
    else:
        dense_analyzer = si.create_sorting_analyzer(sorting, 
                                                    recording,
                                                    folder = os.path.join(paths['Metadata'], 'Analyzer_dense'),
                                                    format = 'binary_folder',
                                                    sparse = False)
        
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
                                   method = 'by_property',
                                   peak_sign = 'both',
                                   by_property = 'group')
    
    sorting_analyzer = si.create_sorting_analyzer(sorting,
                                                  recording,
                                                  folder = os.path.join(paths['Metadata'], 'Analyzer_sparsed'),
                                                  format = 'binary_folder',
                                                  sparsity = sparsity)
    
    loader(sorting_analyzer, 'waveforms')

    # TODO : add part to check phy properties using the phy_properties() function.

    sexp.export_to_phy(sorting_analyzer,
                       output_folder = os.path.join(paths['working_folder'], 'Phy'),
                       compute_amplitudes = True,
                       compute_pc_features = True,
                       copy_binary = True,
                       remove_if_exists = False,
                       template_mode = "average",
                       **job_kwargs)
    
    return recording, sorting, sorting_analyzer

def run_sorting(recording, paths, metadata):

    sorter_name = parameters['spikesorting']['sorter']

    if Path(paths['working_folder']).is_dir() :
        sorting = sorter_dict[sorter_name]['exctractor'](os.path.join(paths['working_folder'], sorter_dict[sorter_name]['path']))
    else:
        sorting = sorter(sorter_name,
                         paths['working_folder'],
                         recording,
                         job_kwargs)
        
    print('SpikeSorting step went well, performing post-processing steps ..')

    if not sorting.has_recording():
        sorting.register_recording(recording)

    if parameters['general']['export_to_phy'] or parameters['general']['do_curation']:
        recording, sorting, sorting_analyzer = phy_exporter(recording,
                                                            sorting,
                                                            paths,
                                                            metadata)

    return recording, sorting, sorting_analyzer