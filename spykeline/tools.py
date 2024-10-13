import os

import pandas as pd

import xml.etree.ElementTree as ET
import spikeinterface.core as si
import spikeinterface.extractors as se 
import spikeinterface.exporters as sexp 

from spykeline import spykeparams

from spykeline.config import op, job_kwargs

extensions_dict = {
    'waveforms' : {
        'ms_before': 1.5,
        'ms_after': 2.,
        'return_scaled': True
    },
    'random_spikes' : {
        'method': 'uniform',
        'max_spikes_per_unit': op.inf
    },
    'templates' : {
        'ms_before': 1.5,
        'ms_after': 2.0,
        'return_scaled': True,
        'operators': ['average', 'std']
    },
    'spike_amplitudes': {
        'peak_sign': 'neg', 
        'return_scaled': True
    },
    'noise_levels': {
        'num_chunks_per_segment': 20,
        'chunk_size': 10000,
        'return_scaled': True
    },
    'principal_components': {
        'n_components': 5,
        'mode': 'by_channel_local',
        'whiten': True
    },
    'quality_metrics': {
        'metric_names': ['rp_violations', 
                         'num_spikes', 
                         'presence_ratio', 
                         'firing_rate', 
                         'amplitude_cutoff', 
                         'isi_violations_count'],
        'qm_params': None,
        'peak_sign': None,
        'seed': None,
        'skip_pc_metrics': False
    }
}

def define_paths(base_folder, secondary_path):
    """
    Create a dictionary of required paths for Spykeline

    Parameters
    ----------
    base_folder : str or path
        Path to the folder containing input data.
    secondary_path : str or path
        Path to the secondary folder for output data.

    Returns
    -------
    paths : dict
        Dictionary containing all required paths
    """

    session = os.path.basename(base_folder)

    paths = {
        'base_folder' : base_folder,
        'dat' : os.path.join(base_folder, session + '.dat'),
        'xml' : os.path.join(base_folder, session + '.xml'),
        'rhd' : os.path.join(base_folder, 'info.rhd')
    }

    if spykeparams['general']['amplifier_renamed']:
        paths['dat'] = os.path.join(base_folder, 'amplifier.dat')

    if spykeparams['general']['secondary_path']:
        paths['output_folder'] = secondary_path
        paths['working_folder'] = os.path.join(paths['output_folder'], 'SpikeSorting')
    else:
        paths['working_folder'] = os.path.join(paths['base_folder'], 'SpikeSorting')

    paths['metadata'] = os.path.join(paths['working_folder'], 'Metadata')

    if spykeparams['general']['do_curation']:
        paths['units'] = os.path.join(paths['metadata'], 'Original_units_analyzed.pkl')
        paths['units_final'] = os.path.join(paths['metadata'], 'Final_units_analyzed.pkl')

    paths['final'] = os.path.join(paths['working_folder'], 'Final_output')

    return paths

def read_xml(path):
    """
    Read and parse an XML file.

    Parameters
    ----------
    path : str
        Path to xml file.

    Returns
    -------
    Chan_groups : list
        Information about the probes, that is from the neuroscope's .xml file
    shanks_groups : list
        Information about the shanks, that is from the neuroscope's .xml file
    """
    
    tree = ET.parse(path)
    root = tree.getroot()
    
    shanks_groups = []
    Chan_groups = []

    for i in range(len(root)):
        if root[i].tag == 'anatomicalDescription':
            Anat_rt = root[i][0]
        elif root[i].tag == 'spikeDetection':
            Shanks_rt = root[i][0]
    
    for i in range(len(Anat_rt)):
        Chan_groups.append([channel.text for channel in Anat_rt[i].iter('channel')])
    for i in range(len(Shanks_rt)):
        shanks_groups.append([channel.text for channel in Shanks_rt[i].iter('channel')])   
        
    if len(Chan_groups) > len(shanks_groups):
        change = Chan_groups
        Chan_groups = shanks_groups
        shanks_groups = change
        
    return Chan_groups, shanks_groups

def open_recording(rec_path, intan_info):
    """
    Open a recording file.

    Parameters
    ----------
    rec_path : str or Path
        Path to the recording file.
    intan_info : object
        Intan information object.

    Returns
    -------
    multirecording : spikeinterface.core.binaryfolder.BinaryFolderRecording 
        The recording in spikeinterface format
    raw_ch_count : int
        Number of channels in the raw recording (including digital inputs)
    """

    # Defining the recording:
    # → Number of channels
    nb_channel = intan_info.get_num_channels()
    # → channel Gain and Offset (from Intan documentation)
    rec_gains = intan_info.get_property('gain_to_uV')
    rec_offsets = intan_info.get_property('offset_to_uV')
    
    # Asserting that all channels have the same value
    assert all(rec_gains == rec_gains[0])
    assert all(rec_offsets == rec_offsets[0])
    
    # Opening of the recording 
    multirecording = se.BinaryRecordingExtractor(rec_path,
                                                 intan_info.get_sampling_frequency(),  # Sampling rate
                                                 intan_info.get_dtype(), 
                                                 nb_channel,                 
                                                 gain_to_uV=rec_gains[0],
                                                 offset_to_uV=rec_offsets[0],
                                                 is_filtered=intan_info.is_filtered())   
    
    return multirecording

def discard_channels(recording, metadata, channel_list: list):
    """
    Remove channels to discard from the data

    Parameters
    ----------
    recording : 
        spikeinterface Recording object
    metadata: dict
        Dict with channel map information.
    channel_list: list
        List of channel to be removed from the process

    Returns
    -------
    loaded_ext : list
        The required extension
    """  
    all_channels = [channel for shank in metadata['Shanks_groups'] for channel in shank]

    channels_to_keep = []
    for channel in all_channels:
        if channel not in channel_list:
            channels_to_keep.append(channel)
        else:
            for probe in metadata['Anatomical_groups']:
                if channel in probe:
                    probe.remove(channel)
                    break
            for shank in metadata['Shanks_groups']:
                if channel in shank:
                    shank.remove(channel)
                    break

    recording_sliced = recording.channel_slice(channels_to_keep)
    
    return recording_sliced, metadata

def loader(sorting_analyzer, extension: str):
    """
    Load or compute any extension, taking kwargs from extensions_dict.

    Parameters
    ----------
    sorting_analyzer : 
        spikeinterface sorting analyzer object
    extension: str
        Name of the required extension

    Returns
    -------
    loaded_ext : list
        The required extension
    """  

    if extension == 'waveforms':
        loader(sorting_analyzer, 'random_spikes')
    elif extension == 'principal_components':
        loader(sorting_analyzer, 'waveforms')
    elif extension == 'quality_metrics':
        loader(sorting_analyzer, 'noise_levels')
        loader(sorting_analyzer, 'spike_amplitudes')
        
    kwargs = extensions_dict[extension]

    if extension in sorting_analyzer.get_loaded_extension_names():
        loaded_ext = sorting_analyzer.get_extension(extension)
    else:
        loaded_ext = sorting_analyzer.compute(extension, 
                                              **kwargs,
                                              **job_kwargs)
        
    return loaded_ext

def get_group_property(data, sh_grps):
    """
    Get group property for data.

    Parameters
    ----------
    data : 
        spikeinterface recording object or sorting object or a dict.
    sh_grps: list
        List of shanks, one shank being a list of ids

    Returns
    -------
    shanks : list
        List of each unit shank's id
    """   
    if isinstance(data, si.BaseRecording):
        unit_ch = data.channel_ids
        if 'group' in data.get_property_keys():
            data.delete_property('group')
    elif isinstance(data, dict):
        unit_ch = [channel for unit, channel in data.items()]
    else:
        if 'group' in data.get_property_keys():
            data.delete_property('group')
        
        unit_ch = data.get_property('ch')
        
    shanks = []
    for i in unit_ch:
        for x, grp in enumerate(sh_grps):
            if str(i) in grp:
                shanks.append(x)
    
    return shanks

def phy_export(data, paths, units):
    """
    Export data to Phy format.

    Parameters
    ----------
    data : dict
        Contains at least 3 keys that are, with their value:
            - 'recording' : a spikeinterface recording object
            - 'sorting' : a spikeinterface sorting object
            - 'sorting_analyzer' : a spikeinterface sorting_analyzer object.
    paths : dict
        Contains all required paths
    units : dict
        Contains unit information

    Returns
    -------
    None.
    """

    sorting_analyzer = data['sorting_analyzer']

    sexp.export_to_phy(sorting_analyzer,
                       output_folder=paths['final'],
                       compute_amplitudes=False,
                       compute_pc_features=True,
                       copy_binary=True,
                       remove_if_exists=False,
                       template_mode="average",
                       **job_kwargs)
    
    for property in os.listdir(paths['final']):
        if property.endswith('.tsv'):
            file = os.path.join(paths['final'], property)
            os.remove(file)
    
    qms = loader(sorting_analyzer, 
                 "quality_metrics", 
                 metric_names=['firing_rate', 'amplitude_median'], 
                 skip_pc_metrics=True)
    metrics = qms.get_data()
    
    cluster_info = pd.DataFrame(
        {"id": [u_id for u_id in sorting_analyzer.unit_ids], 
         "ch": [units[unit].main_ch for unit in sorting_analyzer.unit_ids],
         "shank": [units[unit].mother for unit in sorting_analyzer.unit_ids], 
         "fr": [fr for fr in metrics["firing_rate"]],
         "Amp": [amp for amp in metrics["amplitude_median"]],
         "n_spikes": [units[unit].nb_spikes for unit in sorting_analyzer.unit_ids],
         "mother_id": [units[unit].mother for unit in sorting_analyzer.unit_ids],
         "HOlylabel": [units[unit].label for unit in sorting_analyzer.unit_ids]
        }
    )
    cluster_info.to_csv(os.path.join(paths['final'], "cluster_info.tsv"), sep="\t", index=False)

    print(f"Your data has been exported to phy format!\nTo open it run the following line in the terminal:\n\n phy template-gui {os.path.join(paths['final'], 'params.py')}")