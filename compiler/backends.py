import logging
from logging.config import fileConfig
from os import path

from qiskit import register, get_backend

from compiler import config

logger = logging.getLogger(__name__)
fileConfig(path.join(path.dirname(path.abspath(__file__)), 'logging.ini'))

qx2 = 'ibmqx2'

qx3 = 'ibmqx3'

qx4 = 'ibmqx4'

qx5 = 'ibmqx5'

online_sim = 'ibmq_qasm_simulator'

local_sim = 'local_qasm_simulator'


def get_coupling(backend):
    """Get coupling map of the backend

    Parameters:
        backend (str): backend name

    Returns:
        coupling_map (dict): backend coupling map
    """
    # register(config.APItoken, config.URL)
    configuration = get_backend(backend).configuration
    couplings = configuration['coupling_map']
    coupling_map = dict()
    for n in range(configuration['n_qubits']):
        coupling_map.update({n: []})
    for coupling in couplings:
        coupling_map[coupling[0]].append(coupling[1])
    return coupling_map
