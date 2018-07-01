from compiler.compiler import Compiler
from compiler.backends import *
from compiler.utility import circuit_drawer, order_results, save_results

compiler = Compiler(get_coupling(qx5))
# Oracle can be specified by alias:
#               '00' equals a '00..0000' oracle
#               '10' equals a '10..1010' oracle
#               '11' equals a '11..1111' oracle
#
# Remember that if the backend has 16 qubit, parity will run on 15 qubits because one is used as ancilla
cobj = compiler.compile(15, qx5, algo='parity', oracle='10')
# To draw circuit without running it, uncomment next line and comment the other two
# circuit_drawer(cobj['circuit'], filename='parity')
robj = compiler.run(cobj, backend=qx5)
circuit_drawer(robj['ran_qasm'], filename='parity_10')
results = order_results(robj)
save_results(robj, 'parity_10.txt', directory='Data/parity_10/')

# Oracle can also be explicitly set if custom_mode is True
cobj = compiler.compile(15, qx5, algo='parity', oracle='101101011010011', custom_mode=True)
circuit_drawer(cobj['qasm'], filename='parity_10')
