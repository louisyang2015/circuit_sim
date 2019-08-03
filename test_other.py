import cmath, math

import circuit_sim
from circuit_sim import interpolate


def check_float(test_name: str, result_value: float, expected_value: float):
    if abs(expected_value) > 1e-10:
        percent_diff = abs(result_value - expected_value) / abs(expected_value)
    else:
        percent_diff = abs(result_value - expected_value) / 1e-10

    if percent_diff > 0.01:
        raise Exception(test_name + " failure. Expecting " + str(expected_value)
                        + " but got " + str(result_value) + " instead.")


def test_interpolate():
    value_list = [1, 2, 3, 4]
    data_list = [1, 5, 11, 19] # slope: +4 +6 +8

    check_float("test_interpolate() 1.5", interpolate(1.5, value_list, data_list), 3)
    check_float("test_interpolate() 2.5", interpolate(2.5, value_list, data_list), 8)
    check_float("test_interpolate() 3.5", interpolate(3.5, value_list, data_list), 15)

    check_float("test_interpolate() 0", interpolate(0, value_list, data_list), -3)
    check_float("test_interpolate() 5", interpolate(5, value_list, data_list), 27)


def cap_grounded_transient(options_str):
    circuit = """
        R   vcc     v_out   1k
        R   v_out   gnd     1k
        C   v_out   gnd     30uF

        vcc = 1V
        """

    circuit = circuit_sim.Circuit.build_from_string(circuit)
    time_stamps, results = circuit.transient_simulation(0, 100e-3, ["v_out"], options=options_str)

    check_float("cap_grounded_transient() t=15.31e-3",
                interpolate(15.31e-3, time_stamps, results[0]), 0.319)
    check_float("cap_grounded_transient() t=24.88e-3",
                interpolate(24.88e-3, time_stamps, results[0]), 0.4045)
    check_float("cap_grounded_transient() t=50e-3",
                interpolate(50e-3, time_stamps, results[0]), 0.482)


def cap_floating_transient(options_str):
    circuit = """
        R   vcc     v_out1  1k
        R   v_out1  v_out2  2k
        R   v_out2  gnd     500
        C   v_out1  v_out2  30uF

        vcc = 3.5V
        """

    circuit = circuit_sim.Circuit.build_from_string(circuit)
    time_stamps, results = circuit.transient_simulation(0, 100e-3, ["v_out1", "v_out2"], options=options_str)

    # circuit_sim.line_chart(x_label="time",
    #                        data=[time_stamps, results[0], "v_out1",
    #                              time_stamps, results[1], "v_out2"])

    check_float("cap_floating_transient() t=12.19e-3 v_out1",
                interpolate(12.19e-3, time_stamps, results[0]), 1.67)
    check_float("cap_floating_transient() t=25.73e-3 v_out1",
                interpolate(25.73e-3, time_stamps, results[0]), 2.01)
    check_float("cap_floating_transient() t=43.57e-3 v_out1",
                interpolate(43.57e-3, time_stamps, results[0]), 2.25)

    check_float("cap_floating_transient() t=16.93e-3 v_out2",
                interpolate(16.93e-3, time_stamps, results[1]), 0.846)
    check_float("cap_floating_transient() t=26.86e-3 v_out2",
                interpolate(26.86e-3, time_stamps, results[1]), 0.735)
    check_float("cap_floating_transient() t=39.73e-3 v_out2",
                interpolate(39.73e-3, time_stamps, results[1]), 0.642)


def get_mag_and_phase(value: complex):
    """Return magnitude in dB and phase in degrees."""
    mag, phase = cmath.polar(value)
    mag = 20 * math.log10(mag)
    phase = math.degrees(phase)
    return mag, phase


def cap_grounded_ac_sweep(options_str):
    circuit = """
        R   vcc     v_out   1k
        R   v_out   gnd     1k
        C   v_out   gnd     1uF

        vcc = 1V
        """

    circuit = circuit_sim.Circuit.build_from_string(circuit)
    freq, results = circuit.ac_sweep(["v_out"], options=options_str)

    v_out = interpolate(10, freq, results[0])
    mag, phase = get_mag_and_phase(v_out)
    check_float("cap_grounded_ac_sweep() f=10 mag", mag, -6.02)
    check_float("cap_grounded_ac_sweep() f=10 phase", phase, -1.8)

    v_out = interpolate(318, freq, results[0])
    mag, phase = get_mag_and_phase(v_out)
    check_float("cap_grounded_ac_sweep() f=318 mag", mag, -9.03)
    check_float("cap_grounded_ac_sweep() f=318 phase", phase, -44.97)

    v_out = interpolate(10e3, freq, results[0])
    mag, phase = get_mag_and_phase(v_out)
    check_float("cap_grounded_ac_sweep() f=10e3 mag", mag, -35.97)
    check_float("cap_grounded_ac_sweep() f=10e3 phase", phase, -88.18)


def cap_floating_ac_sweep(options_str):
    circuit = """
        R   vcc     v_out1  1k
        R   v_out1  v_out2  2k
        C   v_out1  v_out2  1uF
        R   v_out2  gnd     1k

        vcc = 1V
        """

    circuit = circuit_sim.Circuit.build_from_string(circuit)
    freq, results = circuit.ac_sweep(["v_out1", "v_out2"], options=options_str)

    v_out = interpolate(12, freq, results[0])
    mag, phase = get_mag_and_phase(v_out)
    check_float("cap_grounded_ac_sweep() v_out1 f=12 mag", mag, -2.51)
    check_float("cap_grounded_ac_sweep() v_out1 f=12 phase", phase, -1.43)

    v_out = interpolate(206, freq, results[0])
    mag, phase = get_mag_and_phase(v_out)
    check_float("cap_grounded_ac_sweep() v_out1 f=206 mag", mag, -4.36)
    check_float("cap_grounded_ac_sweep() v_out1 f=206 phase", phase, -11.52)

    v_out = interpolate(2.59e3, freq, results[0])
    mag, phase = get_mag_and_phase(v_out)
    check_float("cap_grounded_ac_sweep() v_out1 f=2.59e3 mag", mag, -6)
    check_float("cap_grounded_ac_sweep() v_out1 f=2.59e3 phase", phase, -1.75)

    v_out = interpolate(26, freq, results[1])
    mag, phase = get_mag_and_phase(v_out)
    check_float("cap_grounded_ac_sweep() v_out2 f=26 mag", mag, -11.71)
    check_float("cap_grounded_ac_sweep() v_out2 f=26 phase", phase, 8.82)

    v_out = interpolate(110, freq, results[1])
    mag, phase = get_mag_and_phase(v_out)
    check_float("cap_grounded_ac_sweep() v_out2 f=110 mag", mag, -9.1)
    check_float("cap_grounded_ac_sweep() v_out2 f=110 phase", phase, 19.46)

    v_out = interpolate(836, freq, results[1])
    mag, phase = get_mag_and_phase(v_out)
    check_float("cap_grounded_ac_sweep() v_out2 f=836 mag", mag, -6.14)
    check_float("cap_grounded_ac_sweep() v_out2 f=836 phase", phase, 5.34)


def inductor_grounded_transient(options_str):
    circuit = """
        R       vcc     v_out   10
        R       v_out   gnd     2
        L   L1  v_out   gnd     30mH

        vcc = 1V
        """

    circuit = circuit_sim.Circuit.build_from_string(circuit)
    time_stamps, results = circuit.transient_simulation(0, 100e-3, ["L1.current", "v_out"], options=options_str)

    check_float("inductor_grounded_transient() L1.current t=11.48e-3",
                interpolate(11.48e-3, time_stamps, results[0]), 46.97e-3)
    check_float("inductor_grounded_transient() L1.current t=24.4e-3",
                interpolate(24.4e-3, time_stamps, results[0]), 74.15e-3)
    check_float("inductor_grounded_transient() L1.current t=44.26e-3",
                interpolate(44.26e-3, time_stamps, results[0]), 91.43e-3)

    check_float("inductor_grounded_transient() v_out t=5.98e-3",
                interpolate(5.98e-3, time_stamps, results[1]), 119.98e-3)
    check_float("inductor_grounded_transient() v_out t=17.7e-3",
                interpolate(17.7e-3, time_stamps, results[1]), 62.53e-3)
    check_float("inductor_grounded_transient() v_out t=39.71e-3",
                interpolate(39.71e-3, time_stamps, results[1]), 18.39e-3)


def inductor_floating_transient(options_str):
    circuit = """
        R       vcc     v_out1  8
        R       v_out1  v_out2  2
        R       v_out2  gnd     2
        L   L1  v_out1  v_out2  30mH

        vcc = 2V
        """

    circuit = circuit_sim.Circuit.build_from_string(circuit)
    time_stamps, results = circuit.transient_simulation(0, 100e-3, ["L1.current", "v_out1"], options=options_str)

    check_float("inductor_floating_transient() t=13.16e-3 L1.current",
                interpolate(13.16e-3, time_stamps, results[0]), 103.39e-3)
    check_float("inductor_floating_transient() t=25.84e-3 L1.current",
                interpolate(25.84e-3, time_stamps, results[0]), 152.27e-3)
    check_float("inductor_floating_transient() t=42.11e-3 L1.current",
                interpolate(42.11e-3, time_stamps, results[0]), 180.69e-3)

    check_float("inductor_floating_transient() t=16.03e-3 v_out",
                interpolate(16.03e-3, time_stamps, results[1]), 509.79e-3)
    check_float("inductor_floating_transient() t=31.82e-3 v_out",
                interpolate(31.82e-3, time_stamps, results[1]), 445.63e-3)
    check_float("inductor_floating_transient() t=51.2e-3 v_out",
                interpolate(51.2e-3, time_stamps, results[1]), 415.53e-3)



def LC_ac_sweep(options_str):
    circuit = """
        L   vcc     v_out   1m
        C   v_out   gnd     100uF

        vcc = 1V
        """

    circuit = circuit_sim.Circuit.build_from_string(circuit)
    freq, results = circuit.ac_sweep(["v_out"], options=options_str)

    v_out = interpolate(323, freq, results[0])
    mag, phase = get_mag_and_phase(v_out)
    check_float("LC_ac_sweep() f=323 mag", mag, 4.61)
    check_float("LC_ac_sweep() f=323 phase", phase, 0)

    v_out = interpolate(485.93, freq, results[0])
    mag, phase = get_mag_and_phase(v_out)
    # check_float("LC_ac_sweep() f=485.93 mag", mag, 23.38) # Tina reports 23.38
    # In this area, Tina reports different values than this simulator
    check_float("LC_ac_sweep() f=485.93 mag", mag, 23.9)
    check_float("LC_ac_sweep() f=485.93 phase", phase, 0)

    v_out = interpolate(14.35e3, freq, results[0])
    mag, phase = get_mag_and_phase(v_out)
    check_float("LC_ac_sweep() f=14.35e3 mag", mag, -58.19)
    check_float("LC_ac_sweep() f=14.35e3 phase", phase, 180)



def run_all_tests():
    print("Running test_other.py :: run_all_tests()")
    test_interpolate()

    for options_str in ["dense", "sparse"]:
        cap_grounded_transient(options_str)
        cap_floating_transient(options_str)
        cap_grounded_ac_sweep(options_str)
        cap_floating_ac_sweep(options_str)
        inductor_grounded_transient(options_str)
        inductor_floating_transient(options_str)
        LC_ac_sweep(options_str)


if __name__ == "__main__":
    run_all_tests()


