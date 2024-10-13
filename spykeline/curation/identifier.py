import math

import spikeinterface.curation as sc

from .. import spykeparams
from ..config import op

from .functions import spikes_pearson, find_last_unique_one
from .classifier import classify

def clean_units(data):
    """
    Clean the units, removing any spike having an amplitude greater than the noise threshold.

    Parameters
    ----------
    data : dict
        Contains at least 3 keys that are, with their value:
            - 'recording' : a spikeinterface recording object
            - 'sorting' : a spikeinterface sorting object
            - 'sorting_analyzer' : a spikeinterface sorting_analyzer object.

    Returns
    -------
    cs.sorting : Sorting
        New sorting with artifacts removed
    """
    nb = len(data['sorting_analyzer'].unit_ids) + 1

    cs = sc.CurationSorting(parent_sorting = data['sorting'])

    amp_ext = data['sorting_analyzer'].get_extension("spike_amplitudes")
    amplitudes = amp_ext.get_data()

    spike_vector = data['sorting'].to_spike_vector()

    for unit_id in data['sorting_analyzer'].unit_ids:
        spike_train = data['sorting'].get_unit_spike_train(unit_id)
        spike_vector = data['sorting'].to_spike_vector()
        mask = spike_vector["unit_index"] == unit_id
        amp_filtered = amplitudes[mask]
        assert len(amp_filtered) == len(spike_train), "Amplitude array and spike train have different lengths"
        indexes = op.argwhere(abs(amp_filtered) > spykeparams["noise_amp_th"]).flatten()
        if len(indexes) > 0:
            cs.split(unit_id, indexes, [unit_id, nb])
            cs.remove_unit(nb)
        else:
            continue

    return cs.sorting

def find_noise_units(metrics):
    """
    Identify units that are considered noise, using different metrics from the units.

    Parameters
    ----------
    metrics : dict or pd.DataFrame
        Spikeinterface's metrics for units.

    Returns
    -------
    noise_units : list
        List of units ids that are considered noise.
    """
    # Checking that the inputs contain all needed information
    required_keys = ['FDR', 'isi_violations_count', 'num_spikes', 'presence_ratio', 'firing_rate', 'amplitude_cutoff']
    for key in required_keys:
        assert key in metrics.keys(), f"Missing required key: {key}"

    # Contaminated units
    metrics['FDR'] = metrics['isi_violations_count'] / metrics['num_spikes']
    contaminated_units = [metrics['FDR'].index[i] for i, v in enumerate(metrics['FDR']) if v > 0.1]

    # Time specific noise units
    low_pr = [metrics['presence_ratio'].index[i] for i, v in enumerate(metrics['presence_ratio']) if v < 0.8]

    # highly secific
    specifics_av = op.mean(metrics['firing_rate'].loc[low_pr])
    specifics = [metrics['firing_rate'][low_pr].index[i] for i, v in enumerate(metrics['firing_rate'][low_pr]) if v > specifics_av]

    # Clear noise waveforms

    average_ac = op.mean(metrics['amplitude_cutoff'][low_pr])
    pr_ac = [metrics['amplitude_cutoff'][low_pr].index[i] for i, v in enumerate(metrics['amplitude_cutoff'][low_pr]) if v < average_ac or math.isnan(v)]
    clean_noise_units = [metrics['isi_violations_count'][pr_ac].index[i] for i, v in enumerate(metrics['isi_violations_count'][pr_ac]) if v > 100]

    noise_units = list(set(contaminated_units + specifics + clean_noise_units))

    return noise_units

def identify(channel, spikes, template=None, table=None, split=None):
    """
    Clean and classify the unit.
    This is done in 3 steps, that mainly relies on the distribution of the spikes' pearson correlation with the unit template:
        - Classify :
            Based on the shape of the pearson distribution
        - Identify :
            Delete or split based on the distribution

    Parameters
    ----------
    channel : Channel
        Channel object
    spikes : Array
        Shape [n_samples].
    template : Array, optional
        Template of the unit on its highest amplitude channel. The default is None.
    table : list, optional
        In case of recursive cleaning, stores the spikes to be removed, organized by group of new cluster. The default is None.
    split : list, optional
        List of spikes to split out, again organized by group in case of recursive cleaning. The default is None.

    Returns
    -------
    label : str
        Unit's label.
    remove : list
        Spikes ids to remove from the unit.
    split : list
        Spikes ids to keep in a separated unit, empty except for mua.
    """
    if table is None:
        table = []
    if split is None:
        split = []

    remove = []
    threshold = spykeparams['curation']['distib_th'] * spikes.shape[0]
    if template is None:
        template = op.median(spikes, axis = 0)

    # Step 1: Getting distribution based on pearson correlation
    distrib = spikes_pearson(spikes, template, channel.center)
    hist, bin_edges = op.histogram([x[1] for x in distrib], op.arange(-1, 1, spykeparams['curation']['bin_size']))
    deriv = op.diff(hist)

    # Step 2: Identification of bad channels
    if hist[-1] == 0:
        return 'noise', remove, split

    j = len(hist) - 2
    while hist[j] != 0:
        if j == 0:
            return 'raw', remove, split
        j -= 1

    # Step 3: Cleaning based on distribution
    for i, v in distrib:
        if v < bin_edges[j + 1]:
            remove.append(i)

    # Step 4: Classification based on distribution
    last_var = find_last_unique_one(op.sign(deriv)) + 1

    under_th = len(hist) - 2
    try:
        while hist[under_th] > threshold:
            under_th -= 1

        label, lim = classify(hist, under_th, last_var, deriv)
    except Exception as e:
        return 'raw', remove, split

    # Step 5: Identification of the spikes group to remove
    if label == 'mua':  # recursive code
        mask = [v < bin_edges[lim] and i not in remove for i, v in distrib]
        if spykeparams['curation']['recursive']:
            if table:
                if len(mask) <= 3000:
                    table.append([i for i, v in distrib])
                    remove = table
                    return label, remove, split
                table.append(remove)
                split.append([i for i, v in distrib if v < bin_edges[last_var] and i not in remove])
            else:
                split = [[i for i, v in distrib if v < bin_edges[last_var] and i not in remove]]
                table = [remove]

            identify(channel, spikes[mask], template=None, table=table, split=split)
        else:
            split = [i for i, v in distrib if v < bin_edges[last_var] and i not in remove]
    else:
        remove.extend([i for i, v in distrib if v < bin_edges[lim]])
        if split:
            table.append(remove)
            remove = table

    return label, remove, split