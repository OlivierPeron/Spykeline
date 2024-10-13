from scipy.signal import find_peaks

from ..config import op
from .identifier import find_noise_units

def classify_obvious_units(sorting_analyzer, metrics):
    """
    
    Classify units based on certain metrics.     

    Parameters
    ----------
    sorting_analyzer : dict
        Spikeinterface' sorting_analyzer object.
    metrics : dict or pd.DataFrame
        Contains the metrics required
    Returns
    -------
    labels : list
        List of labels for each unit. Not labelized units will have a value of 0

    """

    # Checking that the inputs contains all needed informations
    required_metrics = ['num_spikes', 'presence_ratio', 'firing_rate', 'amplitude_cutoff', 'isi_violations_count']
    assert all(metric in metrics.keys() for metric in required_metrics)
    
    labels = op.zeros(len(sorting_analyzer.unit_ids))

    # Some units have no noise in the refractory period, meaning there is no further need to clean them
    cleans = [True if v == 0 else False for i, v in enumerate(metrics['rp_violations'])]
    labels[cleans] = 'clean'

    # Some units have a nb of spike that doesn't allow us to find their metrics, 
    # therefore, these units will stay as they are, be marked as 'raw', and then 
    # they will be identified or merged (most likely) on Phy.
    raws = [v < 3000 and not cleans[i] for i, v in enumerate(metrics['num_spikes'])]
    labels[raws] = 'raw'
    
    ## Noise units
    noises = find_noise_units(metrics)
    for i in noises:
        labels[i] = 'noise'

    return labels

def classify(distribution, x_th, x_dx, deriv):
    """
    
    Classifier of units based on metrics on a distribution.     

    Parameters
    ----------
    distribution : Array
        Distribution of spike's pearson correlation with the unit's template.
    x_th : int
        Value for which the distribution falls below the threshold.
    x_dx : int
        Value of the last variation of the distrib.
    deriv : Array
        Derivative of the distribution.

    Returns
    -------
    label : str
        Unit's label.
    poi : int
        Threshold under which the spikes aren't part of the unit.
        (Point of Interest)

    """
    poi = max(x_th, x_dx)
    
    if x_th < x_dx:
        # if the derivative id is after the threshold one, it means that there is 2 bumps, close one to another, meaning mua
        label =  'mua'
    else:
        # if there is at least one through in the derivative, means that there is a second bump mixed witht the first in the hist
        thrs, _ = find_peaks(-deriv[poi:-1])
        if len(thrs) > 0:
            poi = max(thrs) + poi + 1
            label = 'noisy'
        else:
            label = 'noisy' if poi < int((2/3) * len(distribution)) else 'good'
    return label, poi