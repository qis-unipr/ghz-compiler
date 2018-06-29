class Compiler(object):
    def __init__(self):
        self.__coupling_map = dict()
        self.__inverse_coupling_map = dict()
        self.__path = dict()
        self.__n_qubits = 0
        self.__ranks = dict()
        self.__connected = dict()
        self.__most_connected = []
