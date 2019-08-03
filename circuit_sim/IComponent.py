import math, numpy
from . ILinearSystem import ILinearSystem



class AnalysisModes:
    """Enumeration of analysis modes."""
    DC = 0
    Transient = 1
    AC_Sweep = 2


class AnalysisDescription:
    """Analysis description information."""
    def __init__(self):
        self.mode = AnalysisModes.DC
        self.time_step = 1e-6
        self.w = 1


class IComponent:
    """Base class of all circuit components"""

    def __init__(self, node1: str, node2: str, name: str):
        """ This constructor will check "name" for naming rule violations.
        :param name:  this can be None
        """
        self.node1 = node1
        self.node2 = node2

        # All components have a name. The default is none. If the
        # name is none, a "$number" name will be assigned later.
        self.__name = name
        if name is None: return
        else: self.check_name(name)


    @staticmethod
    def check_name(name: str):
        """Check the "name" for naming convention violations. If "name"
        has a problem, raise an exception."""

        # name cannot start_record_time with $ and cannot contain '.'
        if name.startswith('$'):
            raise Exception("The name \"" + name + "\" is illegal because " +
                            "it starts with a '$'")

        if name.find('.') >= 0:
            raise Exception("The name \"" + name + "\" is illegal because " +
                            "it contains a '.'")


    def generate_name(self, _id: int):
        """If "name" is None, generate one based on the provided "_id"."""
        if self.__name is None:
            self.__name = "$" + str(_id)
            _id += 1

        return _id

    def get_name(self):
        return self.__name

    def resolve_constants(self, voltage_constants: dict):
        """ Resolve "node1" and "node2" if found inside "voltage_constants".
        Returns "true" if "voltage_constants" is modified in the process.
        :param voltage_constants: something like {"gnd": 0}
        """
        if self.node1 in voltage_constants:
            self.node1 = voltage_constants[self.node1]

        if self.node2 in voltage_constants:
            self.node2 = voltage_constants[self.node2]

        return False


    def get_variable_names(self):
        """Return variable names used in the Ax=b system of equations."""
        var_names = []
        if type(self.node1) is str: var_names.append(self.node1)
        if type(self.node2) is str: var_names.append(self.node2)
        return var_names


    def read_node1_and_node2_as_indices(self, variable_names: dict):
        """ Node1 and node2 can be variable name or actual values. This
        function returns "v1, v1_is_variable, v2, v2_is_variable". The
        "v1" is the actual __value of "v1", or an index __value that can be
        used to access the Ax=b system.

        :param variable_names: maps a string variable name to an integer index
            that can be used to access the Ax=b system.
        :return: v1, v1_is_variable, v2, v2_is_variable
        """
        if type(self.node1) is str:
            v1 = variable_names[self.node1]
            v1_is_variable = True
        else:
            v1 = self.node1
            v1_is_variable = False

        if type(self.node2) is str:
            v2 = variable_names[self.node2]
            v2_is_variable = True
        else:
            v2 = self.node2
            v2_is_variable = False

        return v1, v1_is_variable, v2, v2_is_variable


    def read_node1_and_node2_as_values(self, x: numpy.ndarray, variable_names: dict):
        """Return node1 and node2 as values. If they are variable names, then
        their values will be read from the "x" array.

        :param variable_names: maps a string variable name to an integer index
            that can be used to access the Ax=b system.
        :return: v1, v2
        """
        # get v1
        if type(self.node1) is str:
            v1 = x[variable_names[self.node1]]
        else:
            v1 = self.node1

        # get v2
        if type(self.node2) is str:
            v2 = x[variable_names[self.node2]]
        else:
            v2 = self.node2

        return v1, v2


    def init_linear_system(self, linear_system: ILinearSystem,
                           variable_names: dict,
                           analysis_description: AnalysisDescription):
        """Initialize the Ax=b system of equations. This should be
        called when "linear_system" contains brand new "A" and "b" matrices.

        :param variable_names: maps from string name to integer index
        """
        raise Exception("IComponent::init_linear_system(...) not implemented")


    def update_linear_system(self, linear_system: ILinearSystem,
                             variable_names: dict,
                             analysis_description: AnalysisDescription):
        """Initialize the Ax=b system of equations. This should be
        called when "linear_system" contains old information that
        does not reflect current component values.

        :param variable_names: maps from string name to integer index
        """
        raise Exception("IComponent::update_linear_system(...) not implemented")


    def update_state(self, x: numpy.ndarray, variable_names: dict, t=0):
        """During transient analysis, update the internal state of
        components that has internal state variables, such as
        capacitors and inductors."""
        raise Exception("IComponent::update_state(...) not implemented")

    def calculate_dc_bias_error(self, x: numpy.ndarray, variable_names: dict):
        """During nonlinear dc analysis, return the error of the current
         IV estimation. """
        return 0


class R(IComponent):
    """Model for a resistor."""

    def __init__(self, node1: str, node2: str, value: float, name=None):
        super().__init__(node1, node2, name)
        self.value = value      # current __value
        self.__old_value = None # __value in use


    def apply_element_stamps(self, linear_system: ILinearSystem,
                           variable_names: dict, partial_undo=False):
        """Apply element stamps to linear system.

        :param partial_undo: Reverse some of the element stamps previously
            made, using "old_value". This is not a total undo - only
            increment / decrement fields are reversed. Fields that
            will be overwritten are left unchanged.
        """
        if partial_undo:
            value = self.__old_value
            modifier = -1
        else:
            value = self.value
            modifier = 1

        A = linear_system.A
        b = linear_system.b
        one_over_R = 1 / value

        v1, v1_is_variable, v2, v2_is_variable = self.read_node1_and_node2_as_indices(variable_names)

        # current contribution for node1
        if v1_is_variable:
            A[v1, v1] += (one_over_R * modifier)

            if v2_is_variable:
                A[v1, v2] += (-1 * one_over_R * modifier)
            else:
                b[v1] += (v2 * one_over_R * modifier)

        # current contribution for node2
        if v2_is_variable:
            A[v2, v2] += (one_over_R * modifier)

            if v1_is_variable:
                A[v2, v1] += (-1 * one_over_R * modifier)
            else:
                b[v2] += (v1 * one_over_R * modifier)


    def init_linear_system(self, linear_system: ILinearSystem,
                           variable_names: dict,
                           analysis_description: AnalysisDescription):
        # make a backup
        self.__old_value = self.value

        self.apply_element_stamps(linear_system, variable_names)


    def update_linear_system(self, linear_system: ILinearSystem,
                             variable_names: dict,
                             analysis_description: AnalysisDescription):
        """Update the Ax=b linear system after a change of "__value"."""
        self.apply_element_stamps(linear_system, variable_names, partial_undo=True)
        self.init_linear_system(linear_system, variable_names, analysis_description)


class VS(IComponent):
    """Model for an independent constant voltage source."""
    def __init__(self, node1: str, node2: str, value: float, name=None):
        super().__init__(node1, node2, name)
        self.__value = value
        self.__current_var_name = None
        self.__disabled = False


    def generate_name(self, _id: int):
        """Generate a name for the internal current variable."""
        _id = super().generate_name(_id)
        self.__current_var_name = self.get_name() + ".current"
        return _id

    def resolve_constants(self, voltage_constants: dict):
        """ Resolve "node1" and "node2" if found inside "voltage_constants".
        Returns "true" if "voltage_constants" is modified in the process.
        :param voltage_constants: something like {"gnd": 0}
        """
        # check for data consistency if both nodes are constants
        if (type(self.node1) is not str) and (type(self.node1) is not str):
            if abs(self.node1 - self.node2 - self.__value) > 1e-6:
                raise Exception("The values in voltage source \"" + self.get_name()
                                + "\" are inconsistent. Node1 is " + str(self.node1)
                                + ", node2 is " + str(self.node2), " and __value is "
                                + str(self.__value))
            else:
                return False

        # if either node is a constant, the other node is also a constant
        if self.node1 in voltage_constants:
            self.node1 = voltage_constants[self.node1]
            node2_name = self.node2
            self.node2 = self.node1 - self.__value
            voltage_constants[node2_name] = self.node2

            self.__disabled = True
            return True # "voltage_constants" has been modified

        if self.node2 in voltage_constants:
            self.node2 = voltage_constants[self.node2]
            node1_name = self.node1
            self.node1 = self.node2 + self.__value
            voltage_constants[node1_name] = self.node1

            self.__disabled = True
            return True # "voltage_constants" has been modified


    def get_variable_names(self):
        if self.__disabled: return []

        var_names = super().get_variable_names()
        var_names.append(self.__current_var_name)
        return var_names


    def init_linear_system(self, linear_system: ILinearSystem,
                           variable_names: dict,
                           analysis_description: AnalysisDescription):
        # If one end of the VS is a constant, then both ends will
        # become constant, and this component would be optimized out.
        if self.__disabled: return

        # If the code gets here, that means both node1 and node2
        # are voltage node variables, not constant voltage values.
        A = linear_system.A
        b = linear_system.b
        v1 = variable_names[self.node1]
        v2 = variable_names[self.node2]
        i = variable_names[self.__current_var_name]

        # current contribution for node1
        A[v1, i] += -1

        # current contribution for node2
        A[v2, i] += 1

        # additional equation
        A[i, v1] = 1
        A[i, v2] = -1
        b[i] = self.__value


    def update_linear_system(self, linear_system: ILinearSystem,
                             variable_names: dict,
                             analysis_description: AnalysisDescription):
        """Re-initialize the Ax=b system if the __value of the voltage
        source has changed."""
        if self.__disabled: return

        b = linear_system.b
        i = variable_names[self.__current_var_name]

        b[i] = self.__value



class Diode(IComponent):
    def __init__(self, node1: str, node2: str, i0: float, m: float,
                 v0: float, name=None):
        super().__init__(node1, node2, name)
        # model variables
        self.__v0 = v0
        self.__i0 = i0
        self.__m = m

        # additional Ax=b variables, in addition to "node1" and "node2"
        self.__current_var_name = None
        self.__internal_node_name = None

        # operating condition
        self.__v_bias = 0



    def generate_name(self, _id: int):
        _id = super().generate_name(_id)

        # generate the "current_var_name" and "internal_node_name"
        self.__current_var_name = self.get_name() + ".current"
        self.__internal_node_name = self.get_name() + ".internal_node"

        return _id


    def get_variable_names(self):
        var_names = super().get_variable_names()
        var_names += [self.__internal_node_name, self.__current_var_name]
        return var_names


    def calculate_dc_bias_error(self, x: numpy.ndarray, variable_names: dict):
        """Returns error in current solution."""
        if x is None:
            raise Exception("Diode::calculate_dc_bias_error(...) called "
                            + "without circuit information.")

        v1, v2 = self.read_node1_and_node2_as_values(x, variable_names)
        voltage = v1 - v2
        current = x[variable_names[self.__current_var_name]]

        # calculate error
        current2 = self.__i0 * math.exp(self.__m * (voltage - self.__v0))
        return current2 - current


    def update_state(self, x: numpy.ndarray, variable_names: dict, t=0):
        """Update the "v_bias" operating condition."""
        v1, v2 = self.read_node1_and_node2_as_values(x, variable_names)
        voltage = v1 - v2

        # "voltage" is the current operating condition
        # adjust "v_bias"; limit step size
        v_bias = self.__v_bias
        if voltage > v_bias + 0.3:
            v_bias += 0.3
        elif voltage < v_bias - 0.3:
            v_bias -= 0.3
        else:
            v_bias = voltage

        self.__v_bias = v_bias


    def apply_component_only_stamps(self, linear_system: ILinearSystem,
                                    variable_names: dict):
        """These stamps should be used only by this diode. Therefore
        these can be simply overwritten if v_bias changes."""
        A = linear_system.A
        b = linear_system.b

        # Diode model parameters:
        i0 = self.__i0
        m = self.__m
        v0 = self.__v0
        v_bias = self.__v_bias

        i_bias = i0 * math.exp(m * (v_bias - v0))
        i_derivative = i_bias * m
        v = i_bias / i_derivative
        v_offset = v_bias - v

        # extract node values and variable indices
        v1, v1_is_variable, v2, v2_is_variable = self.read_node1_and_node2_as_indices(variable_names)

        v_int = variable_names[self.__internal_node_name]
        i = variable_names[self.__current_var_name]

        ############################################
        # Apply element stamps

        # Current balance at internal node
        A[v_int, i] = -1
        A[v_int, v_int] = i_derivative

        if v2_is_variable:
            A[v_int, v2] = -1 * i_derivative
            b[v_int] = 0
        else:
            b[v_int] = v2 * i_derivative

        # Additional equation - for v_offset
        A[i, v_int] = -1

        if v1_is_variable:
            A[i, v1] = 1
            b[i] = v_offset
        else:
            b[i] = v_offset - v1


    def init_linear_system(self, linear_system: ILinearSystem,
                           variable_names: dict,
                           analysis_description: AnalysisDescription):
        A = linear_system.A
        i = variable_names[self.__current_var_name]
        v1, v1_is_variable, v2, v2_is_variable = self.read_node1_and_node2_as_indices(variable_names)

        # Current contribution at node1
        if v1_is_variable:
            A[v1, i] += 1

        # Current contribution at node2
        if v2_is_variable:
            A[v2, i] += -1

        self.apply_component_only_stamps(linear_system, variable_names)


    def update_linear_system(self, linear_system: ILinearSystem,
                             variable_names: dict,
                             analysis_description: AnalysisDescription):
        """Update the Ax=b linear system after a change of v_bias."""
        self.apply_component_only_stamps(linear_system, variable_names)


class C(IComponent):
    def __init__(self, node1: str, node2: str, value: float, v0=0.0, i0=0.0,
                 name=None):
        super().__init__(node1, node2, name)
        self.__value = value
        self.__current_var_name = None

        # capacitor state information
        self.__vcap = v0
        self.__icap = i0


    def generate_name(self, _id: int):
        _id = super().generate_name(_id)

        # generate the "current_var_name"
        self.__current_var_name = self.get_name() + ".current"
        return _id


    def get_variable_names(self):
        var_names = super().get_variable_names()
        var_names.append(self.__current_var_name)
        return var_names


    def update_state(self, x: numpy.ndarray, variable_names: dict, t=0):
        """Update "icap" and "vcap" with the information in "x". """
        v1, v2 = self.read_node1_and_node2_as_values(x, variable_names)
        i = variable_names[self.__current_var_name]

        self.__icap = x[i]
        self.__vcap = v1 - v2


    def apply_component_only_stamps(self, linear_system: ILinearSystem,
                                    variable_names: dict,
                                    analysis_description: AnalysisDescription):
        """These stamps should be used only by this capacitor. Therefore
        these can be simply overwritten."""
        A = linear_system.A
        b = linear_system.b

        v1, v1_is_variable, v2, v2_is_variable = self.read_node1_and_node2_as_indices(variable_names)
        i = variable_names[self.__current_var_name]

        # The capacitor equation at row "i" depends on the analysis mode.
        # The analysis mode can change. Some columns are used in one
        # analysis mode but not others. So set all possible matrix entries
        # to zero.
        if v1_is_variable: A[i, v1] = 0
        if v2_is_variable: A[i, v2] = 0
        A[i, i] = 0
        b[i] = 0

        if analysis_description.mode == AnalysisModes.Transient:
            dt_over_2c = analysis_description.time_step / (2 * self.__value)

            if v1_is_variable:
                A[i, v1] = 1
            else:
                b[i] -= v1

            if v2_is_variable:
                A[i, v2] = -1
            else:
                b[i] += v2

            A[i, i] = -1 * dt_over_2c

            b[i] += (dt_over_2c * self.__icap + self.__vcap)

        elif analysis_description.mode == AnalysisModes.AC_Sweep:
            cw = self.__value * analysis_description.w

            if v1_is_variable:
                A[i, v1] = complex(0, cw)
            else:
                b[i] += -1 * complex(0, cw) * v1

            if v2_is_variable:
                A[i, v2] = complex(0, -1 * cw)
            else:
                b[i] += complex(0, cw) * v2

            A[i, i] = -1

        elif analysis_description.mode == AnalysisModes.DC:
            # capacitor is open circuit in DC, with i = 0
            A[i, i] = 1
            b[i] = 0


    def init_linear_system(self, linear_system: ILinearSystem,
                           variable_names: dict,
                           analysis_description: AnalysisDescription):
        A = linear_system.A

        v1, v1_is_variable, v2, v2_is_variable = self.read_node1_and_node2_as_indices(variable_names)
        i = variable_names[self.__current_var_name]

        # current contribution for node1
        if v1_is_variable:
            A[v1, i] += 1

        # current contribution for node2
        if v2_is_variable:
            A[v2, i] += -1

        self.apply_component_only_stamps(linear_system, variable_names, analysis_description)


    def update_linear_system(self, linear_system: ILinearSystem,
                             variable_names: dict,
                             analysis_description: AnalysisDescription):
        self.apply_component_only_stamps(linear_system, variable_names, analysis_description)



class L(IComponent):
    def __init__(self, node1: str, node2: str, value: float, v0=0.0, i0=0.0,
                 name=None):
        super().__init__(node1, node2, name)
        self.__value = value
        self.__current_var_name = None

        # inductor state information
        self.__vL = v0
        self.__iL = i0


    def generate_name(self, _id: int):
        _id = super().generate_name(_id)

        # generate the "current_var_name"
        self.__current_var_name = self.get_name() + ".current"
        return _id


    def get_variable_names(self):
        var_names = super().get_variable_names()
        var_names.append(self.__current_var_name)
        return var_names


    def update_state(self, x: numpy.ndarray, variable_names: dict, t=0):
        """Update "iL" and "vL" with the information in "x". """
        v1, v2 = self.read_node1_and_node2_as_values(x, variable_names)
        i = variable_names[self.__current_var_name]

        self.__iL = x[i]
        self.__vL = v1 - v2


    def apply_component_only_stamps(self, linear_system: ILinearSystem,
                                    variable_names: dict,
                                    analysis_description: AnalysisDescription):
        """These stamps should be used only by this inductor. Therefore
        these can be simply overwritten."""
        A = linear_system.A
        b = linear_system.b

        v1, v1_is_variable, v2, v2_is_variable = self.read_node1_and_node2_as_indices(variable_names)
        i = variable_names[self.__current_var_name]

        # Set all possible matrix entries to zero.
        if v1_is_variable: A[i, v1] = 0
        if v2_is_variable: A[i, v2] = 0
        A[i, i] = 0
        b[i] = 0

        # additional equation - this depends on the analysis mode
        if analysis_description.mode == AnalysisModes.Transient:
            dt_over_2L = analysis_description.time_step / (2 * self.__value)

            if v1_is_variable:
                A[i, v1] = dt_over_2L
            else:
                b[i] -= dt_over_2L * v1

            if v2_is_variable:
                A[i, v2] = -1 * dt_over_2L
            else:
                b[i] += dt_over_2L * v2

            A[i, i] = -1

            b[i] += (-1 * dt_over_2L * self.__vL - self.__iL)


        elif analysis_description.mode == AnalysisModes.AC_Sweep:
            one_over_Lw = 1 / (self.__value * analysis_description.w)

            if v1_is_variable:
                A[i, v1] = complex(0, -1 * one_over_Lw)
            else:
                b[i] += complex(0, one_over_Lw) * v1

            if v2_is_variable:
                A[i, v2] = complex(0, one_over_Lw)
            else:
                b[i] += complex(0, -1 * one_over_Lw) * v2

            A[i, i] = -1

        elif analysis_description.mode == AnalysisModes.DC:
            # inductor is short circuit in DC, with v1 = v2
            if v1_is_variable:
                A[i, v1] = 1
            else:
                b += v1 * -1

            if v2_is_variable:
                A[i, v2] = -1
            else:
                b += v2


    def init_linear_system(self, linear_system: ILinearSystem,
                           variable_names: dict,
                           analysis_description: AnalysisDescription):
        A = linear_system.A

        v1, v1_is_variable, v2, v2_is_variable = self.read_node1_and_node2_as_indices(variable_names)
        i = variable_names[self.__current_var_name]

        # current contribution for node1
        if v1_is_variable:
            A[v1, i] += 1

        # current contribution for node2
        if v2_is_variable:
            A[v2, i] += -1

        self.apply_component_only_stamps(linear_system, variable_names, analysis_description)


    def update_linear_system(self, linear_system: ILinearSystem,
                             variable_names: dict,
                             analysis_description: AnalysisDescription):
        self.apply_component_only_stamps(linear_system, variable_names, analysis_description)



class VG(IComponent):
    """Model for an independent voltage source. The main difference between
    VG and VS is that VS will be optimized out (disabled) if one end
    of VS is a constant voltage, while VG will be retained."""

    def __init__(self, node1: str, node2: str, value: float, name=None):
        super().__init__(node1, node2, name)
        self.value = value
        self.__current_var_name = None

    def generate_name(self, _id: int):
        """Generate a name for the internal current variable."""
        _id = super().generate_name(_id)
        self.__current_var_name = self.get_name() + ".current"
        return _id


    def get_variable_names(self):
        var_names = super().get_variable_names()
        var_names.append(self.__current_var_name)
        return var_names


    def apply_component_only_stamps(self, linear_system: ILinearSystem,
                                    variable_names: dict):
        """These stamps should be used only by this VG. Therefore
        these can be simply overwritten if "__value" changes."""
        A = linear_system.A
        b = linear_system.b
        v1, v1_is_variable, v2, v2_is_variable = self.read_node1_and_node2_as_indices(variable_names)
        i = variable_names[self.__current_var_name]

        # initialization
        if v1_is_variable: A[i, v1] = 0
        if v2_is_variable: A[i, v2] = 0
        b[i] = 0

        # stamping
        if v1_is_variable: A[i, v1] = 1
        else: b[i] += -1 * v1

        if v2_is_variable: A[i, v2] = -1
        else: b[i] += v2

        b[i] += self.value


    def init_linear_system(self, linear_system: ILinearSystem,
                           variable_names: dict,
                           analysis_description: AnalysisDescription):
        # If one end of the VS is a constant, then both ends will
        # become constant, and this component would be optimized out.
        A = linear_system.A
        b = linear_system.b
        v1, v1_is_variable, v2, v2_is_variable = self.read_node1_and_node2_as_indices(variable_names)
        i = variable_names[self.__current_var_name]

        # current contribution for node1
        if v1_is_variable: A[v1, i] += -1

        # current contribution for node2
        if v2_is_variable: A[v2, i] += 1

        self.apply_component_only_stamps(linear_system, variable_names)


    def update_linear_system(self, linear_system: ILinearSystem,
                             variable_names: dict,
                             analysis_description: AnalysisDescription):
        """Re-initialize the Ax=b system if the __value of the voltage
        source has changed."""
        self.apply_component_only_stamps(linear_system, variable_names)
