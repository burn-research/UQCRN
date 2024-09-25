import numpy as np
import os

class Reactor:

    def __init__(self, rtype, num):

        if rtype == 'cstr' or rtype == 'psr':
            self.rtype = rtype
            self.num = num
        
        self.rtype = rtype
        self.num = num

    def WriteInputCSTR(self, path_to_file):

        # Filename
        fname = path_to_file + '/input.cstr.' + str(self.num) + '.dic'
        # Open the file
        with open(fname, 'w') as f:
            f.write("Dictionary PerfectlyStirredReactor \n")
            f.write("{ \n")
            f.write("      @KineticsFolder     dummy; \n")
            f.write('      @InletStatus        Inlet-Mixture; \n')
            # Check for optional attributes
            if hasattr(self, 'InitialStatus'):
                f.write('      @InitialStatus     Initial-Status; \n')
            if hasattr(self, 'Sensitivity'):
                f.write('        @SensitivityAnalysis      sensitivity; \n')
            if hasattr(self, 'ROPA'):
                f.write('        @OnTheFlyROPA              ropa; \n')
            if hasattr(self, 'KineticCorrections'):
                f.write('      @KineticCorrections     kinetic-corrections; \n')

            # Check if it is isothermal
            if hasattr(self, 'Isothermal'):
                if self.Isothermal == True:
                    f.write('      @Type               Isothermal-ConstantPressure; \n')
                else:
                    f.write('      @Type               NonIsothermal-ConstantPressure; \n')
                    # Check for non-isothermal parameters
                    if hasattr(self, 'U'):
                        f.write('      @GlobalThermalExchangeCoefficient   {} W/m2/K; \n'.format(self.U))
                    if hasattr(self, 'A'):
                        f.write('      @ExchangeArea               {} m2; \n'.format(self.A))
                    if hasattr(self, 'Tenv'):
                        f.write('      @EnvironmentTemperature     {} K;  \n'.format(self.Tenv))
            
            # Check for mandatory inputs
            fcount=0
            if hasattr(self, 'V'):
                f.write('      @Volume          {}    cm3; \n'.format(self.V)); fcount=fcount+1
            if hasattr(self, 'Mf'):
                f.write('      @MassFlowRate    {}  kg/s;   \n'.format(self.Mf)); fcount=fcount+1
            if hasattr(self, 'Tau'):
                f.write('      @ResidenceTime    {}   s;   \n'.format(self.Tau)); fcount=fcount+1
            # Check constraints
            if fcount <= 1:
                raise ValueError('Specify at least two between mass flowrate, volume and tau...')
            elif fcount == 3:
                raise Warning('Reactor is overspecified, remove one between mass flowrate, tau and volume...')

            # Close first dictionary
            f.write('} \n')

            ### Inlet mixture (mandatory)
            f.write('\n Dictionary Inlet-Mixture \n { \n')
            # Pressure
            if hasattr(self, 'P') == False:
                raise ValueError('Pressure not specified. Specify R.P')
            else:
                f.write('      @Pressure           {} Pa; \n'.format(self.P))
            # Inlet temperature
            if hasattr(self, 'T') == False:
                raise ValueError('Inlet temperature not specified. Specify R.T')
            else:
                f.write('      @Temperature          {} K; \n'.format(self.T))
            # Composition
            if hasattr(self, 'MassFractions'):
                if isinstance(self.MassFractions, list) == False:
                    raise ValueError('Mass fractions should be a list!')
                nm = len(self.MassFractions)
                f.write('      @Masses       ')
                for i in range(nm):
                    ss = self.MassFractions[i].split(':')
                    if i < nm-1:
                        f.write('         {} {} \n'.format(ss[0], ss[1]))
                    else:
                        f.write('         {} {}; \n'.format(ss[0], ss[1]))
            elif hasattr(self, 'MoleFractions'):
                if isinstance(self.MoleFractions, list) == False:
                    raise ValueError('Mole fractions should be a list!')
                nm = len(self.MoleFractions)
                f.write('      @Moles       ')
                for i in range(nm):
                    ss = self.MoleFractions[i].split(':')
                    if i < nm-1:
                        f.write('         {} {} \n'.format(ss[0], ss[1]))
                    else:
                        f.write('         {} {}; \n'.format(ss[0], ss[1]))
            else:
                raise ValueError('Specify mass fractions or mole fractions as a list!')

            f.write('} \n')
            f.close()
        
        return self

    def WriteInputPFR(self, path_to_file):

        # Filename
        fname = path_to_file + '/input.pfr.' + str(self.num) + '.dic'
        # Open the file
        with open(fname, 'w') as f:
            f.write("Dictionary PlugFlowReactor \n")
            f.write("{ \n")
            f.write("      @KineticsFolder     dummy; \n")
            f.write('      @InletStatus        Inlet-Mixture; \n')
            # Check for optional attributes
            if hasattr(self, 'InitialStatus'):
                f.write('      @InitialStatus     Initial-Status; \n')
            if hasattr(self, 'Sensitivity'):
                f.write('        @SensitivityAnalysis      sensitivity; \n')
            if hasattr(self, 'ROPA'):
                f.write('        @OnTheFlyROPA              ropa; \n')
            if hasattr(self, 'KineticCorrections'):
                f.write('      @KineticCorrections     kinetic-corrections; \n')

            # Check if it is isothermal
            if hasattr(self, 'Isothermal'):
                if self.Isothermal == True:
                    f.write('      @Type               Isothermal; \n')
                    f.write('      @ConstantPressure   true;          \n')
                else:
                    f.write('      @Type               NonIsothermal; \n')
                    f.write('      @ConstantPressure   true;          \n')
                    # Check for non-isothermal parameters
                    if hasattr(self, 'U'):
                        f.write('      @GlobalThermalExchangeCoefficient   {} W/m2/K; \n'.format(self.U))
                    if hasattr(self, 'Cs'):
                        f.write('      @CrossSectionOverPerimeter               {} mm; \n'.format(self.Cs))
                    if hasattr(self, 'Tenv'):
                        f.write('      @EnvironmentTemperature     {} K;  \n'.format(self.Tenv))
            
            # Check for mandatory inputs
            if hasattr(self, 'V'):
                f.write('      @Volume          {}    cm3; \n'.format(self.V)) 
            if hasattr(self, 'Mf'):
                f.write('      @MassFlowRate    {}  kg/s;   \n'.format(self.Mf))
            if hasattr(self, 'Tau'):
                f.write('      @ResidenceTime    {}   s;   \n'.format(self.Tau))
            if hasattr(self, 'L'):
                f.write('      @Length             {} mm;         \n'.format(self.L))
            if hasattr(self, 'D'):
                f.write('      @Diameter             {} mm;         \n'.format(self.D))

            # Close first dictionary
            f.write('} \n')

            ### Inlet mixture (mandatory)
            f.write('\n Dictionary Inlet-Mixture \n { \n')
            # Pressure
            if hasattr(self, 'P') == False:
                raise ValueError('Pressure not specified. Specify R.P')
            else:
                f.write('      @Pressure           {} Pa; \n'.format(self.P))
            # Inlet temperature
            if hasattr(self, 'T') == False:
                raise ValueError('Inlet temperature not specified. Specify R.T')
            else:
                f.write('      @Temperature          {} K; \n'.format(self.T))
            # Composition
            if hasattr(self, 'MassFractions'):
                if isinstance(self.MassFractions, list) == False:
                    raise ValueError('Mass fractions should be a list!')
                nm = len(self.MassFractions)
                f.write('      @Masses       ')
                for i in range(nm):
                    ss = self.MassFractions[i].split(':')
                    if i < nm-1:
                        f.write('         {} {} \n'.format(ss[0], ss[1]))
                    else:
                        f.write('         {} {}; \n'.format(ss[0], ss[1]))
            elif hasattr(self, 'MoleFractions'):
                if isinstance(self.MoleFractions, list) == False:
                    raise ValueError('Mole fractions should be a list!')
                nm = len(self.MoleFractions)
                f.write('      @Moles       ')
                for i in range(nm):
                    ss = self.MoleFractions[i].split(':')
                    if i < nm-1:
                        f.write('         {} {} \n'.format(ss[0], ss[1]))
                    else:
                        f.write('         {} {}; \n'.format(ss[0], ss[1]))
            else:
                raise ValueError('Specify mass fractions or mole fractions as a list!')
            f.write('} \n')

            f.close()
        
        return self


def WriteInput(Rlist, path_to_file, M, Mb, chemfile, thermofile):

    # Check shapes
    nr = len(Rlist)
    if nr != np.shape(M)[0] or nr != np.shape(M)[1]:
        raise ValueError('Length of reactor list do not mactch mass flowrate matrix dimension')
    if nr != np.shape(Mb)[0]:
        raise ValueError('Length of reactor list do not mactch mass flowrate boundaries matrix dimension')
    if np.shape(Mb)[1] != 2:
        raise ValueError('Mb matrix should have two columns. First for inlets, second for outlets')
    
    # Calculate mass flowrates that enter in each reactors
    mass_in = np.zeros((nr,1))
    for j in range(nr):
        mass_in[j] = sum(M[:,j]) + Mb[j,0]

    # Write input files for each reactor
    cstr_count = 0; cstr_list = []
    pfr_count  = 0; pfr_list  = []
    for j in range(nr):
        if Rlist[j].rtype == 'cstr':
            Rlist[j].WriteInputCSTR(path_to_file=path_to_file)
            cstr_list.append(Rlist[j])
            cstr_count += 1
        elif Rlist[j].rtype == 'pfr':
            Rlist[j].WriteInputPFR(path_to_file=path_to_file)
            pfr_list.append(Rlist[j])
            pfr_count += 1

    # filename
    fname = path_to_file + '/input.dic'

    with open(fname, 'w') as f:
        f.write('Dictionary ReactorNetwork \n { \n')
        f.write('@KineticsPreProcessor      kinetic-mechanism; \n')
        f.write('@MinIterations            5;   \n')
        f.write('@MaxIterations            500;  \n')
        f.write('@AtomicErrorThreshold     1e-3;\n')
        f.write('@NonIsothermalErrorThreshold	1e-3; \n')
        f.write('@MaxUnbalance     0.01; \n')
        # Write the pfrs
        if pfr_count !=0:
            f.write('@PlugFlowReactors     \n')
            for j in range(pfr_count):
                if j < pfr_count-1:
                    ss = 'input.pfr.' + str(pfr_list[j].num) + '.dic \n'
                    f.write(ss)
                else:
                    ss = 'input.pfr.' + str(pfr_list[j].num) + '.dic; \n'
                    f.write(ss)
        # Write cstr
        if cstr_count !=0:
            f.write('@PerfectlyStirredReactors     \n')
            for j in range(cstr_count):
                if j < cstr_count-1:
                    ss = 'input.cstr.' + str(cstr_list[j].num) + '.dic \n'
                    f.write(ss)
                else:
                    ss = 'input.cstr.' + str(cstr_list[j].num) + '.dic; \n'
                    f.write(ss)

        # Write internal connections
        n_conn = np.count_nonzero(M)
        count_conn = 1
        f.write('@InternalConnections   ')
        for i in range(nr):
            for j in range(nr):
                if count_conn != n_conn:
                    f.write('                  {}   {}   {} \n'.format(i, j, M[i,j]))
                    count_conn = count_conn + 1
                else:
                    f.write('                  {}   {}   {}; \n'.format(i, j, M[i,j]))
        
        # Write input streams
        n_in = np.count_nonzero(Mb[:,0])
        in_count = 1
        f.write('@InputStreams   ')
        for i in range(nr):
            if Mb[i,0] > 0:
                if in_count != n_in:
                    f.write('{}   {}   \n'.format(i,Mb[i,0]))
                    in_count = in_count + 1
                else:
                    f.write('{}   {};   \n'.format(i,Mb[i,0]))


        # Write output connections
        n_out = np.count_nonzero(Mb[:,1])
        out_count = 1
        f.write('@OutputStreams   ')
        for i in range(nr):
            if Mb[i,1] > 0:
                if out_count != n_out:
                    f.write('{}   {}   \n'.format(i,Mb[i,1]))
                    out_count = out_count + 1
                else:
                    f.write('{}   {};   \n'.format(i,Mb[i,1]))

        # Verbosity
        f.write('@SpeciesToMonitor     NO NH3; \n')
        f.write('@VerbosityLevel     1; \n } \n')

        # Kinetic mechanism dictionary
        f.write('Dictionary kinetic-mechanism \n { \n @Kinetics ')
        f.write(chemfile + '; \n')
        f.write('@Thermodynamics ')
        f.write(thermofile + '; \n')
        f.write('@Output kinetics; \n }')
    









        


                





        
        


            
            




    









        







