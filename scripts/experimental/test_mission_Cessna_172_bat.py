# tut_mission_Cessna_172_bat.py
# 
# Created:  Michael Colonno, Apr 2013
# Modified: Michael Vegh   , Sep 2013
#           Trent Lukaczyk , Jan 2014

""" evaluate a simple mission with a Cessna 172 Skyhawk 
    powered by batteries 
"""


# ----------------------------------------------------------------------
#   Imports
# ----------------------------------------------------------------------

import SUAVE

import numpy as np
import pylab as plt

# ----------------------------------------------------------------------
#   Main
# ----------------------------------------------------------------------
def main():
    
    # build the vehicle
    vehicle = define_vehicle()
    
    # define the mission
    mission = define_mission(vehicle)
    
    # evaluate the mission
    results = evaluate_mission(vehicle,mission)
    
    # plot results
    post_process(vehicle,mission,results)
    
    return


# ----------------------------------------------------------------------
#   Build the Vehicle
# ----------------------------------------------------------------------

def define_vehicle():
    
    # ------------------------------------------------------------------
    #   Initialize the Vehicle
    # ------------------------------------------------------------------    
    
    vehicle = SUAVE.Vehicle()
    vehicle.tag = 'Cessna 172'
    
    # vehicle-level properties
    vehicle.Mass_Props.m_full       = 743.0  # kg
    vehicle.Mass_Props.m_empty      = 743.0  # kg
    vehicle.Mass_Props.m_takeoff    = 743.0  # kg
    vehicle.Mass_Props.m_flight_min = 743.0  # kg
    vehicle.delta                   = 0.0    # deg  
    
    
    # ------------------------------------------------------------------
    #   Propulsor
    # ------------------------------------------------------------------        
    
    # create a motor
    propulsor = SUAVE.Components.Propulsors.Motor_Bat()
    propulsor.tag = 'Lycoming_IO_360_L2A_Battery'
    
    propulsor.propellant = SUAVE.Attributes.Propellants.Aviation_Gasoline()
    propulsor.D               = 1.905    # m
    propulsor.F_min_static    = 343.20   # N
    propulsor.F_max_static    = 2085.9   # N
    propulsor.mdot_min_static = 0.004928 # kg/s 
    propulsor.mdot_max_static = 0.01213  # kg/s
    
    # add component to vehicle
    vehicle.append_component(propulsor)     
    # --> vehicle.Propulsors['Lycoming_IO_360_L2A_Battery']
    
    # ------------------------------------------------------------------
    #   Battery
    # ------------------------------------------------------------------        
    
    #create battery
    battery = SUAVE.Components.Energy.Storages.Battery()
    battery.tag = 'Battery'
    battery.type ='Li-Air'
    # attributes
    battery.SpecificEnergy = 1000.0 #W-h/kW
    battery.SpecificPower  = 0.64   #kW/kg    
    
    # add component to vehicle
    vehicle.append_component( battery )
    # --> vehicle.Energy.Storages['Battery']
    
    
    # ------------------------------------------------------------------
    #   Aerodynamic Model
    # ------------------------------------------------------------------        
    
    # a simple aerodynamic model
    aerodynamics = SUAVE.Attributes.Aerodynamics.Finite_Wing()
    
    aerodynamics.S   = 16.2    # reference area (m^2)
    aerodynamics.AR  = 7.32    # aspect ratio
    aerodynamics.e   = 0.80    # Oswald efficiency factor
    aerodynamics.CD0 = 0.0341  # CD at zero lift (from wind tunnel data)
    aerodynamics.CL0 = 0.30    # CL at alpha = 0.0 (from wind tunnel data)  
    
    # add model to vehicle aerodynamics
    vehicle.Aerodynamics = aerodynamics
    
    
    # ------------------------------------------------------------------
    #   Configurations
    # ------------------------------------------------------------------        
    
    # Takeoff configuration
    config = vehicle.new_configuration("takeoff")
    # --> vehicle.Configs['takeoff']
    
    # Cruise Configuration
    config = vehicle.new_configuration("cruise")
    # --> vehicle.Configs['cruise']
    
    
    # ------------------------------------------------------------------
    #   Vehicle Definition Complete
    # ------------------------------------------------------------------
    
    return vehicle

#: def define_vehicle()


# ----------------------------------------------------------------------
#   Define the Mission
# ----------------------------------------------------------------------
def define_mission(vehicle):
    
    # ------------------------------------------------------------------
    #   Initialize the Mission
    # ------------------------------------------------------------------
    
    mission = SUAVE.Analyses.Mission.Sequential_Segments()
    mission.tag = 'Cessna 172 Test Mission'
    
    # initial mass
    mission.m0 = vehicle.Mass_Props.m_full
    
    # atmospheric model
    atmosphere = SUAVE.Attributes.Atmospheres.Earth.US_Standard_1976()
    planet     = SUAVE.Attributes.Planets.Earth()

    # ------------------------------------------------------------------
    #   Climb Segment: constant Mach, constant climb angle 
    # ------------------------------------------------------------------
    
    climb = SUAVE.Analyses.Mission.Segments.Climb.Constant_Mach()
    climb.tag = "Climb"
    
    # connect vehicle configuration
    climb.config = vehicle.Configs.cruise
    
    # segment attributes
    climb.atmosphere = atmosphere
    climb.planet     = planet    
    climb.altitude   = [0.0, 10.0] # km
    climb.Minf       = 0.15        
    climb.psi        = 15.0         # deg
    climb.options.N  = 16

    # add to mission
    mission.append_segment(climb)


    # ------------------------------------------------------------------
    #   Cruise Segment: constant speed, constant altitude
    # ------------------------------------------------------------------
    
    cruise = SUAVE.Analyses.Mission.Segments.Cruise.Constant_Speed_Constant_Altitude()
    cruise.tag = "Cruise"
    
    # connect vehicle configuration
    cruise.config = vehicle.Configs.cruise
    
    # config attributes
    cruise.atmosphere = atmosphere
    cruise.planet     = planet        
    cruise.altitude  =climb.altitude[-1]    
    cruise.Vinf      = 62.0    # m/s
    cruise.range     = 1000    # km
    cruise.options.N = 16
    
    # add to mission
    mission.append_segment(cruise)


    # ------------------------------------------------------------------
    #   Descent Segment: consant speed, constant descent rate
    # ------------------------------------------------------------------
    
    descent = SUAVE.Analyses.Mission.Segments.Descent.Constant_Speed()
    descent.tag = "Descent"
    
    # connect vehicle configuration
    descent.config = vehicle.Configs.cruise

    # segment attributes
    descent.atmosphere  = atmosphere
    descent.planet      = planet        
    descent.altitude  = [cruise.altitude, 0.0] # km
    descent.Vinf      = 45.0        # m/s
    descent.rate      = 5.0         # m/s
    descent.options.N = 16
    
    # add to mission
    mission.append_segment(descent)

    
    # ------------------------------------------------------------------    
    #   Mission definition complete    
    # ------------------------------------------------------------------
    
    return mission

#: def define_mission()


# ----------------------------------------------------------------------
#   Evaluate the Mission
# ----------------------------------------------------------------------
def evaluate_mission(vehicle,mission):
    
    # ------------------------------------------------------------------
    #   Battery Initial Sizing
    # ------------------------------------------------------------------
    
    # component to size
    battery = vehicle.Energy.Storages['Battery']
    
    # sizing on the climb segment
    climb = mission.Segments['Climb']
    
    # estimate required power for the battery
    W = 9.81*vehicle.Mass_Props.m_full
    a = (1.4*287.*293.)**.5
    T = 1./(np.sin(climb.psi*np.pi/180.))  # direction of thrust vector
    factor = 1                             # factor on maximum power requirement of mission
    Preq = climb.Minf * W * a * T / factor # the required power
    Ereq = 1E5                             # required energy; configuration is power limited so it doesn't reallys matter
    
    # accounting for discharge losses without running out of energy    
    
    massE=Ereq/(battery.SpecificEnergy*3600)
    massP=Preq/(battery.SpecificPower*1000)
    battery.Mass_Props.mass=max(massE, massP)
    battery.MaxPower=battery.Mass_Props.mass*(battery.SpecificPower*1000) #find max power available from battery
    battery.TotalEnergy=battery.Mass_Props.mass*battery.SpecificEnergy*3600
    battery.CurrentEnergy=battery.TotalEnergy
    vehicle.Mass_Props.m_full+=battery.Mass_Props.mass
    vehicle.Mass_Props.m_empty+=battery.Mass_Props.mass
    
    # ------------------------------------------------------------------    
    #   Run Mission
    # ------------------------------------------------------------------
    results = SUAVE.Methods.Performance.evaluate_mission(mission)
    
    
    # ------------------------------------------------------------------    
    #   Compute Useful Results
    # ------------------------------------------------------------------
    SUAVE.Methods.Results.compute_energies(results, summary=True)
    SUAVE.Methods.Results.compute_efficiencies(results)
    SUAVE.Methods.Results.compute_velocity_increments(results)
    SUAVE.Methods.Results.compute_alpha(results)    
    
    
    Pbat_loss=np.zeros_like(results.Segments[0].P_e) #initialize battery losses
    Ecurrent=np.zeros_like(results.Segments[0].t) #initialize battery energies
   
    #now run battery
    #now run the battery for the mission
    j=0
    for i in range(len(results.Segments)):
        results.Segments[i].Ecurrent=np.zeros_like(results.Segments[i].t)
        if i==0:
            results.Segments[i].Ecurrent[0]=battery.TotalEnergy
             
        if i!=0 and j!=0:
            results.Segments[i].Ecurrent[0]=results.Segments[i-1].Ecurrent[j] #assign energy at end of segment to next segment 

        for j in range(len(results.Segments[i].P_e)):
            if j!=0:
                Ploss=battery(results.Segments[i].P_e[j], (results.Segments[i].t[j]-results.Segments[i].t[j-1]))
                
            elif i!=0 and j==0:
                Ploss=battery(results.Segments[i].P_e[j], (results.Segments[i].t[j]-results.Segments[i-1].t[-2]))
            elif j==0 and i==0: 
                Ploss=battery(results.Segments[i].P_e[j], (results.Segments[i].t[j+1]-results.Segments[i].t[j]))
            results.Segments[i].Ecurrent[j]=battery.CurrentEnergy
            results.Segments[i].P_e[j]+=Ploss
           
    
    
    return results

# ----------------------------------------------------------------------
#   Plot Results
# ----------------------------------------------------------------------
def post_process(vehicle,mission,results):
    
    # ------------------------------------------------------------------    
    #   Thrust Angle
    # ------------------------------------------------------------------
    title = "Thrust Angle History"
    plt.figure(0)
    for i in range(len(results.Segments)):
        plt.plot(results.Segments[i].t/60,np.degrees(results.Segments[i].gamma),'bo-')
    plt.xlabel('Time (mins)'); plt.ylabel('Thrust Angle (deg)'); plt.title(title)
    plt.grid(True)

    # ------------------------------------------------------------------    
    #   Throttle
    # ------------------------------------------------------------------
    title = "Throttle History"
    plt.figure(1)
    for i in range(len(results.Segments)):
        plt.plot(results.Segments[i].t/60,results.Segments[i].eta,'bo-')
    plt.xlabel('Time (mins)'); plt.ylabel('Throttle'); plt.title(title)
    plt.grid(True)

    # ------------------------------------------------------------------    
    #   Angle of Attack
    # ------------------------------------------------------------------
    title = "Angle of Attack History"
    plt.figure(2)
    for i in range(len(results.Segments)):
        plt.plot(results.Segments[i].t/60,np.degrees(results.Segments[i].alpha),'bo-')
    plt.xlabel('Time (mins)'); plt.ylabel('Angle of Attack (deg)'); plt.title(title)
    plt.grid(True)

    # ------------------------------------------------------------------    
    #   Energy
    # ------------------------------------------------------------------
    title = "Energy"
    plt.figure(3)
    for i in range(len(results.Segments)):
        plt.plot(results.Segments[i].t/60, results.Segments[i].Ecurrent,'bo-')
    plt.xlabel('Time (mins)'); plt.ylabel('Energy in Battery (Joules)'); plt.title(title)
    plt.grid(True)

    # ------------------------------------------------------------------    
    #   Power
    # ------------------------------------------------------------------
    title = "Electrical Power"
    plt.figure(4)
    for i in range(len(results.Segments)):
        plt.plot(results.Segments[i].t/60,results.Segments[i].P_e,'bo-')
    plt.xlabel('Time (mins)'); plt.ylabel('Electrical Power (Watts)'); plt.title(title)
    plt.grid(True)

    plt.show()

    return     


# ---------------------------------------------------------------------- 
#   Call Main
# ----------------------------------------------------------------------
if __name__ == '__main__':
    main()


