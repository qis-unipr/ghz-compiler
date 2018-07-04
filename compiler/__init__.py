from qiskit import register
from compiler import config

# set the APIToken and API url
register(config.APItoken, config.URL)
