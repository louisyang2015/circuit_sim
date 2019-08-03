import circuit_sim


def check_float(test_name: str, result_value: float, expected_value: float):
    if abs(expected_value) > 1e-10:
        percent_diff = abs(result_value - expected_value) / abs(expected_value)
    else:
        percent_diff = abs(result_value - expected_value) / 1e-10

    if percent_diff > 0.01:
        raise Exception(test_name + " failure. Expecting " + str(expected_value)
                        + " but got " + str(result_value) + " instead.")


def resistor_divider(options):
    circuit = """
        R vcc v_out 1k
        R v_out gnd 1kOhm
        
        vcc = 2.5v 
        """
    circuit = circuit_sim.Circuit.build_from_string(circuit)
    circuit.dc_analysis(options)

    check_float("resistor_divider() v_out", circuit.get_variable("v_out"), 1.25)


def resistor_divider2(options):
    circuit = """
        R       vcc     v_out1      1e3
        R R2    v_out1  v_out2      1000
        R R3    v_out2  v_out3      3KOhm
        R       v_out3  v_out4      500
        R       v_out4  gnd         0.5k 
    
        vcc = 6 
        """
    circuit = circuit_sim.Circuit.build_from_string(circuit)
    circuit.dc_analysis(options)

    check_float("resistor_divider2() v_out1", circuit.get_variable("v_out1"), 5)
    check_float("resistor_divider2() v_out2", circuit.get_variable("v_out2"), 4)
    check_float("resistor_divider2() v_out3", circuit.get_variable("v_out3"), 1)
    check_float("resistor_divider2() v_out4", circuit.get_variable("v_out4"), 0.5)


def resistor_parallel(options):
    circuit = """
        R   vcc     v_out1      300
        R   v_out1  v_out2      1k
        R   v_out1  v_out2      2k
        R   v_out1  v_out2      3k
        R   v_out1  v_out2      4k
        R   v_out2  gnd         500
    
        vcc = 5
        """
    circuit = circuit_sim.Circuit.build_from_string(circuit)
    circuit.dc_analysis(options)

    check_float("resistor_parallel() v_out1", circuit.get_variable("v_out1"), 3.83)
    check_float("resistor_parallel() v_out2", circuit.get_variable("v_out2"), 1.95)


def vs_anchored(options):
    circuit = """
        VS  vcc     gnd         5V
        R   vcc     v_out1      300
        R   v_out1  v_out2      1k
        R   v_out1  v_out2      2k
        R   v_out1  v_out2      3k
        R   v_out1  v_out2      4k
        R   v_out2  gnd         500
        """
    circuit = circuit_sim.Circuit.build_from_string(circuit)
    circuit.dc_analysis(options)

    check_float("vs_anchored() v_out1", circuit.get_variable("v_out1"), 3.83)
    check_float("vs_anchored() v_out2", circuit.get_variable("v_out2"), 1.95)


def vs_floating(options):
    circuit = """
        VS  vcc     v_rtn       5v
        R   v_rtn   gnd         100
        
        R   vcc     v_out1      300
        R   v_out1  v_out2      1k
        R   v_out1  v_out2      2k
        R   v_out1  v_out2      3k
        R   v_out1  v_out2      4k
        R   v_out2  gnd         500
        """
    circuit = circuit_sim.Circuit.build_from_string(circuit)
    circuit.dc_analysis(options)

    check_float("vs_floating() v_out1", circuit.get_variable("v_out1"), 3.55)
    check_float("vs_floating() v_out2", circuit.get_variable("v_out2"), 1.81)
    check_float("vs_floating() v_rtn", circuit.get_variable("v_rtn"), -0.362)


def vs_stacked(options):
    circuit = """
        VS  vcc     vs1         2V
        VS  vs1     vs2         1.5
        VS  vs2     gnd         2.5 
        
        R   vcc     v_out1      300
        R   v_out1  v_out2      1k
        R   v_out1  v_out2      2k
        R   v_out1  v_out2      3k
        R   v_out1  v_out2      4k
        R   v_out2  gnd         500
        """
    circuit = circuit_sim.Circuit.build_from_string(circuit)
    circuit.dc_analysis(options)

    check_float("vs_stacked() v_out1", circuit.get_variable("v_out1"), 4.59)
    check_float("vs_stacked() v_out2", circuit.get_variable("v_out2"), 2.34)


def vs_stacked_and_floating(options):
    circuit = """
        VS  vcc     vs1         2V
        VS  vs1     vs2         1.5
        VS  vs2     v_rtn       2.5 
        R   v_rtn   gnd         200
    
        R   vcc     v_out1      300
        R   v_out1  v_out2      1k
        R   v_out1  v_out2      2k
        R   v_out1  v_out2      3k
        R   v_out1  v_out2      4k
        R   v_out2  gnd         500
        """
    circuit = circuit_sim.Circuit.build_from_string(circuit)
    circuit.dc_analysis(options)

    check_float("vs_stacked_and_floating() v_out1", circuit.get_variable("v_out1"), 3.97)
    check_float("vs_stacked_and_floating() v_out2", circuit.get_variable("v_out2"), 2.03)


def diode_minus_side_fixed(options):
    circuit = """
        R           vcc     v1      0.1
        D my_diode  v1      gnd     i0=1e-5 m=3 v0=0.5

        vcc = 5v 
        """
    circuit = circuit_sim.Circuit.build_from_string(circuit)
    circuit.dc_analysis(options)

    check_float("diode_minus_side_fixed() v1", circuit.get_variable("v1"), 4.702)
    check_float("diode_minus_side_fixed() my_diode.current", circuit.get_variable("my_diode.current"), 2.982)


def diode_plus_side_fixed(options):
    circuit = """
        D my_diode  vcc     v1      i0=1e-5 m=3 v0=0.5
        R           v1      gnd     0.1

        vcc = 5v 
        """
    circuit = circuit_sim.Circuit.build_from_string(circuit)
    circuit.dc_analysis(options)

    check_float("diode_plus_side_fixed() v1", circuit.get_variable("v1"), 0.298)
    check_float("diode_plus_side_fixed() my_diode.current", circuit.get_variable("my_diode.current"), 2.982)


def diode_both_sides_floating(options):
    circuit = """
        R           vcc     v1      0.03
        D my_diode  v1      v2      i0=1e-5 m=3 v0=0.5
        R           v2      gnd     0.07

        vcc = 5v 
        """
    circuit = circuit_sim.Circuit.build_from_string(circuit)
    circuit.dc_analysis(options)

    check_float("diode_both_sides_floating() v1", circuit.get_variable("v1"), 4.911)
    check_float("diode_both_sides_floating() v2", circuit.get_variable("v2"), 0.208)
    check_float("diode_both_sides_floating() my_diode.current", circuit.get_variable("my_diode.current"), 2.982)


def cap_dc(options):
    circuit = """
            R       vcc     v_out1      500
            R       v_out1  v_out2      1000
            R       v_out2  gnd         2000
            C       v_out1  v_out2      10uF

            vcc = 3.5v
            """
    circuit = circuit_sim.Circuit.build_from_string(circuit)
    circuit.dc_analysis(options)

    check_float("cap_dc() v_out1", circuit.get_variable("v_out1"), 3)
    check_float("cap_dc() v_out2", circuit.get_variable("v_out2"), 2)


def inductor_dc(options):
    circuit = """
            R       vcc     v_out1      500
            R       v_out1  v_out2      1000
            R       v_out2  gnd         2000
            L       v_out1  v_out2      10uH

            vcc = 2.5v
            """
    circuit = circuit_sim.Circuit.build_from_string(circuit)
    circuit.dc_analysis(options)

    check_float("inductor_dc() v_out1", circuit.get_variable("v_out1"), 2)
    check_float("inductor_dc() v_out2", circuit.get_variable("v_out2"), 2)


def run_all_tests():
    print("Running test_dc.py :: run_all_tests()")

    for options_str in ["dense", "sparse"]:
        # R tests
        resistor_divider(options_str)
        resistor_divider2(options_str)
        resistor_parallel(options_str)

        # VS tests
        vs_anchored(options_str)
        vs_floating(options_str)
        vs_stacked(options_str)
        vs_stacked_and_floating(options_str)

        # D tests
        diode_minus_side_fixed(options_str)
        diode_plus_side_fixed(options_str)
        diode_both_sides_floating(options_str)

        # C test
        cap_dc(options_str)

        # L test
        inductor_dc(options_str)



if __name__ == "__main__":
    run_all_tests()

