# Copyright 2018, Davide Ferrari and Michele Amoretti
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from os import path
import logging
from logging.config import fileConfig

from qiskit import get_backend

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
    return {
        'backend_name': backend,
        'coupling_map': coupling_map
    }
