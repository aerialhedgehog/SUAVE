# test_aerodynamics
#
# Created:  Tim MacDonald - 09/09/14
# Modified: Tim MacDonald - 03/10/15
#
# Changed to use new structures and drag functions from Tarik

import SUAVE
from SUAVE.Core import Units
from SUAVE.Core import Data

from SUAVE.Methods.Aerodynamics.Fidelity_Zero.Lift import compute_aircraft_lift
from SUAVE.Methods.Aerodynamics.Fidelity_Zero.Drag import compute_aircraft_drag

from test_mission_B737 import vehicle_setup

import numpy as np
import pylab as plt

import copy, time
from copy import deepcopy
import random

def main():
    
    # initialize the vehicle
    vehicle = vehicle_setup() 
    for wing in vehicle.wings:
        wing.areas.wetted   = 2.0 * wing.areas.reference
        wing.areas.exposed  = 0.8 * wing.areas.wetted
        wing.areas.affected = 0.6 * wing.areas.wetted  
        
        
    # initalize the aero model
    aerodynamics = SUAVE.Analyses.Aerodynamics.Fidelity_Zero()
    aerodynamics.geometry = vehicle
        
    aerodynamics.initialize()    
    
    
    #no of test points
    test_num = 11
    
    #specify the angle of attack
    angle_of_attacks = np.linspace(-.174,.174,test_num)[:,None] #* Units.deg
    
    
    # Cruise conditions (except Mach number)
    state = SUAVE.Analyses.Mission.Segments.Conditions.State()
    state.conditions = SUAVE.Analyses.Mission.Segments.Conditions.Aerodynamics()
    
    
    state.expand_rows(test_num)    
        
    # --------------------------------------------------------------------
    # Initialize variables needed for CL and CD calculations
    # Use a seeded random order for values
    # --------------------------------------------------------------------
    
    random.seed(1)
    Mc = np.linspace(0.05,0.9,test_num)
    random.shuffle(Mc)
    rho = np.linspace(0.3,1.3,test_num)
    random.shuffle(rho)
    mu = np.linspace(5*10**-6,20*10**-6,test_num)
    random.shuffle(mu)
    T = np.linspace(200,300,test_num)
    random.shuffle(T)
    pressure = np.linspace(10**5,10**6,test_num)
    
    # Changed after to preserve seed for initial testing
    Mc = Mc[:,None]
    rho = rho[:,None]
    mu = mu[:,None]
    T = T[:,None]
    pressure = pressure[:,None]

    
    state.conditions.freestream.mach_number = Mc
    state.conditions.freestream.density = rho
    state.conditions.freestream.dynamic_viscosity = mu
    state.conditions.freestream.temperature = T
    state.conditions.freestream.pressure = pressure
    
    state.conditions.aerodynamics.angle_of_attack = angle_of_attacks   
    
    
    # --------------------------------------------------------------------
    # Surrogate
    # --------------------------------------------------------------------    
    
            
    #call the aero model        
    results = aerodynamics.evaluate(state)
    
    #build a polar for the markup aero
    polar = Data()    
    CL = results.lift.total
    CD = results.drag.total
    polar.lift = CL
    polar.drag = CD    
    
    
    # --------------------------------------------------------------------
    # Test compute Lift
    # --------------------------------------------------------------------
    
    
    
    #compute_aircraft_lift(conditions, configuration, geometry) 
    
    lift = state.conditions.aerodynamics.lift_coefficient
    lift_r = np.array([-2.07712357, -0.73495391, -0.38858687, -0.1405849 ,  0.22295808,
                       0.5075275 ,  0.67883681,  0.92787301,  1.40470556,  2.08126751,
                       1.69661601])[:,None]
    
    lift_test = np.abs((lift-lift_r)/lift)
    
    print '\nCompute Lift Test Results\n'
    #print lift_test

    print lift
        
    assert(np.max(lift_test)<1e-4), 'Aero regression failed at compute lift test'    
    
    
    # --------------------------------------------------------------------
    # Test compute drag 
    # --------------------------------------------------------------------
    
    #compute_aircraft_drag(conditions, configuration, geometry)
    
    # Pull calculated values
    drag_breakdown = state.conditions.aerodynamics.drag_breakdown
    
    # Only one wing is evaluated since they rely on the same function
    cd_c           = drag_breakdown.compressible['main_wing'].compressibility_drag
    cd_i           = drag_breakdown.induced.total
    cd_m           = drag_breakdown.miscellaneous.total
    # cd_m_fuse_base = drag_breakdown.miscellaneous.fuselage_base
    # cd_m_fuse_up   = drag_breakdown.miscellaneous.fuselage_upsweep
    # cd_m_nac_base  = drag_breakdown.miscellaneous.nacelle_base['turbo_fan']
    # cd_m_ctrl      = drag_breakdown.miscellaneous.control_gaps
    cd_p_fuse      = drag_breakdown.parasite['fuselage'].parasite_drag_coefficient
    cd_p_wing      = drag_breakdown.parasite['main_wing'].parasite_drag_coefficient
    cd_tot         = drag_breakdown.total
    
    (cd_c_r, cd_i_r, cd_m_r, cd_m_fuse_base_r, cd_m_fuse_up_r, cd_m_nac_base_r, cd_m_ctrl_r, cd_p_fuse_r, cd_p_wing_r, cd_tot_r) = reg_values()
    
    drag_tests = Data()
    drag_tests.cd_c = np.abs((cd_c-cd_c_r)/cd_c)
    drag_tests.cd_i = np.abs((cd_i-cd_i_r)/cd_i)
    drag_tests.cd_m = np.abs((cd_m-cd_m_r)/cd_m)
    ## Commented lines represent values not set by current drag functions, but to be recreated in the future
    # Line below is not normalized since regression values are 0, insert commented line if this changes
    # drag_tests.cd_m_fuse_base = np.abs((cd_m_fuse_base-cd_m_fuse_base_r)) # np.abs((cd_m_fuse_base-cd_m_fuse_base_r)/cd_m_fuse_base)
    # drag_tests.cd_m_fuse_up   = np.abs((cd_m_fuse_up - cd_m_fuse_up_r)/cd_m_fuse_up)
    # drag_tests.cd_m_ctrl      = np.abs((cd_m_ctrl - cd_m_ctrl_r)/cd_m_ctrl)
    drag_tests.cd_p_fuse      = np.abs((cd_p_fuse - cd_p_fuse_r)/cd_p_fuse)
    drag_tests.cd_p_wing      = np.abs((cd_p_wing - cd_p_wing_r)/cd_p_wing)
    drag_tests.cd_tot         = np.abs((cd_tot - cd_tot_r)/cd_tot)
    
    print '\nCompute Drag Test Results\n'
    print drag_tests
    
    for i, tests in drag_tests.items():
        assert(np.max(tests)<1e-4),'Aero regression test failed at ' + i
    
    #return conditions, configuration, geometry, test_num
      

def reg_values():
    cd_c_r = np.array([  1.41429794e-08,   2.96579619e-09,   1.03047740e-22,   4.50771390e-09,
                         1.27784183e-03,   1.31214322e-04,   3.98984222e-09,   6.19742191e-11,
                         8.21182714e-05,   1.20217216e-03,   5.63926215e-14])
    
    cd_i_r = np.array([ 0.17295472,  0.02165349,  0.00605319,  0.00079229,  0.00199276,
                        0.01032588,  0.01847305,  0.03451317,  0.07910034,  0.17364551,
                        0.11539178])
    cd_m_r = np.array([ 0.00335972,  0.00335972,  0.00335972,  0.00335972,  0.00335972,
                        0.00335972,  0.00335972,  0.00335972,  0.00335972,  0.00335972,
                        0.00335972])
    
    cd_m_fuse_base_r = np.array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.])
    
    cd_m_fuse_up_r   = np.array([  4.80530506e-05,   4.80530506e-05,   4.80530506e-05,
                                   4.80530506e-05,   4.80530506e-05,   4.80530506e-05,
                                   4.80530506e-05,   4.80530506e-05,   4.80530506e-05,
                                   4.80530506e-05,   4.80530506e-05])
    
    cd_m_nac_base_r = np.array([ 0.00033128,  0.00033128,  0.00033128,  0.00033128,  0.00033128,
                                0.00033128,  0.00033128,  0.00033128,  0.00033128,  0.00033128,
                                0.00033128])
    
    cd_m_ctrl_r     = np.array([ 0.0001,  0.0001,  0.0001,  0.0001,  0.0001,  0.0001,  0.0001,
                                 0.0001,  0.0001,  0.0001,  0.0001])
    
    cd_p_fuse_r     = np.array([ 0.0083099 ,  0.00967087,  0.01479402,  0.00948378,  0.00967548,
                                 0.00812209,  0.00992429,  0.01224443,  0.00966431,  0.00869054,
                                 0.01006034])
    
    cd_p_wing_r     = np.array([ 0.00488075,  0.00492079,  0.00759052,  0.00476707,  0.00542126,
                                 0.00421107,  0.00496795,  0.00620658,  0.00498686,  0.00464893,
                                 0.00499523])
    
    cd_tot_r        = np.array([ 0.1984218 ,  0.04386556,  0.03793675,  0.02213741,  0.02631103,
                                 0.02960579,  0.04098187,  0.0619007 ,  0.10264035,  0.19867105,
                                 0.1400349 ])
    
    return cd_c_r[:,None], cd_i_r[:,None], cd_m_r[:,None], cd_m_fuse_base_r[:,None], cd_m_fuse_up_r[:,None], \
           cd_m_nac_base_r[:,None], cd_m_ctrl_r[:,None], cd_p_fuse_r[:,None], cd_p_wing_r[:,None], cd_tot_r[:,None]

if __name__ == '__main__':
    #(conditions, configuration, geometry, test_num) = main()
    main()
    
    print 'Aero regression test passed!'
    
    ## --------------------------------------------------------------------
    ## Drag Polar
    ## --------------------------------------------------------------------  
    
    # --------------------------------------------------------------------
    # Drag Polar
    # --------------------------------------------------------------------
    
    # initialize the vehicle
    vehicle = vehicle_setup() 
    for wing in vehicle.wings:
        wing.areas.wetted   = 2.0 * wing.areas.reference
        wing.areas.exposed  = 0.8 * wing.areas.wetted
        wing.areas.affected = 0.6 * wing.areas.wetted  
        
        
    # initalize the aero model
    aerodynamics = SUAVE.Analyses.Aerodynamics.Fidelity_Zero()
    aerodynamics.geometry = vehicle
    
    ## modify inviscid wings - linear model
    #inviscid_wings = SUAVE.Analyses.Aerodynamics.Linear_Lift()
    #inviscid_wings.settings.slope_correction_coefficient = 1.04
    #inviscid_wings.settings.zero_lift_coefficient = 2.*np.pi* 3.1 * Units.deg    
    #aerodynamics.process.compute.lift.inviscid_wings = inviscid_wings
    
    ## modify inviscid wings - avl model
    #inviscid_wings = SUAVE.Analyses.Aerodynamics.Surrogates.AVL()
    #inviscid_wings.geometry = vehicle
    #aerodynamics.process.compute.lift.inviscid_wings = inviscid_wings
    
    aerodynamics.initialize()    
    
    
    #no of test points
    test_num = 11
    
    #specify the angle of attack
    angle_of_attacks = np.linspace(-.174,.174,test_num) #* Units.deg
    
    
    # Cruise conditions (except Mach number)
    state = SUAVE.Analyses.Mission.Segments.Conditions.State()
    state.conditions = SUAVE.Analyses.Mission.Segments.Conditions.Aerodynamics()
    
    
    state.expand_rows(test_num)    
    
    #specify  the conditions at which to perform the aerodynamic analysis
    state.conditions.aerodynamics.angle_of_attack[:,0] = angle_of_attacks
    state.conditions.freestream.mach_number = np.array([0.8]*test_num)
    state.conditions.freestream.density = np.array([0.3804534]*test_num)
    state.conditions.freestream.dynamic_viscosity = np.array([1.43408227e-05]*test_num)
    state.conditions.freestream.temperature = np.array([218.92391647]*test_num)
    state.conditions.freestream.pressure = np.array([23908.73408391]*test_num)
            
    #call the aero model        
    results = aerodynamics.evaluate(state)
    
    #build a polar for the markup aero
    polar = Data()    
    CL = results.lift.total
    CD = results.drag.total
    polar.lift = CL
    polar.drag = CD
    

    #load old results
    old_polar = SUAVE.Input_Output.load('polar_M8.pkl') #('polar_old2.pkl')
    CL_old = old_polar.lift
    CD_old = old_polar.drag

    
    #plot the results
    plt.figure("Drag Polar")
    axes = plt.gca()     
    axes.plot(CD,CL,'bo-',CD_old,CL_old,'*')
    axes.set_xlabel('$C_D$')
    axes.set_ylabel('$C_L$')
    
    
    plt.show(block=True) # here so as to not block the regression test
      
