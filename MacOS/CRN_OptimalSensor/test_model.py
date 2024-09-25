import numpy as np
from write_reactor_input import Reactor, WriteInput

R = Reactor(rtype='cstr', num=0)
R.V = 100
R.Tau = 1
R.P = 101325
R.T = 300
R.Isothermal = True
R.InitialStatus = True
if hasattr(R,'V'):
    print('SI')
R.MassFractions = ['NH3:0', 'H2:1']
R.WriteInputCSTR(path_to_file='./')
R.D = 100
R.L = 100
R.WriteInputPFR(path_to_file='./')

R2 = Reactor(rtype='cstr', num=1)
R2.V = 100
R2.Tau = 1
R2.P = 101325
R2.T = 300
R2.Isothermal = True
R2.MassFractions = ['NH3:0', 'H2:1']
R2.WriteInputCSTR(path_to_file='ProvaNet')

R3 = Reactor(rtype='pfr', num=2)
R3.V = 100
R3.L = 100
R3.Tau = 1
R3.P = 101325
R3.T = 300
R3.MassFractions = ['O2:0.21', 'N2:0.79']

Rlist = [R, R2, R3]
print(Rlist[0].rtype)
M = np.array([[0, 1, 1], [1, 0, 1], [1, 1, 0]])
Mb = np.array([[0, 0], [1, 1], [0, 0]])
chemfile = '/Users/matteosavarese/Desktop/Dottorato/Github/Dakota_Interface/MacOS/Otomo/otomo.inp'
thermofile = '/Users/matteosavarese/Desktop/Dottorato/Github/Dakota_Interface/MacOS/Otomo/otomo_therm.dat'
path_to_inputs = '/Users/matteosavarese/Desktop/Dottorato/Github/Dakota_Interface/MacOS/ProvaNet'

WriteInput(Rlist, path_to_inputs, M, Mb, chemfile, thermofile)





