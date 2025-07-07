from dycov.gfm.parameters import GFM_Params


class GFMCalculator:
    # Constants for indexing parameter arrays: original, minimum, and maximum values.
    _ORIGINAL_PARAMS_IDX = 0
    _MINIMUM_PARAMS_IDX = 1
    _MAXIMUM_PARAMS_IDX = 2
    # Threshold to differentiate between overdamped and underdamped systems.
    # Critically damped systems are grouped with overdamped.
    _EPSILON_THRESHOLD = 1.0

    def __init__(self, gfm_params: GFM_Params, debug: bool = False):
        """
        Initializes the PhaseJump class with GFM parameters.

        Parameters
        ----------
        gfm_params: GFM_Params
            Parameters for the GFM phase jump calculations.
        """
        self._gfm_params = gfm_params
        self._debug = debug
