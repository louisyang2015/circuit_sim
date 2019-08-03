"""
Decodes a string circuit description into a list of components
and voltage_constants.
"""

import circuit_sim.IComponent as IComponent

class StringCircuitBuilder:

    def __init__(self, circuit_description: str):
        self.list_of_components = []
        self.voltage_constants = {}

        for line in circuit_description.split("\n"):
            line = line.strip()

            # skip blank and comment lines
            if len(line) == 0: continue
            if line.startswith("#") or line.startswith("//") \
                    or line.startswith(";") or line.startswith("*"):
                continue

            try:
                # try to detect the line as a model
                if line.startswith("R "):
                    self.list_of_components.append(self.parse_R(line))
                elif line.startswith("VS "):
                    self.list_of_components.append(self.parse_VS(line))
                elif line.startswith("VG "):
                    self.list_of_components.append(self.parse_VG(line))
                elif line.startswith("D "):
                    self.list_of_components.append(self.parse_D(line))
                elif line.startswith("C "):
                    self.list_of_components.append(self.parse_C(line))
                elif line.startswith("L "):
                    self.list_of_components.append(self.parse_L(line))

                else:
                    # try to detect the line as a voltage reference
                    success = self.try_parse_as_voltage_constant(line)

                    if success == False:
                        raise Exception("Unknown syntax.")

            except Exception as ex:
                raise Exception("Failed to process the line \"" + line
                                + "\". " + str(ex))

        # check names for naming convention violation
        for c in self.list_of_components:
            if c.get_name() is not None:
                c.check_name(c.get_name())

        for k in self.voltage_constants:
            IComponent.IComponent.check_name(k)

        # always add in the "gnd = 0" reference for convenience
        if "gnd" not in self.voltage_constants:
            self.voltage_constants["gnd"] = 0.0


    def remove_ending(self, value: str, ending: str):
        """Removes "ending" from "__value" - if it exists. If "__value"
        does not have "ending", then the original "__value" string is
        returned.
        :param value: such as 10kOhm, or 10ohm
        :param ending: this should be provided in lower case
        :return: "__value" with the "ending" removed, or "__value"
        """
        length = len(ending)
        if len(value) < length: return value

        if value[-1*length:].lower() == ending:
            return value[:-1*length]
        else:
            return value


    def parse_value_ending(self, value: str):
        """ Returns the "__value" minus the ending character,
        and the power that ending character represents.
        :param value: such as "1k", "1K", or just "1"
        :return: __value, power
        """
        if len(value) < 1:
            raise Exception("Failed to parse the __value.")

        if value.endswith("T"):
            return value[:-1], 12
        if value.endswith("G"):
            return value[:-1], 9
        if value.endswith("M"):
            return value[:-1], 9
        if value.endswith("k") or value.endswith("K"):
            return value[:-1], 3
        if value.endswith("m"):
            return value[:-1], -3
        if value.endswith("u"):
            return value[:-1], -6
        if value.endswith("n"):
            return value[:-1], -9
        if value.endswith("p"):
            return value[:-1], -12

        return value, 0


    def parse_float_value(self, value: str):
        """Returns "__value" as a floating point."""
        value, power = self.parse_value_ending(value)
        try:
            value = float(value)
            return value * 10 ** power
        except:
            raise Exception("Failed to parse the __value.")


    def extract_parameters(self, tokens: list):
        """ Process tokens in the format of "m=2".

        :param tokens: A list of strings, each looking like "m=2"
        :return: A dictionary, for example {"m": 2}
        """
        results = {}

        for parameter in tokens:
            words = parameter.split('=')
            if len(words) != 2:
                raise Exception('Failed to break "' + parameter +
                                '" into a "name=__value" pair.')
            try:
                value = float(words[1])
                results[words[0]] = value
            except:
                raise Exception('Expecting ' + words[1]
                                + ' to be a floating point.')

        return results


    def extract_optional_parameters(self, tokens: list):
        """Starting at the final token and work the way to the front
        of the string. Returns index, parameters_dictionary. The
        index is the first token from the right that is NOT a
        parameter.

        :param tokens: list of strings
        :return: index, parameters_dictionary
        """
        parameters_dict = {}

        for i in range(len(tokens) - 1, -1, -1):
            possible_param = tokens[i]
            words = possible_param.split('=')
            if len(words) != 2:
                return i, parameters_dict
            else:
                try:
                    value = float(words[1])
                    parameters_dict[words[0]] = value
                except:
                    raise Exception('Expecting ' + words[1]
                                    + ' to be a floating point.')

        # code gets here if all tokens are parameters
        return 0, parameters_dict


    def check_parameter_existence(self, d: dict, params: list):
        """Check that the dictionary "d" has all the parameter names.
        Throws an exception for not finding all expected parameter names.

        :param d: something like {"m": 2}
        :param params: something like ["m"]
        """
        for param_name in params:
            if param_name not in d:
                raise Exception('Expecting the parameter "' + param_name
                                + '" but cannot find it.')


    def parse_two_node_component(self, line: str, optional_value_ending: str):
        """Parse the typical "model name node1 node2 __value" line.

        :param line: "model name node1 node2 __value"
        :param optional_value_ending: for resistor, this would be "ohm"
        :return: name, node1, node2, __value
        """

        # "line" can be:
        # R node1 node2 __value
        # R name node1 node2 __value
        tokens = line.split()

        if len(tokens) < 4 or len(tokens) > 5:
            raise Exception("Incorrect number of arguments.")

        # at this point, the number of tokens is either 4 or 5
        if len(tokens) == 4:
            name = None
            base = 1
        else:
            name = tokens[1]
            base = 2

        node1 = tokens[base]
        node2 = tokens[base+1]
        value = tokens[base+2]

        # parse the "__value" string
        value = self.remove_ending(value, optional_value_ending)
        value = self.parse_float_value(value)

        return name, node1, node2, value


    def parse_R(self, line: str):
        """Returns an "R" (resistor) object"""

        # R node1 node2 __value
        # R name node1 node2 __value
        name, node1, node2, value = self.parse_two_node_component(line,"ohm")
        return IComponent.R(node1, node2, value, name)


    def parse_VS(self, line: str):
        """Returns an "VS" (voltage source) object"""

        # VS node1 node2 __value
        # VS name node1 node2 __value
        name, node1, node2, value = self.parse_two_node_component(line,"v")
        return IComponent.VS(node1, node2, value, name)

    def parse_VG(self, line: str):
        """Returns an "VG" (voltage generator) object"""

        # VG node1 node2 __value
        # VG name node1 node2 __value
        name, node1, node2, value = self.parse_two_node_component(line,"v")
        return IComponent.VG(node1, node2, value, name)


    def parse_D(self, line):
        """Parse a diode circuit description line.

        :param line: "D name node1 node2 i0=val m=val v0=val"
        :return: a Diode object
        """
        # "line" can be:
        # D name node1 node2 i0=val m=val v0=val
        # D node1 node2 i0=val m=val v0=val
        tokens = line.split()

        if len(tokens) < 6 or len(tokens) > 7:
            raise Exception("Incorrect number of arguments.")

        # at this point, the number of tokens is either 6 or 7
        if len(tokens) == 6:
            name = None
            base = 1
        else:
            name = tokens[1]
            base = 2

        node1 = tokens[base]
        node2 = tokens[base + 1]

        # the parameters are at [base+2] to [base+4]
        parameters = self.extract_parameters(tokens[base+2 : base+5])
        self.check_parameter_existence(parameters, ["i0", "m", "v0"])

        return IComponent.Diode(node1, node2, parameters["i0"],
                                parameters["m"], parameters["v0"], name)


    def try_parse_as_voltage_constant(self, line: str):
        """Try to parse "line" as a voltage constant. If successful, the
        voltage constant is added to "self.voltage_constant". Returns a
        "success" flag.

        :param line: string like "gnd = 0"
        :return: True if line successfully processed as a voltage constant.
        """
        tokens = line.split()
        if len(tokens) != 3: return False
        if tokens[1] != "=": return False

        value = tokens[2]
        value = self.remove_ending(value, "v")
        value = self.parse_float_value(value)

        self.voltage_constants[tokens[0]] = value

        return True


    def parse_C_or_L(self, line: str, unit: str):
        """Handles a C (capacitor) or L (inductor) definition.

        :param line: something like "C name node1 node2 __value v0=0 i0=0"
        :param unit: "f" for capacitor and "h" for inductor
        :return: node1, node2, __value, v0, i0, name
        """
        # The C and L has a common syntax:
        # C name node1 node2 __value v0=0 i0=0
        # The name and the initial state parameters at the end are optional
        tokens = line.split()
        index, optional_params = self.extract_optional_parameters(tokens)

        # get "i0" and "v0" from "optional_params"
        i0 = 0
        if "i0" in optional_params: i0 = optional_params["i0"]

        v0 = 0
        if "v0" in optional_params: v0 = optional_params["v0"]

        # index should be 3 or 4
        if index < 3 or index > 4:
            raise Exception("Incorrect number of arguments.")

        if index == 4:
            name = tokens[1]
            base = 2
        else:
            name = None
            base = 1

        node1 = tokens[base]
        node2 = tokens[base + 1]
        value = tokens[base + 2]

        # parse the "__value" string
        value = self.remove_ending(value, unit)
        value = self.parse_float_value(value)

        return node1, node2, value, v0, i0, name


    def parse_C(self, line: str):
        """Returns a capacitor object"""
        node1, node2, value, v0, i0, name = self.parse_C_or_L(line, "f")
        return IComponent.C(node1, node2, value, v0, i0, name)


    def parse_L(self, line: str):
        """Returns an inductor object"""
        node1, node2, value, v0, i0, name = self.parse_C_or_L(line, "h")
        return IComponent.L(node1, node2, value, v0, i0, name)


