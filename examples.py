import cmath, math

import circuit_sim
from circuit_sim import bode_plot, interpolate, line_chart


def dc_analysis():
    circuit = """    
        R R1    vcc     v_out   1k
        R       v_out   gnd     1kOhm
    
        vcc = 2.5v 
        """
    circuit = circuit_sim.Circuit.build_from_string(circuit)
    circuit.dc_analysis()

    print("v_out =", circuit.get_variable("v_out")) # 1.25
    circuit.print_equations() # (0.002)(v_out) = 0.0025
    circuit.print_all_variables() # v_out = 1.25


def non_linear_dc_analysis():
    circuit = """
        R           vcc     v1      0.1
        D my_diode  v1      gnd     i0=1e-5 m=3 v0=0.5

        vcc = 5v 
        """
    circuit = circuit_sim.Circuit.build_from_string(circuit)
    circuit.dc_analysis()

    print("v1 =", circuit.get_variable("v1"))  # 4.701818974760387
    print()

    circuit.print_equations()
    # (10.0)(v1) + (1.0)(my_diode.current) = 50.0
    # (8.957281531220291)(my_diode.internal_node) + (-1.0)(my_diode.current) = 0.0
    # (1.0)(v1) + (-1.0)(my_diode.internal_node) = 4.368926652240085
    print()

    circuit.print_all_variables()
    # v1 = 4.701818974760387
    # my_diode.internal_node = 0.33289232252030193
    # my_diode.current = 2.981810252396129

    # externally, confirm the following:
    # diode current: 2.982 = 0.00001*exp(3*(4.70812-0.5))
    # resistor current: 2.982 = (5 - 4.70182) / 0.1


def transient_simulation():
    circuit = """
        R   vcc     v_out   1k
        R   v_out   gnd     1k
        C   v_out   gnd     30uF
        
        vcc = 1V
        """

    circuit = circuit_sim.Circuit.build_from_string(circuit)
    time_stamps, results = circuit.transient_simulation(0, 100e-3, ["v_out"])

    # print results
    print("time".center(15), "v_out".center(18))
    for time in [15.31e-3, 24.88e-3, 50e-3]:
        print(str(time).center(15), interpolate(time, time_stamps, results[0]))

    # plot results
    line_chart(x_label="time",
               #    [   x,            y,           graph_title   ]
               data=[time_stamps, results[0], "Capacitor Voltage"],
               legend_location="center right")



def ac_sweep():
    circuit = """
        R   vcc     v_out   1k
        R   v_out   gnd     1k
        C   v_out   gnd     1uF

        vcc = 1V
        """

    circuit = circuit_sim.Circuit.build_from_string(circuit)
    freq, results = circuit.ac_sweep(["v_out"])

    # print results
    print("freq".center(15), "Mag (dB)".center(30), "Phase (degrees)".center(30))
    for f in [10, 318, 100e3]:
        v_out = interpolate(f, freq, results[0])
        mag, phase = cmath.polar(v_out)
        mag = 20 * math.log10(mag)
        phase = math.degrees(phase)

        print(str(f).center(15), str(mag).center(30), str(phase).center(30))

    # plot results
    bode_plot(freq, results[0])


def buck_output_ripple():
    circuit = """
            VG  vg      v_sw    gnd     12v
            L   L1      v_sw    v_out   50uH    v0=0    i0=5   
            C   C1      v_out   gnd     500uF   v0=5    i0=0
            R   R_load  v_out   gnd     1ohm
            """

    circuit = circuit_sim.Circuit.build_from_string(circuit)
    time_stamps, results = circuit.transient_simulation(0, 0, ["v_out"])

    on_time = 10e-6 * 5 / 12
    off_time = 10e-6 - on_time

    for i in range(0, 800):
        vg = circuit.get_component_for_modification("vg")
        vg.value = 12
        circuit.continue_transient_simulation(on_time, time_step=100e-9)

        vg = circuit.get_component_for_modification("vg")
        # The "get_component_for_modification" needs to be called again
        # and again because it registers the "vg" component as having
        # been modified.
        vg.value = 0
        circuit.continue_transient_simulation(off_time, time_step=100e-9)

    # plot full result
    line_chart(x_label="time",
               #    [   x,            y,        graph_title  ]
               data=[time_stamps, results[0], "v_out Voltage"],
               legend_location="upper right")

    # The steady state estimation is off - it should be 5V ideally.
    # Using time_step=5e-9 during the transient simulation will
    # improve steady state estimation, but simulation time will
    # be much longer.

    # plot final cycles
    line_chart(x_label="time",
               data=[time_stamps[-500:], results[0][-500:], "v_out Voltage"],
               legend_location="upper right")

    circuit.print_all_variables()


class Controller:
    def __init__(self, circuit: circuit_sim.Circuit):
        self.__circuit = circuit
        self.__goal = 5.0

        self.__duty_cycle = 0   # 0 to 1.0

        # v_out data points
        self.__v_out_error = [0.0] * 10

        # control equation coefficients
        self.__coeff = [0.60, 0.01, 0.01, 0.01, 0.01,
                        0.01, 0.01, 0.01, 0.01, 0.01]
        self.__norm = 1 / sum(self.__coeff)

        # control gain
        self.__control_gain = -0.002
        # Note that gain is negative. Positive error requires
        # a reduction in duty cycle.


    def get_duty_cycle(self):
        return self.__duty_cycle

    def control_loop(self):
        """Updates the internal duty cycle variable."""
        # read output and put it in the "v_out_err" list
        v_out = self.__circuit.get_variable("v_out")
        error = v_out - self.__goal
        self.__v_out_error.insert(0, error)
        self.__v_out_error = self.__v_out_error[:-1]

        # compute total error
        total_error = 0
        for i in range(0, len(self.__v_out_error)):
            total_error += self.__coeff[i] * self.__v_out_error[i]

        total_error =  total_error / self.__norm
        self.__duty_cycle += (total_error * self.__control_gain)

        # limit duty cycle
        upper_limit = self.__goal / 12 * 1.2

        if self.__duty_cycle > upper_limit:
            self.__duty_cycle = upper_limit

        elif self.__duty_cycle < 0:
            self.__duty_cycle = 0.0


def run_buck_converter(circuit: circuit_sim.Circuit,
                       controller: Controller, duty_cycle_data: list,
                       duty_cycle_data_t: list, num_cycles: int):
    """Runs buck converter simulation

    :param circuit: the buck converter circuit
    :param controller: the digital controller for the converter
    :param duty_cycle_data: a list to hold the duty cycles used
    :param duty_cycle_data_t: a list to hold the time stamps for the duty
        cycle data
    :param num_cycles: number of cycles to run the converter
    """
    cycle_time = 10e-6  # 10us pwm period

    for i in range(0, num_cycles):
        duty_cycle = controller.get_duty_cycle()
        duty_cycle_data.append(duty_cycle)
        duty_cycle_data_t.append(circuit.get_transient_simulation_time())

        vg = circuit.get_component_for_modification("vg")
        vg.value = 12 * duty_cycle

        circuit.continue_transient_simulation(cycle_time, time_step=cycle_time/10)

        controller.control_loop()
        # the duty cycle update will be applied on next loop


def digital_buck():
    circuit = """
            VG  vg      v_sw    gnd     12v
            L   L1      v_sw    v_out   50uH   
            C   C1      v_out   gnd     500uF
            R   R_load  v_out   gnd     1ohm
            """

    circuit = circuit_sim.Circuit.build_from_string(circuit)
    time_stamps, results = circuit.transient_simulation(0, 0, ["v_out"])
    duty_cycle_data = []
    duty_cycle_data_t = []

    controller = Controller(circuit)

    # starting condition: 1 ohm load
    run_buck_converter(circuit, controller, duty_cycle_data,
                       duty_cycle_data_t, num_cycles=1000)

    # change load to 0.1 ohm
    r_load = circuit.get_component_for_modification("R_load")
    r_load.value = 0.1

    run_buck_converter(circuit, controller, duty_cycle_data,
                       duty_cycle_data_t, num_cycles=1000)

    # plot results
    line_chart(x_label="time",
               #    [   x,            y,        graph_title  ]
               data=[time_stamps, results[0], "v_out Voltage",
                     duty_cycle_data_t, duty_cycle_data, "duty cycle"],
                     legend_location="center right")




if __name__ == "__main__":
    print("DC Analysis Example")
    dc_analysis()

    print("\nNon-linear DC Analysis Example")
    non_linear_dc_analysis()

    print("\nTransient Simulation Example")
    transient_simulation()

    print("\nAC Sweep Example")
    ac_sweep()

    print("\nBuck Output Ripple Example")
    buck_output_ripple()

    print("\nDigital Buck Example")
    digital_buck()




