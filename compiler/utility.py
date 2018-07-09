import logging
from logging.config import fileConfig
import os
import subprocess
from os import path

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
                          scale=0.5)
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


def order_results(robj):
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


def save_results(robj, filename, directory='Data/'):
    """Saves execution results to file

    Parameters:
        robj (dict): ran object
        filename (str): file name
        directory (str): directory where the file will be written
    """
    results = order_results(robj)
    os.makedirs(os.path.dirname(directory), exist_ok=True)
    os.makedirs(os.path.dirname(directory + filename), exist_ok=True)
    out_f = open(directory + filename, 'w')
    out_f.write('VALUES\t\tCOUNTS\n\n')
    for value, count in results.items():
        out_f.write(value + '\t' + str(count) + '\n')
    out_f.close()
