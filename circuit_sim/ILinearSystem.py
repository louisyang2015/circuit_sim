import numpy
import scipy.sparse.linalg

# dok_matrix = Dictionary Of Keys based sparse matrix
from scipy.sparse import dok_matrix


class ILinearSystem:
    """Interface to an Ax=b linear system."""
    def __init__(self):
        self.A = None
        self.b = None
        self.x = None

    def clear(self):
        raise Exception("ILinearSystem::clear() is not implemented.")

    def solve(self):
        raise Exception("ILinearSystem::solve() is not implemented.")

    @staticmethod
    def create(num_variables: int, dtype, options: str):
        """
        :param dtype: Numpy dtype
        :param options: "dense", "sparse"
        """
        if options == "dense":
            return NumpyLinearSystem(num_variables, dtype)
        elif options == "sparse":
            return SparseLinearSystem(num_variables, dtype)
        else:
            raise Exception("ILinearSystem::create(...) does not accept "
                            + "option \"" + options + "\".")



class NumpyLinearSystem(ILinearSystem):
    def __init__(self, num_variables: int, dtype):
        super().__init__()
        self.A = numpy.zeros((num_variables, num_variables), dtype=dtype)
        self.b = numpy.zeros(num_variables, dtype=dtype)

    def clear(self):
        num_variables = self.A.shape[0]
        dtype = self.A.dtype
        self.A = numpy.zeros((num_variables, num_variables), dtype=dtype)
        self.b = numpy.zeros(num_variables, dtype=dtype)

    def solve(self):
        self.x = numpy.linalg.solve(self.A, self.b)


class SparseLinearSystem(ILinearSystem):
    def __init__(self, num_variables: int, dtype):
        super().__init__()
        self.A = dok_matrix((num_variables, num_variables), dtype=dtype)
        self.b = numpy.zeros(num_variables, dtype=dtype)

    def clear(self):
        num_variables = self.A.shape[0]
        dtype = self.A.dtype
        self.A.clear()
        self.b = numpy.zeros(num_variables, dtype=dtype)

    def solve(self):
        self.x, info = scipy.sparse.linalg.gmres(self.A, self.b)
        if info > 0:
            raise Exception("Failed to solve linear system. "
                            + "scipy.sparse.linalg.gmres(...) failed to converge "
                            + "after " + str(info) + " number of iterations.")
        if info < 0:
            raise Exception("Failed to solve linear system. "
                            + "scipy.sparse.linalg.gmres(...) reports \""
                            + "illegal input or breakdown\"")


