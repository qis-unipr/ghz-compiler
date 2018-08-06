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
import subprocess
from os import path
import logging
from logging.config import fileConfig

from qiskit import load_qasm_string
from qiskit.dagcircuit import DAGCircuit
from qiskit.qasm import Qasm
from qiskit.tools.visualization import generate_latex_source

logger = logging.getLogger(__name__)
fileConfig(path.join(path.dirname(path.abspath(__file__)), 'logging.ini'))


def circuit_drawer(circuit, filename, directory=None):
    """Saves circuit to pdf

    Parameters:
        circuit (QuantumCircuit, DAGCircuit, Qasm): input circuit, better in Qasm format
        filename (str): filename to write pdf, file extension not needed
        directory (str): directory where the circuit will be saved
    """
    if isinstance(circuit, DAGCircuit):
        circuit = load_qasm_string(circuit.qasm())
    elif isinstance(circuit, str):
        circuit = load_qasm_string(circuit)
    elif isinstance(circuit, Qasm):
        circuit = load_qasm_string(circuit.parse())
    if directory is None:
        directory = ''
    generate_latex_source(circuit, directory+filename + '.tex',
                          basis="id,u0,u1,u2,u3,x,y,z,h,s,sdg,t,tdg,rx,ry,rz,""cx,cy,cz,ch,crz,cu1,cu3,swap,ccx,cswap",
                          scale=0.8)
    if directory == '':
        cmd = ['pdflatex', '-interaction', 'nonstopmode', '%s.tex' % filename]
    else:
        cmd = ['pdflatex', '-interaction', 'nonstopmode', '-output-directory', directory, '%s.tex' % filename]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL)
    proc.communicate()

    retcode = proc.returncode
    if not retcode == 0:
        raise ValueError('Error {} executing command: {}'.format(retcode, ' '.join(cmd)))
    os.unlink('%s.log' % (directory+filename))
    os.unlink('%s.toc' % (directory+filename))
    os.unlink('%s.snm' % (directory+filename))
    os.unlink('%s.nav' % (directory+filename))
    os.unlink('%s.aux' % (directory+filename))


def _order_results(robj):
    """Converts execution results to correct format, based on oracle

    Parameters:
        robj (dict): object returned by compiler.run()

    Returns:
        results (dict): dictionary of value:counts
    """
    stop = robj['n_qubits'] // 2
    results = dict()
    counts = robj['counts']
    connected = robj['connected']
    for count in counts:
        reverse = count[0][::-1]
        if robj['algo'] != 'parity':
            sorted_v = []
            for n in range(robj['n_qubits'] - stop):
                sorted_v.append(reverse[connected[n + stop]])
            for n in range(stop):
                sorted_v.append(reverse[connected[n]])
        else:
            sorted_v = [reverse[connected[0]]]
            one = 1
            zero = robj['n_qubits'] - 1
            for q in robj['oracle']:
                if q == '1':
                    sorted_v.append(reverse[connected[one]])
                    one += 1
                else:
                    sorted_v.append(reverse[connected[zero]])
                    zero -= 1
        value = ''.join(str(v) for v in sorted_v)
        results.update({value: count[1]})
    return results


def save_results(results, filename, directory='Data/'):
    """Saves execution results to file

    Parameters:
        results (dict): dictionary of value:counts
        filename (str): file name
        directory (str): directory where the file will be written
    """
    # results = order_results(robj)
    os.makedirs(os.path.dirname(directory), exist_ok=True)
    os.makedirs(os.path.dirname(directory + filename), exist_ok=True)
    out_f = open(directory + filename, 'w')
    out_f.write('VALUES\t\tCOUNTS\n\n')
    for value, count in results.items():
        out_f.write(value + '\t' + str(count) + '\n')
    out_f.close()
