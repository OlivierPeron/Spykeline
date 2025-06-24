
from scipy.stats import pearsonr
from collections import defaultdict
from typing import List, Tuple, Dict, Optional


from ..config import op
from ..curation.unit import Unit

def _find_zero_cross_ids(data) -> List[int]:
    '''
    Find the indices where the data crosses zero.

    Parameters
    ----------
    data : array-like
        The input data.

    Returns
    -------
    List[int]
        The indices where the data crosses zero.
    '''
    data = op.asarray(data)
    ids = list(op.argwhere(data == 0).flatten())
    
    for i, current_value in enumerate(data[1:], start=1): 
        previous_value = data[i - 1]
        product = previous_value * current_value
        if op.sign(product) < 0:
            ids.append(i - 1 if previous_value < 0 else i)
    
    for j, v in enumerate(ids):
        if isinstance(v, op.ndarray):  # Use isinstance for type checking
            ids[j] = v.item()
    
    return ids

def _define_spike_area(spike, center: int) -> Tuple[int, int]:
    '''
    Define the spike area based on zero crossings.

    Parameters
    ----------
    spike : array-like
        The spike data.
    center : int
        The center index.

    Returns
    -------
    Tuple[int, int]
        The start and stop indices of the spike area.
    '''
    ids = _find_zero_cross_ids(spike)
    
    try:
        start = max([i for i in ids if i < center - 2])
    except ValueError:
        start = center - 5 if center > 4 else 0
            
    try:
        stop = min([i for i in ids if i > center + 2])
    except ValueError:
        stop = center + 10 if center < 59 else 69
            
    return int(start), int(stop)


def _derivate(data, dx: int = 1):
    '''
    Calculate the derivative of the data.

    Parameters
    ----------
    data : array-like
        The input data.
    dx : int, optional
        The step size for the derivative calculation. Default is 1.

    Returns
    -------
    array-like
        The derivative of the data.
    '''
    data = op.asarray(data)
    dy_dx = op.zeros_like(data)
    
    dy_dx[1:-1] = (data[2:] - data[:-2]) / (2 * dx)
    dy_dx[0] = (data[1] - data[0]) / dx
    dy_dx[-1] = (data[-1] - data[-2]) / dx
    
    return dy_dx


def spikes_pearson(spikes, template, center: int) -> List[Tuple[int, float]]:
    '''
    Calculate the Pearson correlation between spikes and a template.

    Parameters
    ----------
    spikes : array-like
        The spike data.
    template : array-like
        The template data.
    center : int
        The center index.

    Returns
    -------
    List[Tuple[int, float]]
        A list of tuples containing the spike index and its Pearson correlation coefficient.
    '''
    limits = _define_spike_area(_derivate(template), center)
    spike_area = op.linspace(*limits, limits[1] - limits[0] + 1, dtype=int)

    pears = defaultdict(float)

    for i, spike in enumerate(spikes):
        template_area = op.asnumpy(template[spike_area])
        spike_area_data = op.asnumpy(spike[spike_area])

        pears[i], _ = pearsonr(template_area, spike_area_data)

    indexed_list = sorted(pears.items(), key=lambda x: x[1])

    return indexed_list

def find_last_unique_one(arr) -> Optional[int]:
    '''
    Find the last unique occurrence of 1 in the array.

    Parameters
    ----------
    arr : array-like
        The input array.

    Returns
    -------
    Optional[int]
        The index of the last unique occurrence of 1, or None if not found.
    '''
    arr = op.asarray(arr)
        
    for i in range(len(arr) - 1, 0, -1):
        if arr[i] == 1 and arr[i-1] != 1:
            return i
            
    if arr[0] == 1:
        return 0
        
    return None

def split_unit(u_id: int, units: Dict[int, Unit], cs) -> Dict[int, Unit]:
    """
    Split a unit into multiple units based on its label.

    Parameters
    ----------
    u_id : int
        The id of the sorting unit to split, based on label.
    units : Dict[int, Unit]
        A dictionary of Unit objects.
    cs : spikeinterface curationsorting
        The curationsorting object, used to split the sorting.

    Returns
    -------
    Dict[int, Unit]
        The updated dictionary of Unit objects.
    """
    from .. import spykeparams

    if units[u_id].label in ['raw', 'clean']:
        return units
    
    if units[u_id].label == 'noise':
        if spykeparams['curation']['remove_noise_units']:
            cs.remove_unit(u_id)
            del units[u_id]
        return units
        
    indices_list = units[u_id].get_indices_list()

    if units[u_id].label == 'mua':
        nb_new = int(op.max([op.max(v) for v in indices_list]) + 1)
        childs = cs._get_unused_id(nb_new)
        
        cs.split(u_id, indices_list)
            
        units[childs[0]] = Unit(childs[0], 
                                len([v for v in indices_list[0] if v == 0]), 
                                units[u_id].main_ch, 
                                units[u_id].group,
                                units[u_id].probe,
                                mother = u_id)
        
        units[childs[0]].labelize('good')
        
        if units[u_id].remove:
            units[childs[-1]] = Unit(childs[-1], 
                                     len(units[u_id].remove), 
                                     units[u_id].main_ch,
                                     units[u_id].group,
                                     units[u_id].probe,
                                     mother = u_id)
            units[childs[-1]].labelize('trash')

            for i in range(1, nb_new - 2):
                units[childs[i]] = Unit(childs[i], 
                                        len([v for v in indices_list[0] if v == i]), 
                                        units[u_id].main_ch, 
                                        units[u_id].group, 
                                        units[u_id].probe,
                                        mother = u_id)
                units[childs[i]].labelize('child')
        else:
            for i in range(1, nb_new - 1):
                units[childs[i]] = Unit(childs[i],
                                        len([v for v in indices_list[0] if v == i]), 
                                        units[u_id].main_ch, 
                                        units[u_id].group,
                                        units[u_id].probe, 
                                        mother = u_id)
                units[childs[i]].labelize('child')
        del units[u_id]
        
    else:
        childs = cs._get_unused_id(2)
        cs.split(u_id, indices_list)
        
        if units[u_id].remove:
            units[childs[0]] = Unit(childs[0],
                                    len([v for v in indices_list[0] if v == 0]),
                                    units[u_id].main_ch,
                                    units[u_id].group,
                                    units[u_id].probe,
                                    mother = u_id)
            units[childs[0]].labelize('good')

            units[childs[1]] = Unit(childs[1],
                                    len([v for v in indices_list[0] if v == 1]),
                                    units[u_id].main_ch,
                                    units[u_id].group,
                                    units[u_id].probe,
                                    mother = u_id)
            units[childs[1]].labelize('trash')
        
        del units[u_id]

    return units, cs