import sys
import os
from genericpath import isfile
import numpy as np
import pandas as pd
import cantera as ct

# ---------------- NEW MODEL STRUCTURE ---------------- #
# REACTOR 0: Fuel inlet (fake reactor), T = T_fuel (300 K) fixed
# REACTOR 1: Air inlet (fake reactor), T = T_rich  (800 - 1000 K) 
# REACTOR 2: Ignition flame PSR, adiabatic reactor, small volume (~30cm3)
# REACTOR 3: Quenching reactor, non-adiabatic, U = 10-20 W/m2/K, small volume (in theory should not be reactive)
# REACTOR 4: First post-flame PFR (only rich mixture) it simulates the duct (tau ~ 0.02s)
# REACTOR 5: First lean combustion reactor (tau ~ 0.001 s), rich mixture reacts with a portion of the lean mixture
# REACTOR 6: Second lean combustion reactor (stagnation zone), rich mixture reacts with a portion of the lean mixture
# REACTOR 7: Third lean combustion reactor, now is isothermal (T = 1200 K) because of the heat loss in the quenching

# ---------------- USER DEFINED PARAMETERS ---------------- #
P = 96.0                # kW
y_nh3 = 1.0             # mole fraction
Tout  = 1225.0          # K
Power = 96.0            # kW
T_in_rich = 300.0       # K (fuel temperature)
phi_rich = [1.0, 1.15, 1.3, 1.45, 1.6]          # equivalence ratio
T_cstr_1 = [800, 900, 1000]         # K
data_sensor = pd.read_csv('smart_sensors.csv', sep = ';')
val_sensor  = np.array(data_sensor.values[:,4:]).astype(np.float32)
val_sensor[:-1,:] = val_sensor[:-1,:]*1e6

# ---------------- HELPER FUNCTIONS ---------------- #
# calculate fuel and air mass flowrates
def calc_inlet_mass(Power, y_nh3, phi):
    
    # This function calculates the mass flow rate of fuel
    # and total air (based on the global equivalence ratio)
    # given the power (kW), the NH3 mole fraction of the fuel and 
    # The global equivalence ratio.

    # Calculate the stoichiometric coefficients
    y_h2 = 1 - y_nh3
    y = y_h2*2 + y_nh3*3
    w = y_nh3
    x = 0.
    m = x + y/4                                 # O2/fuel molar basis
    f = 0.79/0.21                               # Ratio between N2 and O2 in air
    af_mol  = m + m*f                           # Air/fuel stoichiometric molar basis
    af_mass = af_mol*29/(y_h2*2 + y_nh3*17)     # Air/fuel stoichiometric mass basis
    air_ecc = 1/phi -1                          # Air excess
    af_eff  = af_mass*(1+air_ecc)               # Air/Fuel operative mass basis

    # Calculate the fuel flowrate
    nH2O_s = y/2;                               # Stoichiometric moles of H2O produced
    DH_r   = -241.86*nH2O_s + 46.01*y_nh3;      # DH of global reaction kJ/mol
    LHV = -1000*DH_r/(y_h2*2 + y_nh3*17);       # LHV kJ/kg
    m_fuel = Power/LHV;                         # Fuel flowrate kg/s

    # Calculate air flowrate
    m_air = m_fuel * af_eff                 # Air flowrate kg/s

    return m_fuel, m_air

# Calculate the mass flowrates of the network
def calc_mass_flowrates(Power, y_nh3, phi_rich, phi_global, stagn1=0.1, stagn2=0.15, entr=0.976):

    # This function calculates the mass flow rates across the reactors 
    # and stores them in a Matrix M[i,j] where M[i,j] is the mass flow rate
    # from reactor i to reactor j. Please note that this function defines
    # the internal structure of the reactor network. The user should modify
    # this function to change the reactor network model.
    # stagn1, stagn2 are the fractions of the bypass air that goes to the
    # 1st stagnation reactor and 2nd stagnation reactor respectively.
    # They can be specified by the user from the Dakota input file.

    # Global quantities
    m_fuel, m_air_tot = calc_inlet_mass(Power, y_nh3, phi_global)
    m_fuel, m_air_rich = calc_inlet_mass(Power, y_nh3, phi_rich)
    m_air_bypass = m_air_tot - m_air_rich

    # Initialize mass flowrates matrix
    M = np.zeros((8,8))

    # First combustion zone
    M[0,2] = m_fuel                 # To flame PSR
    M[1,2] = m_air_rich*entr        # To flame PSR (we consider the fraction of air that is entrained)

    # The quenching reactor is number 7
    M[2,3] = m_fuel + m_air_rich*entr       # From ignition to quenching PSR
    M[3,4] = m_fuel + m_air_rich*entr       # From quenching to FIRST POST-FLAME flame PFR
    M[4,5] = m_fuel + m_air_rich*entr       # From flame to first stagnation reactor

    # Stagnation zone
    stagn3 = 1 - stagn1 - stagn2
    M[1,5] = m_air_bypass*stagn1 + m_air_rich*(1.0-entr) # From inlet air to first stagnation reactor
    M[1,6] = m_air_bypass*stagn2                         # From inlet air to second stagnation reactor
    M[1,7] = m_air_bypass*stagn3                         # From inlet air to outlet reactor

    # Sequential mass flowrates
    M[5,6] = m_fuel + m_air_rich + m_air_bypass*stagn1
    M[6,7] = m_fuel + m_air_rich + m_air_bypass*stagn1 + m_air_bypass*stagn2

    return M

# ---------------- HELPER FUNCTIONS ---------------- #
# Calculate fuel and air mass flowrates given a certain power, equivalence ratio
# and NH3 mole fraction (a mixture of NH3 and H2 is assumed)
def calc_inlet_mass(Power, y_nh3, phi):
    
    # This function calculates the mass flow rate of fuel
    # and total air (based on the global equivalence ratio)
    # given the power (kW), the NH3 mole fraction of the fuel and 
    # The global equivalence ratio.

    # Calculate the stoichiometric coefficients
    y_h2 = 1 - y_nh3
    y = y_h2*2 + y_nh3*3
    w = y_nh3
    x = 0.
    m = x + y/4                                 # O2/fuel molar basis
    f = 0.79/0.21                               # Ratio between N2 and O2 in air
    af_mol  = m + m*f                           # Air/fuel stoichiometric molar basis
    af_mass = af_mol*29/(y_h2*2 + y_nh3*17)     # Air/fuel stoichiometric mass basis
    air_ecc = 1/phi -1                          # Air excess
    af_eff  = af_mass*(1+air_ecc)               # Air/Fuel operative mass basis

    # Calculate the fuel flowrate
    nH2O_s = y/2;                               # Stoichiometric moles of H2O produced
    DH_r   = -241.86*nH2O_s + 46.01*y_nh3;      # DH of global reaction kJ/mol
    LHV = -1000*DH_r/(y_h2*2 + y_nh3*17);       # LHV kJ/kg
    m_fuel = Power/LHV;                         # Fuel flowrate kg/s

    # Calculate air flowrate
    m_air = m_fuel * af_eff                 # Air flowrate kg/s

    return m_fuel, m_air

def CalcLHV(y_nh3):

    # This function calculates the LHV of the fuel given the NH3 mole fraction

    # Calculate the stoichiometric coefficients
    y_h2 = 1 - y_nh3
    y = y_h2*2 + y_nh3*3
    w = y_nh3
    x = 0.
    m = x + y/4                                 # O2/fuel molar basis

    # Calculate the fuel flowrate
    nH2O_s = y/2;                               # Stoichiometric moles of H2O produced
    DH_r   = -241.86*nH2O_s + 46.01*y_nh3;      # DH of global reaction kJ/mol
    LHV = -1000*DH_r/(y_h2*2 + y_nh3*17);       # LHV kJ/kg

    return LHV

# CALCULATE THE OUTLET TEMPERATURE OF THE NETWORK
def calc_outlet_temp(Power, y_nh3, phi_rich, phi_lean, T_in_rich, T_in_lean, T_amb=300.0, U=0.0, A=1.0):

    # This function calculates the outlet temperature of the network given:
    # Power: Power of the network (kW)
    # y_nh3: Mole fraction of NH3 in the fuel
    # phi_rich: Equivalence ratio of the rich combustion
    # phi_lean: Equivalence ratio of the lean combustion
    # T_in_rich: Inlet temperature of the rich combustion (K)
    # T_in_lean: Inlet temperature of the lean combustion (K)
    # T_amb: Ambient temperature (K)
    # U: Heat transfer coefficient (W/m2K)
    # A: Area of the reactor (m2)

    # Calculate the mass flowrate of the fuel and air
    m_fuel, m_air_lean = calc_inlet_mass(Power, y_nh3, phi_lean)
    m_fuel, m_air_rich = calc_inlet_mass(Power, y_nh3, phi_rich)

    # Global mass of air
    m_air = m_air_rich + m_air_lean

    # Calculate the fraction of power reacted in the rich combustion
    y_h2 = 1 - y_nh3
    y = y_h2*2 + y_nh3*3
    w = y_nh3
    x = 0.
    m = x + y/4                                 # O2/fuel molar basis
    f = 0.79/0.21                               # Ratio between N2 and O2 in air
    af_mol  = m + m*f                           # Air/fuel stoichiometric molar basis
    af_mass = af_mol*29/(y_h2*2 + y_nh3*17)     # Air/fuel stoichiometric mass basis

    # In the rich zone, there is less air than the stoichiometric value. Therefore,
    # the fraction of fuel reacted is equal to the ratio between the mass of air
    # and the stoichiometric mass of air
    f_rich = m_air_rich/af_mass

    # The power reacted in the rich zone is equal to:
    Power_rich = f_rich*Power # kW

    # Create Cantera objects so that the calculation is more accurate
    fuel = ct.Solution('/Users/imacremote/Distributions/NetSMOKE_Dakota_Interface/MacOS/Stagni_NH3/chem.cti')
    fuel_comp = 'H2:' + str(y_h2) + ', NH3:' + str(y_nh3)
    fuel.TPX = 340.0, 101325.0, fuel_comp

    # Create air
    air = ct.Solution('/Users/imacremote/Distributions/NetSMOKE_Dakota_Interface/MacOS/Stagni_NH3/chem.cti')
    air.TPX = T_in_rich, 101325.0, 'O2:0.21, N2:0.79'

    # Use quantity objects so that you can mix the fuel and air
    qfuel = ct.Quantity(fuel, mass=m_fuel)
    qair_rich  = ct.Quantity(air, mass=m_air_rich)

    # Combustion products
    prod_rich = qfuel + qair_rich

    # Calculate the chemical equilibrium
    prod_rich.equilibrate('HP')
    T_out_rich = prod_rich.T

    # Now mix the remaining air with the products of the rich combustion
    qair_lean  = ct.Quantity(air, mass=m_air_lean)

    # Second stage
    prod_lean = prod_rich + qair_lean
    prod_lean.equilibrate('HP')

    # Calculate the outlet temperature of the lean combustion
    T_out_lean = prod_lean.T

    return T_out_rich, T_out_lean, prod_rich, prod_lean

# This function directly calculates the phi_lean as a function of the outlet temperature T
def CalcPhiLean(Tout, *parameters):

    T, Power, y_nh3, phi_rich, T_in_rich, T_in_lean = parameters

    # Calculate the mass flowrate of the fuel and air
    m_fuel, m_air_rich = calc_inlet_mass(Power, y_nh3, phi_rich)

    # Use cantera to find equilibrium mixture of rich stage
    fuel = ct.Solution('/Users/imacremote/Distributions/NetSMOKE_Dakota_Interface/MacOS/Stagni_NH3/chem.cti')
    fuel_comp = 'NH3:1'
    fuel.TPX = 300.0, 101325.0*5, fuel_comp

    # Create air
    air = ct.Solution('/Users/imacremote/Distributions/NetSMOKE_Dakota_Interface/MacOS/Stagni_NH3/chem.cti')
    air.TPX = T_in_rich, 101325.0*5, 'O2:0.21, N2:0.79'

    # Use quantity objects so that you can mix the fuel and air
    qfuel = ct.Quantity(fuel, mass=m_fuel)
    qair_rich  = ct.Quantity(air, mass=m_air_rich)

    # Combustion products
    prod_rich = qfuel + qair_rich

    # Calculate the chemical equilibrium
    prod_rich.equilibrate('HP')

    # Do a manual thermal balance to find the mass of air in the lean zone
    # Calculate the mass of fuel from prod_rich
    y_nh3_rich = prod_rich.Y[fuel.species_index('NH3')]
    y_h2_rich = prod_rich.Y[fuel.species_index('H2')]
    m_fuel_lean = prod_rich.mass * (y_h2_rich + y_nh3_rich)
    
    # Calculate the power left
    LHV_NH3 =    CalcLHV(y_nh3) * 1000                       # J/kg
    LHV_H2  =    CalcLHV(1 - y_nh3) * 1000                   # J/kg
    LHV = (y_h2_rich * LHV_H2 + y_nh3_rich * LHV_NH3)/(y_h2_rich + y_nh3_rich)        # J/kg
    Power_lean = m_fuel_lean * LHV                          # W

    # Create a new quantity object for the lean zone
    m_air_lean = (Power_lean - prod_rich.mass * qair_rich.cp_mass * (Tout - prod_rich.T))/(qair_rich.cp_mass*(Tout - T_in_lean))

    # Now get the equivalence ratio of the lean zone
    # Calculate the fraction of power reacted in the rich combustion
    y_h2 = 1 - y_nh3
    y = y_h2*2 + y_nh3*3
    w = y_nh3
    x = 0.
    m = x + y/4                                 # O2/fuel molar basis
    f = 0.79/0.21                               # Ratio between N2 and O2 in air
    af_mol  = m + m*f                           # Air/fuel stoichiometric molar basis
    af_mass = af_mol*29/(y_h2*2 + y_nh3*17)     # Air/fuel stoichiometric mass basis

    excess_lean = m_air_lean/(af_mass*m_fuel) # Equivalence ratio of the lean zone
    excess_global = (m_air_lean + m_air_rich)/(af_mass*m_fuel)

    phi_lean = 1/(1+excess_lean)
    phi_global = 1/(1+excess_global)
     
    return phi_lean, phi_global, m_air_rich, m_air_lean

def CalcAirMassNew(Tout, Tair):

    # Properties of the fuel
    y_nh3 = 1.0
    LHV = CalcLHV(y_nh3)

    # Specific heat of the burned mixture
    cp = 1.173 # kJ/kg K

    # Calculate the mass of fuel and the mass of rich air
    Power = 96.0
    phi_rich = 1.0
    m_fuel, m_air_rich = calc_inlet_mass(Power, y_nh3, phi_rich)

    # Define the residual function
    def res(m_air):

        Tmix = (m_fuel * 300 + m_air * Tair)/(m_fuel + m_air)
        mcalc = Power/(cp*(Tout - Tmix))

        return mcalc - m_air

    # Calculate the total mass 
    m_start = Power/(cp*(Tout - Tair))

    # Solve the equation
    from scipy.optimize import fsolve
    m_air_tot = fsolve(res, m_start)[0]

    return m_air_tot, m_air_rich

# Calculate the mass flowrates of the network
def calc_mass_flowrates_new(Power, y_nh3, phi_rich, Tout, Tair, stagn1=0.1, stagn2=0.15, entr=0.976,
                            ff8=0.02, fa8=0.08, kv=0.085):

    # This function calculates the mass flow rates across the reactors 
    # and stores them in a Matrix M[i,j] where M[i,j] is the mass flow rate
    # from reactor i to reactor j. Please note that this function defines
    # the internal structure of the reactor network. The user should modify
    # this function to change the reactor network model.
    # stagn1, stagn2 are the fractions of the bypass air that goes to the
    # 1st stagnation reactor and 2nd stagnation reactor respectively.
    # They can be specified by the user from the Dakota input file.

    # Calculate total mass of air
    m_air_tot, m_air_rich = CalcAirMassNew(Tout, Tair)

    # Global quantities
    m_fuel, m_air_rich = calc_inlet_mass(Power, y_nh3, phi_rich)
    m_air_bypass = m_air_tot - m_air_rich

    # New lean comnbustion zone
    mf8 = m_fuel * ff8
    ma8 = m_air_rich * fa8

    # Initialize mass flowrates matrix
    M = np.zeros((9,9))

    # First combustion zone
    M[0,2] = m_fuel - mf8               # To flame PSR
    M[1,2] = m_air_rich*entr - ma8      # To flame PSR (we consider the fraction of air that is entrained)

    # New lean combustion zone
    M[0,8] = mf8
    M[1,8] = ma8
    # Recirculation from main flame zone
    M[8,2] = mf8 + ma8 + (m_fuel + m_air_rich)*kv
    M[2,8] = (m_fuel + m_air_rich)*kv

    # The quenching reactor is number 7
    M[2,3] = m_fuel + m_air_rich*entr       # From ignition to quenching PSR
    M[3,4] = m_fuel + m_air_rich*entr       # From quenching to FIRST POST-FLAME flame PFR
    M[4,5] = m_fuel + m_air_rich*entr       # From flame to first stagnation reactor

    # Stagnation zone
    stagn3 = 1 - stagn1 - stagn2
    M[1,5] = m_air_bypass*stagn1 + m_air_rich*(1.0-entr) # From inlet air to first stagnation reactor
    M[1,6] = m_air_bypass*stagn2                         # From inlet air to second stagnation reactor
    M[1,7] = m_air_bypass*stagn3                         # From inlet air to outlet reactor

    # Sequential mass flowrates
    M[5,6] = m_fuel + m_air_rich + m_air_bypass*stagn1
    M[6,7] = m_fuel + m_air_rich + m_air_bypass*stagn1 + m_air_bypass*stagn2

    return M

# ---------------- SUBSTITUTING PARAMETERS INTO REACTORS ---------------- #
# Check if phi_rich is in the input name list
# Phi lean should be calculated given the outlet temperature of the flame
# print(names)
output_values_global = []
output_names_global = []
intcounter = 0
for T in T_cstr_1:
    for phi in phi_rich:

        os.system("rm input.*")
        os.system("cp -a ../CRN_Model_3/* ./")

        # Get the name of the file which is passed as an argument
        filename = sys.argv[1]

        # Read the input file
        with open(filename, 'r') as f:
            params = f.readlines()

        # Get the number of parameters
        n_params = int(params[0].split()[0])

        # Extract their names and values and put them in two separate lists
        names = []
        values = []
        counter = 1
        while counter < n_params+1:
            names.append(params[counter].split()[1])
            values.append(params[counter].split()[0])
            counter += 1

        # Extract the name of the outputs
        n_output = int(params[counter].split()[0])
        print('File has', n_output, 'outputs')

        if 'phi_rich' in names and 'T_cstr_1' in names:
            phi_rich = float(values[names.index('phi_rich')])
            T_cstr_1 = float(values[names.index('T_cstr_1')])
        elif 'phi_rich' in names and 'T_cstr_1' not in names:
            phi_rich = float(values[names.index('phi_rich')])
            names.append('T_cstr_1')
            values.append(T_cstr_1)
        elif 'phi_rich' not in names and 'T_cstr_1' in names:
            T_cstr_1 = float(values[names.index('T_cstr_1')])
            names.append('phi_rich')
            values.append(phi_rich)
        else:
            names.append('phi_rich')
            values.append(str(phi))
            names.append('T_cstr_1')
            values.append(str(T))
            print(phi)

        # Append T_cstr_3 as well
        if 'T_cstr_3' not in names:
            T_cstr_3 = T            # Set temperature of the sourrounding quenching reactor
            names.append('T_cstr_3')
            values.append(str(T_cstr_3))

        # Fraction of air to the different reactors
        # The names are from the table in the paper
        if 'Fa3' and 'Fa4' in names:
            stagn1 = float(values[names.index('Fa3')])
            stagn2 = float(values[names.index('Fa4')])
        elif 'Fa3' in names and 'Fa4' not in names:
            stagn1 = float(values[names.index('Fa3')])
            stagn2 = 0.1500
        elif 'Fa3' not in names and 'Fa4' in names:
            stagn2 = float(values[names.index('Fa4')])
            stagn1 = 0.0873
        else:
            stagn1 = 0.0873
            stagn2 = 0.1500

        # Check for entrainment fraction
        if 'Fa1' in names:
            entr = float(values[names.index('Fa1')])
        else:
            entr = 0.9600

        ## New parameters for R8 (new lean reactor)
        # Fraction of fuel to new reactor
        if 'Ff8' in names:
            ff8 = float(values[names.index('Ff8')])
        else:
            ff8 = 0.02
        # Fraction of air to new reactor
        if 'Fa8' in names:
            fa8 = float(values[names.index('Fa8')])
        else:
            fa8 = 0.085
        # Recirculation ratio
        if 'Kv' in names:
            kv = float(values[names.index('Kv')])
        else:
            kv = 0.085

        # Calculate phi lean
        T_in_lean = T    # K
        T_in_rich = T_in_lean
        # parameters = (Tout, Power, y_nh3, phi, T_in_rich, T_in_lean)
        # phi_lean, phi_global, m_air_rich, m_air_lean = CalcPhiLean(Tout, *parameters)

        # Get mass flowrates
        M = calc_mass_flowrates_new(P, y_nh3, phi, Tout, T, stagn1, stagn2, entr, ff8, fa8, kv)

        # Get the number of reactors and the list of files to open to replace strings
        print('Checking which files to open...\n')
        nr = 0
        fname_list = []
        for i in range(1000):
            if isfile('input.cstr.'+str(i)+'.dic'):
                fname_list.append('input.cstr.' + str(i) + '.dic')
                nr += 1
            elif isfile('input.pfr.'+str(i)+'.dic'):
                fname_list.append('input.pfr.' + str(i) + '.dic')
                nr += 1
            else:
                print('Found', nr, 'reactors')
                break

        # Check if main input is present
        if not isfile('input.dic'):
            print('Error: input.dic not found')
            sys.exit(1)

        # Open and modify each file
        for fname in fname_list:
            newlines = []    # New lines to write in the modified input
            counter = 0      # Counter to keep track of the line number
            with open(fname, 'r') as fid:
                lines = fid.readlines()
                for item in lines:
                    line = item.split()
                    # For each of the names check if it is in line
                    for name in names:
                        if name in line:
                            # If it is, replace the name with the value
                            index = line.index(name)
                            line[index] = values[names.index(name)]
                    
                    for subitem in line:
                        if subitem =='M0':
                            line[line.index(subitem)] = str(np.sum(M[0,:]))     # Inlets reactors indeces should be inverted
                        elif subitem =='M1':
                            line[line.index(subitem)] = str(np.sum(M[1,:]))     # Inlets reactors indeces should be inverted
                        elif subitem =='M2':
                            line[line.index(subitem)] = str(np.sum(M[:,2]))
                        elif subitem =='M3':
                            line[line.index(subitem)] = str(np.sum(M[:,3]))
                        elif subitem =='M4':
                            line[line.index(subitem)] = str(np.sum(M[:,4]))
                        elif subitem =='M5':
                            line[line.index(subitem)] = str(np.sum(M[:,5]))
                        elif subitem =='M6':
                            line[line.index(subitem)] = str(np.sum(M[:,6]))
                        elif subitem =='M7':
                            line[line.index(subitem)] = str(np.sum(M[:,7]))
                        elif subitem == 'M8':
                            line[line.index(subitem)] = str(np.sum(M[:,8]))
                
                    newlines.append(line)
                    counter += 1

            # Write modified lines to file
            with open(fname, 'w') as f:
                for item in newlines:
                    for ss in item:
                        if ss == item[-1]:
                            f.write(ss + '\n')
                        else:
                            f.write(ss + ' ')

        print('New inputs are ready')
        print('Now modifying the internal connections of the network...')

        # ---------------- WRITING THE MAIN INPUT.DIC ---------------- #

        # Modify input dictionary
        # Modify the mass flowrates
        with open('input.dic', 'r') as fid:
            lines = fid.readlines()
            newlines = []
            for item in lines:
                line = item.split()
                try:
                    r1 = int(line[0])
                    r2 = int(line[1])
                    line[2] = str(M[r1,r2])
                except:
                    pass

                for subitem in line:
                        if subitem =='M0':
                            line[line.index(subitem)] = str(np.sum(M[0,:]))
                        elif subitem =='M1':
                            line[line.index(subitem)] = str(np.sum(M[1,:]))
                        elif subitem =='M2':
                            line[line.index(subitem)] = str(np.sum(M[:,2]))
                        elif subitem =='M3':
                            line[line.index(subitem)] = str(np.sum(M[:,3]))
                        elif subitem =='M4':
                            line[line.index(subitem)] = str(np.sum(M[:,4]))
                        elif subitem =='M5':
                            line[line.index(subitem)] = str(np.sum(M[:,5]))
                        elif subitem =='M6':
                            line[line.index(subitem)] = str(np.sum(M[:,6]))
                        elif subitem =='M7':
                            line[line.index(subitem)] = str(np.sum(M[:,7]))
                        elif subitem =='M8':
                            line[line.index(subitem)] = str(np.sum(M[:,8]))
                    
                newlines.append(line)

        with open('input.dic', 'w') as f:
            for item in newlines:
                for ss in item:
                    if ss == item[-1]:
                        f.write(ss + '\n')
                    else:
                        f.write(ss + ' ')

        print('Main input file is ready')

        # ---------------- RUNNING THE SIMULATION ---------------- #
        os.system('sh Run2.sh')

        # ---------------- WRITING OUTPUTS ---------------- #
        print('Reading outputs...')
        # Calibration on the smart sensors
        outname = 'Output/Reactor.8/Output.out'
        dt = pd.read_csv(outname, sep = '\s+'); feature_name = 'NO2_w(61)'
        output_values_global.append(dt[feature_name].values[-1]*1e6)
        output_names_global.append('Sensor0_Case' + str(intcounter)); intcounter+=1

        outname = 'Output/Reactor.2/Output.out'
        dt = pd.read_csv(outname, sep = '\s+'); feature_name = 'OH_w(48)'
        output_values_global.append(dt[feature_name].values[-1]*1e6)
        output_names_global.append('Sensor1_Case' + str(intcounter)); intcounter+=1

        outname = 'Output/Reactor.6/Output.out'
        dt = pd.read_csv(outname, sep = '\s+'); feature_name = 'NO2_w(61)'
        output_values_global.append(dt[feature_name].values[-1]*1e6)
        output_names_global.append('Sensor2_Case' + str(intcounter)); intcounter+=1

        outname = 'Output/Reactor.2/Output.out'
        dt = pd.read_csv(outname, sep = '\s+'); feature_name = 'OH_w(48)'
        output_values_global.append(dt[feature_name].values[-1]*1e6)
        output_names_global.append('Sensor3_Case' + str(intcounter)); intcounter+=1

        outname = 'Output/Reactor.3/Output.out'
        dt = pd.read_csv(outname, sep = '\s+'); feature_name = 'NH2_w(52)'
        output_values_global.append(dt[feature_name].values[-1]*1e6)
        output_names_global.append('Sensor4_Case' + str(intcounter)); intcounter+=1

        outname = 'Output/Reactor.5/Output.out'
        dt = pd.read_csv(outname, sep = '\s+'); feature_name = 'NO_w(42)'
        output_values_global.append(dt[feature_name].values[-1]*1e6)
        output_names_global.append('Sensor5_Case' + str(intcounter)); intcounter+=1

        outname = 'Output/Reactor.1/Output.out'
        dt = pd.read_csv(outname, sep = '\s+'); feature_name = 'T[K](5)'
        output_values_global.append(dt[feature_name].values[-1])
        output_names_global.append('Sensor6_Case' + str(intcounter)); intcounter+=1

print('All the CRN values:')
print(output_values_global)
print('All the CFD values:')
print(val_sensor.reshape(-1,1)*1e6)
SSE = np.sum((np.array(output_values_global).reshape(-1,1) - val_sensor.T.reshape(-1,1)*1e6)**2)

# Write outputs to file
output_dakota = sys.argv[2]
with open(output_dakota, 'w') as f:
    f.write(str(SSE))


