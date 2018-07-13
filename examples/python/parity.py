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

import os
import sys
sys.path.append(os.path.abspath('../..'))

from compiler.compiler import Compiler
from compiler.backends import *
from compiler.utility import circuit_drawer, save_results, order_results

logging.getLogger('compiler.compiler').setLevel(logging.DEBUG)

compiler = Compiler(get_coupling(qx5))
# Oracle can be specified by alias:
#               '00' equals a '00..0000' oracle
#               '10' equals a '10..1010' oracle
#               '11' equals a '11..1111' oracle
#
# Remember that if the backend has 16 qubit, parity will run on 15 qubits because one is used as ancilla
cobj = compiler.compile(15, qx5, algo='parity', oracle='10')
# To draw circuit without running it, uncomment next line and comment the others
# circuit_drawer(cobj['circuit'], filename='parity')
robj = compiler.run(cobj, backend=qx5)
circuit_drawer(robj['ran_qasm'], filename='parity_10')
results = order_results(robj)
save_results(robj, 'parity_10.txt', directory='Data/parity_10/')

# Oracle can also be explicitly set if custom_mode is True
cobj = compiler.compile(15, qx5, algo='parity', oracle='101101011010011', custom_mode=True)
circuit_drawer(cobj['qasm'], filename='parity_10')
robj = compiler.run(cobj, backend=online_sim)
