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
from compiler.utility import circuit_drawer, save_results

logging.getLogger('compiler.compiler').setLevel(logging.DEBUG)

compiler = Compiler(get_coupling(qx5))
# It's possible to compile and run on a simulator instead of a real backend, if you want
cobj = compiler.compile(16, qx5)
# To draw circuit without running it, uncomment next line and comment the others
# circuit_drawer(cobj['circuit'], filename='ghz')
robj = compiler.run(cobj, backend=qx5, shots=10)
circuit_drawer(robj['ran_qasm'], filename='ghz')
results = robj['results']
save_results(results, 'ghz.txt', directory='Data/ghz/')
