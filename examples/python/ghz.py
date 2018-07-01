from compiler.compiler import Compiler
from compiler.backends import *
from compiler.utility import circuit_drawer, order_results, save_results

compiler = Compiler(get_coupling(qx5))
# It's possible to compile and run on a simulator instead of a real backend, if you want
cobj = compiler.compile(16, qx5)
# To draw circuit without running it, uncomment next line and comment the other two
# circuit_drawer(cobj['circuit'], filename='ghz')
robj = compiler.run(cobj, backend=qx5)
circuit_drawer(robj['ran_qasm'], filename='ghz')
results = order_results(robj)
save_results(robj, 'ghz.txt', directory='Data/ghz')
