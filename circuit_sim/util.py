import bisect, cmath, math
import matplotlib.pyplot as pyplot


def interpolate(value, value_list: list, data_list: list):
    """Search for a "__value" in "value_list", then interpolate
    a result using the data in "data_list". The "value_list"
    is assumed to be sorted and a binary search is used."""

    if len(value_list) != len(data_list):
        raise Exception("interpolate(...) called using a __value list "
                        + "that differs in length from a data list.")

    index_right = bisect.bisect_left(value_list, value)

    if (index_right > 0) and (index_right < len(value_list)):
        # standard case - __value is in the middle of the list
        index_left = index_right - 1
        percent = (value - value_list[index_left]) / (value_list[index_right] - value_list[index_left])
        return data_list[index_left] + percent * (data_list[index_right] - data_list[index_left])

    elif index_right == 0:
        # __value is to the left of the list
        percent = (value_list[0] - value) / (value_list[1] - value_list[0])
        return data_list[0] - percent * (data_list[1] - data_list[0])

    elif index_right == len(value_list):
        last_index = len(value_list) - 1
        # __value is to the right of the list
        percent = (value - value_list[last_index]) / (value_list[last_index] - value_list[last_index-1])
        return data_list[last_index] + percent * (data_list[last_index] - data_list[last_index - 1])



def line_chart(x_label: str, data: list, legend_location=None):
    """Draws a line chart that can hold multiple lines.
    ::
        data[0] = x data
        data[1] = y data
        data[2] = graph title
        data[3] = x data, pattern repeats
    :param legend_location: This is the pyplot.legend(loc) parameter.
        It can be "upper left", "upper center", etc.
    """

    if len(data) > 15:
        raise Exception("Too many arguments given to my_line_chart().")

    # styles - for up to 5 lines
    line_styles = ["b-", "g-", "c-", "m-", "r-"]

    for i in range(0, len(data), 3):
        pyplot.plot(data[i], data[i + 1], line_styles[i // 3], label=data[i + 2])

    # legend location
    if legend_location is None:
        pyplot.legend()
    else:
        pyplot.legend(loc=legend_location)

    pyplot.grid(True)
    pyplot.xlabel(x_label)
    pyplot.show()



def bode_plot(freq: list, v_out: list, v_in: list = None):
    """ Generates a Bode plot of the gain, computed by (v_out / v_in).

    :param freq: a list of frequency data in Hz
    :param v_out: output voltage
    :param v_in: input voltage, assumed to be 1 if omitted
    """
    mag = []
    phase = []
    for i in range(0, len(v_out)):
        if v_in is None:
            gain = v_out[i]
        else:
            gain = v_out[i] / v_in[i]

        m, p = cmath.polar(gain)
        mag.append(20 * math.log10(m))
        phase.append(math.degrees(p))

    # plot magnitude
    pyplot.subplot(211)
    pyplot.xscale("log")
    pyplot.ylabel("Magnitude")
    pyplot.plot(freq, mag)

    # plot phase
    pyplot.subplot(212)
    pyplot.xscale("log")
    pyplot.xlabel("Frequency")
    pyplot.ylabel("Phase")
    pyplot.plot(freq, phase)

    pyplot.show()
