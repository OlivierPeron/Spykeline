import os

import spikeinterface as si
import spikeinterface.preprocessing as spre

from pathlib import Path
from probeinterface.plotting import plot_probe_group

from probe import create_probe
from spikesorting.sorter_params import sorters_params
from config import op, parameters, job_kwargs

def apply_filter(recording):
    """
    Here get the filtering parameters from the parameters and lauch the according filter between :
        - banpass filter
        - lowpass filter
        - highpass filter
    """

    if parameters['preprocessing']['filter']['freq_max'] is None:
        btype = "highpass"
        band = parameters['preprocessing']['filter']['freq_min']
    else:
        btype = "bandpass"
        band = [parameters['preprocessing']['filter']['freq_min'], parameters['preprocessing']['filter']['freq_max']]

    recording_filtered = spre.filter(recording = recording,
                                     band = band,
                                     btype = btype,
                                     ftype = parameters['preprocessing']['filter']['type'])

    return recording_filtered


def apply_common_ref(recording, metadata):

    channel_groups = [[eval(j) for j in grp] for grp in metadata['Shanks_groups']]

    recording_cr = spre.common_reference(recording,
                                         'global',
                                         parameters['preprocessin']['common_reference']['method'],
                                         channel_groups)
    
    return recording_cr



def run_preprocessing(recording, paths, metadata):

    pp_folder = os.path.join(paths['working_folder'], 'Preprocessed')

    if Path(pp_folder).is_dir():
        recording_loaded = si.load_extractor(pp_folder)
    else:
        recording_filtered = apply_filter(recording)
        recording_loaded = apply_common_ref(recording_filtered,
                                            metadata)
        
        # Creation of the recording's probes
        probegroup = create_probe(metadata['Anatomical_groups'],
                                  metadata['Shanks_groups'],
                                  parameters['spikesorting']['sorter'])

        probegroup.set_global_device_channel_indices([grp for grp in metadata['Shanks_groups']])

        # Line to check that the channels_ids are correct
        # -> they have to be ordered from 0 to the total number of channel
        channel_ids = recording_final.get_channel_ids()
        channel_model = op.arange(0, metadata['nb_channels'], 1) 
        assert (channel_ids[c] == channel_model[c] for c in channel_model), "Something is wrong with the way your channels are defined ..."
        
        recording_final = recording_final.set_probegroup(probegroup)

        if parameters['general']['plot_probe']:
            plot_probe_group(recording_final.get_probegroup(),
                             with_device_index = True)
        else:
            pass

        recording_loaded = recording_final.save(folder = pp_folder, 
                                                **job_kwargs)

    return recording_loaded



