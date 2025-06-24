import os

import spikeinterface.core as si
import spikeinterface.sorters as ss

from .sorter_params import sorter_dict

def run_sorting(recordings, paths, metadata):
    """
    Run sorting pipeline.

    Parameters
    ----------
    recording : BaseRecording
        spikeinterface BaseRecording object. The recording to spikesort.
    paths : dict
        Dict with all the required paths.
    metadata : dict
        Dict with channel map information.

    Returns
    -------
    data : dict
        Contains at least 2 keys that are, with their value:
            - 'sorting' : a spikeinterface sorting object
            - 'sorting_analyzer' : a spikeinterface sorting_analyzer object.
    """
    print('Starting SpikeSorting...')

    from .. import spykeparams
    from ..tools import exporter

    sorter_name = spykeparams['spikesorting']['sorter']

    image = None
    # requirements = None
    if spykeparams['spikesorting']['execution_mode'] == 'Docker':
        image = sorter_dict[sorter_name]['docker_image']
        # requirements = ["numpy==1.26.1"]

    if spykeparams['spikesorting']['pipeline'] == 'all':
        merged_recording = si.aggregate_channels(recordings)

        if sorter_name in ['spykingcircus2', 'tridesclous2']:
                full_time = rec.get_duration()
                sorter_dict[sorter_name]['params']['selection']['n_peaks_per_channel'] = int(0.1 * full_time)
                sorter_dict[sorter_name]['params']['selection']['min_n_peaks'] = int(0.02 * full_time)

        sorting = ss.run_sorter(sorter_name,
                                merged_recording,
                                paths['output_folder'],
                                docker_image=image,
                                verbose=True,
                                **sorter_dict[sorter_name]['params'])
        
        if spykeparams['general']['do_curation'] or spykeparams['general']['export_to_phy'] or spykeparams['general']['export_to_klusters']:
                final_recording, final_sorting, sorting_analyzer = exporter(None, 
                                                                            merged_recording,
                                                                            sorting,
                                                                            paths[f'Probe_{id}'],
                                                                            metadata)
        else: 
            sorting_analyzer = None
            final_recording = rec
            final_sorting = sorting

        if not final_sorting.has_recording():
            final_sorting.register_recording(final_recording)

        data = {
            'sorting': final_sorting,
            'sorting_analyzer': sorting_analyzer
        }
        
    elif spykeparams['spikesorting']['pipeline'] == 'by_probe':
        data = []
        for id, rec in enumerate(recordings): 
            if sorter_name in ['spykingcircus2', 'tridesclous2']:
                full_time = rec.get_duration()
                sorter_dict[sorter_name]['params']['selection']['n_peaks_per_channel'] = int(0.1 * full_time)
                sorter_dict[sorter_name]['params']['selection']['min_n_peaks'] = int(0.02 * full_time)
            
            sorting = ss.run_sorter(sorter_name,
                                    rec,
                                    paths[f'Probe_{id}']['base_folder'],
                                    docker_image=image,
                                    verbose=True,
                                    **sorter_dict[sorter_name]['params'])

            if spykeparams['general']['do_curation'] or spykeparams['general']['export_to_phy']:
                final_recording, final_sorting, sorting_analyzer = exporter(id,
                                                                            rec,
                                                                            sorting,
                                                                            paths[f'Probe_{id}'],
                                                                            metadata)
            else: 
                sorting_analyzer = None
                final_recording = rec
                final_sorting = sorting

            if not final_sorting.has_recording():
                final_sorting.register_recording(final_recording)

            tmp = {
                'sorting': final_sorting,
                'sorting_analyzer': sorting_analyzer
                }
            data.append(tmp)

    print('SpikeSorting went well !')

    return data