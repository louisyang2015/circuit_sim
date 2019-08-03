import math, numpy

import circuit_sim.IComponent as IComponent

from . StringCircuitBuilder import StringCircuitBuilder
from . ILinearSystem import ILinearSystem
from . IComponent import AnalysisDescription, AnalysisModes


class CircuitComponents:
    def __init__(self, list_of_components: list, voltage_constants: dict):
        self.all_components = list_of_components
        self.__voltage_constants = voltage_constants

        # lists for components that require special treatment
        self.constant_voltages = []
        self.non_linear = []
        self.lc = []
        self.modified = []

        # mapping from variable name to index
        self.variable_names_dict = {} # name to index
        self.variable_names_list = [] # index to name

        # for looking up components by name
        self.components_dict = {} # name to component object

        # generate names as needed
        _id = 0
        for c in list_of_components:
            _id = c.generate_name(_id)

        # check that all components have unique names
        all_names = set()
        for c in list_of_components:
            if c.get_name() in all_names:
                raise Exception("The component name \"" + c.name
                                + "\" is used more than once.")
            else:
                all_names.add(c.get_name())

        # collect components that require special treatment into lists
        for c in list_of_components:
            if type(c) is IComponent.VS: self.constant_voltages.append(c)
            elif type(c) is IComponent.Diode: self.non_linear.append(c)

            elif (type(c) is IComponent.C) or (type(c) is IComponent.L):
                self.lc.append(c)

        # resolve voltage_constants for voltage sources
        changes_found = True
        while changes_found:
            changes_found = False
            for c in self.constant_voltages:
                change = c.resolve_constants(voltage_constants)
                if change:
                    changes_found = True

        # resolve all voltage_constants for components
        for c in self.all_components:
            c.resolve_constants(voltage_constants)

        # Collect variable names, building up "variable_names_dict"
        # and "components_dict"
        var_name_index = 0

        for c in list_of_components:
            name = c.get_name()
            if name.startswith('$') == False:
                self.components_dict[name] = c

            var_names = c.get_variable_names()
            for var_name in var_names:
                if var_name not in self.variable_names_dict:
                    self.variable_names_dict[var_name] = var_name_index
                    var_name_index += 1

        # Now build up "variable_names_list"
        self.variable_names_list = [''] * len(self.variable_names_dict)

        for var_name, index in self.variable_names_dict.items():
            self.variable_names_list[index] = var_name


    def sum_non_linear_error(self, x: numpy.ndarray):
        """Total the dc bias error for the "non_linear" components."""
        err = 0
        for c in self.non_linear:
            err += abs(c.calculate_dc_bias_error(x, self.variable_names_dict))

        return err



class Circuit:
    def __init__(self, list_of_components: list, voltage_constants: dict):
        """
        :param voltage_constants: something like {"gnd": 0}
        """
        self.__circuit_components = CircuitComponents(
            list_of_components, voltage_constants)

        self.__linear_system = None

        # transient simulation member variables, so to support
        # "continue_transient_simulation(...)"
        self.__t = 0 # current transient simulation time
        self.__start_record_time = 0
        self.__var_list_index = [] # indices of "x" vector to be recorded

        self.__time_stamps = []
        self.__results = []


    @staticmethod
    def build_from_string(circuit_description: str):
        """Builds a circuit from a custom circuit description
        language."""
        circuit_builder = StringCircuitBuilder(circuit_description)

        return Circuit(circuit_builder.list_of_components,
                       circuit_builder.voltage_constants)


    def print_equations(self):
        """Prints the Ax=b equations."""
        if self.__linear_system is None:
            print("Nothing to print.")
            return

        A = self.__linear_system.A
        b = self.__linear_system.b
        var_names = self.__circuit_components.variable_names_list

        for row in range(0, A.shape[0]):
            first_item = True

            for col in range(0, A.shape[1]):
                if A[row, col] != 0:
                    if first_item is False:
                        print("+ ", end="")

                    print("(" + str(A[row, col]) + ")(" + var_names[col] + ") ",
                          end="")

                    first_item = False

            print("= " + str(b[row]))


    def print_all_variables(self):
        if self.__linear_system is None:
            print("Nothing to print.")
            return

        x = self.__linear_system.x
        if x is None:
            print("There's nothing to print.")
            return

        var_names = self.__circuit_components.variable_names_list
        for i in range(0, len(x)):
            print(var_names[i], "=", x[i])


    def get_variable(self, var_name: str):
        x = self.__linear_system.x
        variable_names = self.__circuit_components.variable_names_dict
        return x[variable_names[var_name]]


    def get_component_for_modification(self, component_name: str):
        """Return the component. This component will be put on the
        "modified" list, so that on continue_xxx(...) simulation calls,
        the component will re-stamp the Ax=b linear system.

        :return: returns None if no such component is found
        """
        if component_name in self.__circuit_components.components_dict:
            component = self.__circuit_components.components_dict[component_name]
            self.__circuit_components.modified.append(component)
            return component

        else:
            return None


    def solve(self, analysis_description: AnalysisDescription,
              max_iter=40, debug=False):
        """ This solve(...) routine is shared among different analysis
        types. The routine calls "self.__linear_system.solve()" iteratively
        to reduce errors from non-linear components.

        :param analysis_description: this controls how the Ax=b system is
            de-stamped and re-stamped for each solution iteration
        :param max_iter: maximum iteration in attempting to converge for
            non-linear components
        :param debug: enable debug printing
        """
        variable_names = self.__circuit_components.variable_names_dict

        # initial solution attempt
        self.__linear_system.solve()

        # additional solve attempts, for non-linear components (such as the diode)
        num_iter = 0

        while num_iter < max_iter:
            # compute dc analysis error due to non-linearity
            err = self.__circuit_components.sum_non_linear_error(self.__linear_system.x)
            if debug: print("Error due to non-linearity:", err)

            # decide if the "err" is sufficiently small
            norm = sum(abs(self.__linear_system.x))
            # This is using 1-norm
            # Alternatively use 2-norm: numpy.linalg.norm(x)

            max_err = norm * 1e-3
            if max_err < 1e-6: max_err = 1e-6

            if err < max_err:
                if debug: print("Number of iterations:", num_iter)
                return

            # Code arrive here if the DC non-linear error is too great

            for c in self.__circuit_components.non_linear:
                # For each non-linear component,
                # update internal bias point and re-stamp the Ax=b system
                c.update_state(self.__linear_system.x, variable_names)
                c.update_linear_system(self.__linear_system, variable_names,
                                       analysis_description)

            # Recompute a DC solution
            self.__linear_system.solve()
            num_iter += 1

        # Code arrive here after unable to reduce DC bias error after
        # "max_iter"
        raise Exception("Unable to converge to a circuit solution due "
                        + "to error from non-linear components.")


    def dc_analysis(self, options="dense", max_iter=40, debug=False):
        """

        :param options: linear algebra options implemented by
            ILinearSystem, such as "dense" or "sparse".
        """
        num_variables = len(self.__circuit_components.variable_names_list)
        self.__linear_system = ILinearSystem.create(num_variables,
                                                    numpy.float64, options)
        analysis_description = AnalysisDescription()
        analysis_description.mode = AnalysisModes.DC

        variable_names = self.__circuit_components.variable_names_dict

        for c in self.__circuit_components.all_components:
            c.init_linear_system(self.__linear_system,
                                 variable_names,
                                 analysis_description)

        self.solve(analysis_description, max_iter, debug)


    def transient_simulation(self, start_record_time: float, end: float, var_list: list,
                             time_step=None, options="dense", max_iter=40,
                             debug=False):
        """ returns time_stamps, results. The "results" is a list
        of lists. So "results[0]" is a list of the first variable
        being recorded.

        :param start_record_time: start recording data at this time
        :param end: stop simulation at this time
        :param var_list: variable names to record
        :param time_step: simulation speed
        :param options: linear algebra options implemented by
            ILinearSystem, such as "dense" or "sparse".
        :param max_iter: this refers to the DC circuit solution that
            happens at each time step. This is the maximum iteration
            in attempting to converge for non-linear components.
        :param debug: enable debug printing
        :return: time_stamps, results
        """
        self.__t = 0
        self.__start_record_time = start_record_time
        self.__time_stamps = []

        # default to collecting 1024 points
        if time_step is None:
            time_step = (end - start_record_time) / 1024

        variable_names = self.__circuit_components.variable_names_dict

        # The var_list is a list of string variable names
        # Build var_list_index - a list of indices, to know where in
        # the solution "x" to find the variables
        self.__var_list_index = []
        for var_name in var_list:
            self.__var_list_index.append(variable_names[var_name])

        self.__results = []
        # "results" is a list of lists
        # "results[3]" will correspond to the variable "var_list[3]"
        for _ in range(0, len(self.__var_list_index)):
            self.__results.append([])

        # set up analysis description
        analysis_description = AnalysisDescription()
        analysis_description.mode = AnalysisModes.Transient
        analysis_description.time_step = time_step

        # initial setup of Ax=b
        num_variables = len(self.__circuit_components.variable_names_list)
        self.__linear_system = ILinearSystem.create(num_variables,
                                                    numpy.float64, options)

        for c in self.__circuit_components.all_components:
            c.init_linear_system(self.__linear_system,
                                 variable_names,
                                 analysis_description)

        run_time = end - 0

        # use "continue_transient_simulation()" to run transient simulation
        self.continue_transient_simulation(run_time, time_step,
                                           max_iter, debug)
        return self.__time_stamps, self.__results


    def continue_transient_simulation(self, run_time: float, time_step=None,
                                      max_iter=40, debug=False):
        """Continue running the transient simulation, using existing settings.

        :param time_step: the "time_step" is not the same as before. If this
            is not provided, it is recalculated.
        :return: time_stamps, results
        """
        end_time = self.__t + run_time

        # default to collecting 1024 points
        if time_step is None:
            start_record_time = max(self.__t, self.__start_record_time)
            time_step = (end_time - start_record_time) / 1024

        # set up analysis description
        analysis_description = AnalysisDescription()
        analysis_description.mode = AnalysisModes.Transient
        analysis_description.time_step = time_step

        variable_names = self.__circuit_components.variable_names_dict

        # re-stamp any modified components
        for c in self.__circuit_components.modified:
            c.update_linear_system(self.__linear_system, variable_names,
                                   analysis_description)

        self.__circuit_components.modified.clear()

        # The current simulation advances the time (self.__t) to
        # "end_time", but does not actually record data at end_time.
        # In other words, each simulation does not include the final
        # data point - that data point will be included in the next
        # "continue_transient_simulation(...)" call.
        while self.__t < end_time:
            self.solve(analysis_description, max_iter, debug)
            x = self.__linear_system.x

            # collect data from simulation
            if self.__start_record_time <= self.__t:
                self.__time_stamps.append(self.__t)
                for i in range(0, len(self.__var_list_index)):
                    var_index = self.__var_list_index[i]
                    self.__results[i].append(x[var_index])

            # update the LC components
            for c in self.__circuit_components.lc:
                c.update_state(self.__linear_system.x, variable_names)
                c.update_linear_system(self.__linear_system, variable_names,
                                       analysis_description)

            # Simulation needs to run exactly as long as specified. The
            # time_steps can be manually provided, so simply adding the same
            # time steps on each iteration might not result in the simulation
            # ending at the exact "end_time".

            # On the last two simulation cycles, manually adjust the
            # time_steps.
            if self.__t + 2 * time_step < end_time:
                # All situations besides the last two time steps
                # use the standard time stepping
                self.__t += time_step

            elif self.__t + time_step >= end_time:
                # final time step
                analysis_description.time_step = end_time - self.__t
                self.__t = end_time

            else:
                # the second last time step
                # step half of the remaining time
                second_last_step = (end_time - self.__t) / 2
                analysis_description.time_step = second_last_step
                self.__t += second_last_step

        return self.__time_stamps, self.__results


    def clear_transient_simulation_data(self):
        self.__time_stamps.clear()
        for a_list in self.__results:
            a_list.clear()

    def get_transient_simulation_time(self):
        return self.__t

    def ac_sweep(self, var_list: list, start_freq=1,
                 stop_freq=1e6, num_data_points=512, log_scale=True,
                 options="dense", max_iter=40,
                 debug=False):
        """Runs an AC sweep analysis. Returns freq, results.
        The "freq" is in Hz. The "results" is a list of lists,
        so that "results[1]" corresponds to "var_list[1]".

        :param var_list: list of variable names to record
        :param start_freq: start_record_time frequency, in Hz
        :param stop_freq: stop frequency, in Hz
        :param num_data_points: number of data points
        :param log_scale: if False, a linear scale will be used
        :param options: linear algebra options implemented by
            ILinearSystem, such as "dense" or "sparse".
        :param max_iter: this refers to the DC circuit solution that
            happens at each time step. This is the maximum iteration
            in attempting to converge for non-linear components.
        :param debug: enable debug printing
        :return: freq, results
        """
        variable_names = self.__circuit_components.variable_names_dict

        # generate the frequency data points
        if log_scale:
            start_power = math.log10(start_freq)
            stop_power = math.log10(stop_freq)
            freq = numpy.logspace(start_power, stop_power, num_data_points)
        else:
            # linear scale
            freq = numpy.linspace(start_freq, stop_freq, num_data_points)

        freq = list(freq) # to satisfy IDE type checking

        # The var_list is a list of string variable names
        # Build var_list_index - a list of indices, to know where in
        # the solution "x" to find the variables
        var_list_index = []
        for var_name in var_list:
            var_list_index.append(variable_names[var_name])

        # "results" is a list of lists
        # "results[3]" will correspond to the variable "var_list[3]"
        results = []
        for _ in range(0, len(var_list_index)):
            results.append([])

        # set up analysis description
        analysis_description = AnalysisDescription()
        analysis_description.mode = AnalysisModes.AC_Sweep
        analysis_description.w = freq[0]

        # initial setup of Ax=b
        num_variables = len(self.__circuit_components.variable_names_list)
        self.__linear_system = ILinearSystem.create(num_variables,
                                                    numpy.complex128, options)

        for c in self.__circuit_components.all_components:
            c.init_linear_system(self.__linear_system,
                                 variable_names,
                                 analysis_description)

        for f in freq:
            # Update frequency to the __value used in the current loop pass,
            # and then reapply the element stamps
            analysis_description.w = f * 2 * math.pi

            for c in self.__circuit_components.lc:
                c.update_linear_system(self.__linear_system, variable_names,
                                       analysis_description)

            # solve circuit
            self.solve(analysis_description, max_iter, debug)
            x = self.__linear_system.x

            # collect data
            for i in range(0, len(results)):
                results[i].append(x[var_list_index[i]])

        return freq, results

