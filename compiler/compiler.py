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
import operator
from time import sleep
import pickle
from concurrent.futures import CancelledError, TimeoutError
import pkg_resources
from sympy import pi

from IBMQuantumExperience import IBMQuantumExperience
from qiskit import QuantumRegister, ClassicalRegister, QuantumCircuit, compile, QISKitError
from qiskit.backends import JobStatus
from qiskit.backends.ibmq.ibmqjob import IBMQJobError
from qiskit.dagcircuit import DAGCircuit
from qiskit.wrapper import load_qasm_string

from compiler.backends import *
from compiler import config

logger = logging.getLogger(__name__)
fileConfig(path.join(path.dirname(path.abspath(__file__)), 'logging.ini'))


class Compiler(object):
    """Compiler class
    TODO More detailed class description
    """

    def __init__(self, backend_info):
        # Class constructor
        self._coupling_map = backend_info['coupling_map'].copy()
        self._inverse_coupling_map = dict()
        self._path = dict()
        self._n_qubits = 0
        self._ranks = dict()
        self._connected = dict()
        self._most_connected = []
        self.__pickle_data = None
        if backend_info['coupling_map']:
            if os.path.isfile(pkg_resources.resource_filename(__name__, 'trees/' + backend_info['backend_name'] + '.p')):
                print('Found pickle')
                pickle_file = open(pkg_resources.resource_filename(__name__, 'trees/' + backend_info['backend_name'] + '.p'), 'rb')
                self.__pickle_data = pickle.load(pickle_file)
                print(self.__pickle_data)
                pickle_file.close()
            if self.__pickle_data is None or backend_info['coupling_map'] != self.__pickle_data['coupling_map']:
                self._invert_graph(backend_info['coupling_map'], self._inverse_coupling_map)
                self._start_explore(self._coupling_map, self._ranks)
                self._most_connected = self._find_max(self._ranks)
                self._spanning_tree(self._most_connected[0], inverse_map=self._inverse_coupling_map,
                                    ranks=sorted(self._ranks.items(), key=operator.itemgetter(1), reverse=True))
                pickle_file = open(pkg_resources.resource_filename(__name__, 'trees/' + backend_info['backend_name'] + '.p'), 'wb')
                pickle.dump({'coupling_map': self._coupling_map,
                             'inverse_coupling_map': self._inverse_coupling_map,
                             'path': self._path,
                             'ranks': self._ranks,
                             'most_connected': self._most_connected}, pickle_file)
                pickle_file.close()
            else:
                print('pickle used')
                self._inverse_coupling_map = self.__pickle_data['inverse_coupling_map']
                self._path = self.__pickle_data['path']
                self._ranks = self.__pickle_data['ranks']
                self._most_connected = self.__pickle_data['most_connected']
        else:
            logger.critical('Missing coupling map')
            exit(1)

    def _explore(self, source, visiting, visited, ranks):
        # Recursively explores the graph, avoiding already visited nodes
        for next in self._coupling_map[visiting]:
            if next not in visited[source]:
                visited[source].append(next)
                ranks[next] = ranks[next] + 1
                self._explore(source, next, visited, ranks)

    def _start_explore(self, graph, ranks):
        # Starts exploring the graph assign a rank to nodes,
        # node rank is based on how many other nodes can reach the node
        visited = dict()
        for node in range(len(graph)):
            ranks[node] = 0
        for source in graph:
            visited.update({source: []})
            self._explore(source, source, visited, ranks)

    @staticmethod
    def _invert_graph(graph, inverse_graph=None):
        # Inverts the edges of the graph
        if inverse_graph is None:
            inverse_graph = {}
        for end in graph:
            for start in graph[end]:
                if start not in inverse_graph:
                    inverse_graph.update({start: [end]})
                else:
                    inverse_graph[start].append(end)
        for node in graph:
            if node not in inverse_graph:
                inverse_graph.update({node: []})
        logger.debug('inverse coupling map: %s', str(inverse_graph))

    @staticmethod
    def _find_max(ranks):
        # Returns the node with highest rank
        most_connected = max(ranks.items(), key=operator.itemgetter(1))[0]
        found = [most_connected, ranks[most_connected]]
        logger.debug('Node with highest rank is %d, with rank %d', found[0], found[1])
        return found

    def _spanning_tree(self, start, inverse_map, ranks):
        # Creates a list of edges to follow when compiling a circuit
        ranks = dict(ranks)
        self._path.update({start: -1})
        del ranks[start]
        to_connect = [start]
        max = len(self._coupling_map)
        count = max - 1
        visiting = 0
        updated = True
        while count > 0:
            if updated is False:
                for inv in ranks:
                    for node in inverse_map[inv]:
                        if node in to_connect:
                            to_connect.append(inv)
                            logger.debug('Found inverse path to node %d', inv)
                            logger.debug('to connect: %s', str(to_connect))
                            del ranks[inv]
                            self._path.update({inv: node})
                            logger.debug('path: %s', str(self._path))
                            updated = True
                            count -= 1
                            break
                    if updated is True:
                        break
            if count > 0:
                for node in inverse_map[to_connect[visiting]]:
                    if node not in self._path:
                        self._path.update({node: to_connect[visiting]})
                        logger.debug('path: %s', str(self._path))
                        del ranks[node]
                        count -= 1
                        if node not in to_connect:
                            to_connect.append(node)
                            logger.debug('to connect: %s', str(to_connect))
                        if count <= 0:
                            break
                visiting += 1
                if visiting == len(to_connect):
                    updated = False
                    logger.debug('No more direct paths to explore, searching an inverse one')

    def _cx(self, circuit, control_qubit, target_qubit, control, target):
        # Places a cnot gate between the control and target qubit,
        # inverts it to sastisfy couplings if needed
        if target in self._coupling_map[control]:
            circuit.cx(control_qubit, target_qubit)
            logger.debug('Connected qubit %d to qubit %d with cnot gate', control, target)
        elif control in self._coupling_map[target]:
            circuit.u2(0, pi, control_qubit)
            circuit.u2(0, pi, target_qubit)
            circuit.cx(target_qubit, control_qubit)
            circuit.u2(0, pi, control_qubit)
            circuit.u2(0, pi, target_qubit)
            logger.debug('Connected qubit %d to qubit %d with inverse cnot gate', control, target)
        else:
            exit(3)

    def _place_cx(self, circuit, quantum_r, stop, oracle='11'):
        # Places all needed cnot gates fro the specified oracle
        if not oracle == '00':
            for qubit in self._connected:
                if self._connected[qubit] != -1:
                    if oracle == '11':
                        self._cx(circuit, quantum_r[qubit], quantum_r[self._connected[qubit]], qubit,
                                 self._connected[qubit])
                    elif oracle == '10':
                        if stop > 0:
                            self._cx(circuit, quantum_r[qubit], quantum_r[self._connected[qubit]], qubit,
                                     self._connected[qubit])
                            stop -= 1
                        else:
                            break

    def _place_h(self, circuit, start, quantum_r, initial=True, x=True):
        # Places Hadamard gates in the circuit
        for qubit in self._connected:
            if qubit != start:
                circuit.u2(0, pi, quantum_r[qubit])
            else:
                if initial is True:
                    if x is True:
                        circuit.u3(pi, 0, pi, quantum_r[qubit])
                else:
                    circuit.u2(0, pi, quantum_r[qubit])

    def _place_x(self, circuit, quantum_r):
        # Places Pauli-x gates needed for envariance
        sorted_c = sorted(self._connected.items(), key=operator.itemgetter(0))
        s_0 = self._n_qubits // 2
        i = 0
        count = self._n_qubits - 1
        for qubit in sorted_c:
            if count <= 0:
                break
            if i >= s_0:
                circuit.u3(pi, 0, pi, quantum_r[qubit[0]])
            else:
                circuit.iden(quantum_r[qubit[0]])
            i += 1
        i = 0
        for qubit in sorted_c:
            if i >= s_0:
                circuit.iden(quantum_r[qubit[0]])
            else:
                circuit.u3(pi, 0, pi, quantum_r[qubit[0]])
            i += 1

    def _measure(self, circuit, quantum_r, classical_r):
        # Places measure gates at the edn of the circuit
        # circuit.barrier()
        for qubit in self._connected:
            circuit.measure(quantum_r[qubit], classical_r[qubit])

    def _create(self, circuit, quantum_r, classical_r, n_qubits, x=True, oracle='11', custom_mode=False):
        # Creates the circuit based on input parameters
        stop = 0
        if custom_mode is False and len(oracle) != 2:
            logger.critical('custom mode set to False but oracle %s is not a known alias', oracle)
            exit(5)
        elif custom_mode is False and len(oracle) == 2:
            stop = n_qubits // 2
        else:
            for i in oracle:
                if i == '1':
                    stop += 1

        self._n_qubits = n_qubits

        max_qubits = len(self._path)
        if max_qubits < self._n_qubits:
            logger.critical('Maximum qubits allowed for backend is %d but n_qubits = %d', max_qubits, n_qubits)
            exit(2)

        self._connected.clear()
        count = self._n_qubits
        for qubit in self._path:
            if count <= 0:
                break
            self._connected.update({qubit: self._path[qubit]})
            count -= 1
        self._place_h(circuit, self._most_connected[0], quantum_r, x=x)
        if custom_mode is False:
            self._place_cx(circuit, quantum_r, stop, oracle=oracle)
        else:
            self._place_cx(circuit, quantum_r, stop, oracle='10')
        self._place_h(circuit, self._most_connected[0], quantum_r, initial=False)
        if x is True:
            self._place_x(circuit, quantum_r)
        self._measure(circuit, quantum_r, classical_r)
        circuit = self.optimize_h(circuit)
        cobj = {
            'circuit': circuit,
            'connected': self._connected.copy(),
            'n_qubits': n_qubits
        }
        return cobj

    @staticmethod
    def optimize_h(circuit):
        """Optimize Hadamard gates by removing doubles, which corresponds to identity

        Parameters:
            circuit (QuantumCircuit): circuit to be optimized

        Returns:
            optimized circuit (QuantumCircuit): the optimized circuit
        """
        dag_circuit = DAGCircuit.fromQuantumCircuit(circuit)
        h = dag_circuit.get_named_nodes('u2')
        for node in h:
            if dag_circuit.multi_graph.node[node] is not None and dag_circuit.multi_graph.node[node]['params'] == [0,
                                                                                                                   pi]:
                edge = dag_circuit.multi_graph.in_edges(node)
                pred = []
                for e in edge:
                    pred = e[0]
                if dag_circuit.multi_graph.node[pred]['name'] == 'u2' and dag_circuit.multi_graph.node[pred][
                    'params'] == [0, pi]:
                    logger.debug('Two consecutive Hadamard gates on qubit %s removed',
                                 str(dag_circuit.multi_graph.node[pred]['qargs']))
                    dag_circuit._remove_op_node(pred)
                    dag_circuit._remove_op_node(node)
        return load_qasm_string(dag_circuit.qasm())

    @staticmethod
    def _sort_connected(connected, algo='ghz'):
        # Sort list of connected qubits
        # Returns sorted list
        if algo == 'parity':
            return list(connected.keys())
        else:
            return list(zip(*sorted(connected.items(), key=operator.itemgetter(0))))[0]

    def set_size(self, backend, n_qubits):
        """Checks if number of qubits is consistent with backend and set register size accordingly

        Parameters:
            backend (str): backend name
            n_qubits (int): number of qubits

        Returns:
            size (int): register size
        """
        size = 0
        if backend == qx2 or backend == qx4:
            if n_qubits <= 5:
                size = 5
            else:
                logger.critical('Maximum qubits allowed for %s backend is 5 but n_qubits = %d', backend, n_qubits)
                exit(1)
        elif backend == qx3 or backend == qx5:
            if n_qubits <= 16:
                size = 16
            else:
                logger.critical('Maximum qubits allowed for %s backend is 16 but n_qubits = %d', backend, n_qubits)
                exit(4)
        elif backend == online_sim or backend == local_sim:
            size = len(self._coupling_map)
        else:
            logger.critical('Backend %s not known', backend)
            exit(5)
        return size

    @staticmethod
    def set_oracle(oracle, n_qubits):
        """Creates explicit oracle string based on oracle alias

        Parameters:
            oracle (str): oracle alias, either '00', '10 or '11'
            n_qubits (int): number of qubits

        Returns:
            oracle (str): explicit oracle string
        """
        if oracle != '10':
            for i in range(2, n_qubits - 1, 1):
                oracle += oracle[i - 1]
        else:
            oracle = ''
            one = True
            for i in range(n_qubits - 1):
                if one is True:
                    one = False
                    oracle += '1'
                else:
                    one = True
                    oracle += '0'
        return oracle

    def compile(self, n_qubits, backend=online_sim, algo='ghz', oracle='11', custom_mode=False, compiling=False):
        """Compiles circuit according to input parameters

        Parameters:
            n_qubits (int): number of qubits used in circuit
            backend (str): backend on wich circuit will be compiled
            algo (str): alias of algorithm to implement, can be either 'ghz', 'envariance' or 'parity'
            oracle (str): oracle, can be an alias or explicit oracle representation; it's '11' for ghz and envariance
            custom_mode (bool): set True fro explicit oracle representation
            compiling (bool): set to True fi you want to let qiskit remap your circuit, which is generally not needed

        Returns:
            cobj (dict): compiled object, dictionary containing results of compiling, for example:

                                cobj = {
                                circuit: compiled circuit as QuantumCircuit,
                                qasm: compiled circuit as Qasm,
                                n_qubits: number of qubits used in circuit,
                                connected: list of connected qubits, in th order they were connected,
                                oracle: specified oracle,
                                algo: specified algorithm,
                                compiled: qobj to be run on the backend }
        """
        size = self.set_size(backend, n_qubits)

        quantum_r = QuantumRegister(size, "qr")
        classical_r = ClassicalRegister(size, "cr")

        circuit = QuantumCircuit(quantum_r, classical_r, name=algo)

        cobj = dict()

        if algo == 'parity':
            if n_qubits > len(self._path) - 1:
                exit(6)
            n_qubits += 1

        if algo == 'ghz':
            cobj = self._create(circuit, quantum_r, classical_r, n_qubits, x=False)
        elif algo == 'envariance':
            cobj = self._create(circuit, quantum_r, classical_r, n_qubits)
        elif algo == 'parity':
            cobj = self._create(circuit, quantum_r, classical_r, n_qubits, x=False, oracle=oracle,
                                custom_mode=custom_mode)
        else:
            logger.critical('algorithm %s not recognized', algo)
            exit(6)
        logger.info('Created %s circuit for %s backend with %d qubit', algo, backend, n_qubits)
        QASM_source = cobj['circuit'].qasm()
        connected = self._sort_connected(cobj['connected'], algo=algo)
        cobj['connected'] = connected
        cobj['qasm'] = QASM_source
        if custom_mode is False:
            cobj['oracle'] = self.set_oracle(oracle, n_qubits)
        else:
            cobj['oracle'] = oracle
        if compiling is True:
            cobj['compiled'] = compile(cobj['circuit'], backend)
        else:
            cobj['compiled'] = compile(cobj['circuit'], backend, skip_transpiler=True)
        cobj['circuit'] = load_qasm_string(cobj['compiled']['circuits'][0]['compiled_circuit_qasm'])
        cobj['algo'] = algo
        logger.info('Compiled %s circuit for %s backend with %d qubit', algo, backend, n_qubits)
        logger.debug('cobj: %s', str(cobj))
        return cobj

    def run(self, cobj, backend=online_sim, shots=1024, max_credits=5):
        """Runs circuit on backend

        Parameters:
            cobj (dict): compiled object
            backend (str): backend on which circuit will run
            shots (int): number of shots
            max_credits (int): maximum credits to use

        Returns:
            robj (dict): ran object, dictionary containing results of ran circuit, for example:

                                robj = {
                                circuit: ran circuit as QuantumCircuit,
                                ran_qasm: ran circuit as Qasm,
                                n_qubits: number of qubits used in circuit,
                                connected: list of connected qubits, in th order they were connected,
                                oracle: specified oracle,
                                algo: specified algorithm,
                                backend: backend on which circuit was ran
                                result: result of running the circuit
                                counts: result counts, sorted in descending order}
        """
        while True:
            try:
                backend_status = get_backend(backend).status
                if ('available' in backend_status and backend_status['available'] is False) \
                        or ('busy' in backend_status and backend_status['busy'] is True):
                    while get_backend(backend).status['available'] is False:
                        sleep(300)
            except (ConnectionError, ValueError, KeyError):
                logger.error('Error getting backend status', exc_info=True)
                sleep(300)
                continue
            break

        api = IBMQuantumExperience(config.APItoken)

        min_credits = 0
        if shots > 1024:
            min_credits = 5
        else:
            min_credits = 3

        while api.get_my_credits()['remaining'] < min_credits:
            logger.warning('Less than 5 credits remaining, waiting for replenishment')
            sleep(900)
        try:
            base_backend = get_backend(backend)
            cobj['compiled']['config']['backend_name'] = base_backend.configuration['name']
            cobj['compiled']['config']['shots'] = shots
            job = base_backend.run(cobj['compiled'])
            logger.info('Circuit running on %s backend', backend)
            lapse = 0
            interval = 10
            while not job.done:
                logger.info('Status @ {} seconds: \n%s'.format(interval * lapse), job.status)
                if job.status['status'] == JobStatus.ERROR:
                    return self.run(cobj, backend, shots, max_credits)
                sleep(interval)
                lapse += 1
            logger.info('Status @ {} seconds: \n%s'.format(interval * lapse), job.status)
            if job.status['status'] == JobStatus.ERROR:
                return self.run(cobj, backend, shots, max_credits)
            result = job.result()
        except (QISKitError, IBMQJobError, TimeoutError, CancelledError):
            logger.error('Error getting results from backend', exc_info=True)
            sleep(900)
            return self.run(cobj, backend, shots, max_credits)

        try:
            counts = result.get_counts()
        except QISKitError:
            logger.error('Error reading results', exc_info=True)
            return self.run(cobj['circuit']['compiled'], backend, shots, max_credits)

        sorted_c = sorted(counts.items(), key=operator.itemgetter(1), reverse=True)
        robj = {
            'circuit': load_qasm_string(result.get_ran_qasm(result.get_names()[0])),
            'n_qubits': cobj['n_qubits'],
            'connected': cobj['connected'],
            'oracle': cobj['oracle'],
            'result': result,
            'counts': sorted_c,
            'ran_qasm': result.get_ran_qasm(result.get_names()[0]),
            'algo': cobj['algo'],
            'backend': backend
        }
        logger.info('Circuit successfully ran on %s backend', backend)
        logger.debug('robj: %s', str(robj))
        return robj
