# -*- coding: utf-8 -*-
# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
# Contributors:
#    INITIAL AUTHORS - API and implementation and/or documentation
#       :author: Damien Guenot - 26 avr. 2016
#       :author: Francois Gallard, refactoring
#    OTHER AUTHORS   - MACROSCOPIC CHANGES

"""Base class for algorithm libraries."""

from __future__ import unicode_literals

import inspect
import logging
from typing import Any, Dict, List, Mapping, MutableMapping

from numpy import ndarray

from gemseo.algos.linear_solvers.linear_problem import LinearProblem
from gemseo.core.grammar import InvalidDataException
from gemseo.core.json_grammar import JSONGrammar
from gemseo.utils.py23_compat import Path
from gemseo.utils.source_parsing import get_options_doc

LOGGER = logging.getLogger(__name__)


class AlgoLib(object):
    """Abstract class for algorithms libraries interfaces.

    An algorithm library solves a numerical problem
    (optim, doe, linear problem) using a particular algorithm
    from a particular family of numerical methods.

    Provide the available methods in the library for the proposed
    problem to be solved.

    To integrate an optimization package, inherit from this class
    and put your module in gemseo.algos.doe or gemseo.algo.opt,
    or gemseo.algos.linear_solver packages.

    Attributes:
        lib_dict (Dict[str, Dict[str, Union[str, bool]]]): The properties
            of the algorithm in terms
            of requirements on the properties of the problem to
            be solved.
        algo_name (str): The name of the algorithm used currently.
        internal_algo_name (str): The name of the algorithm used currently
            as defined in the used library.
        problem (Any): The problem to be solved.
    """

    LIB = "lib"
    INTERNAL_NAME = "internal_algo_name"
    OPTIONS_DIR = "options"
    OPTIONS_MAP = {}
    PROBLEM_TYPE = "problem_type"

    def __init__(self):  # type: (...) -> None
        # Library settings and check
        self.lib_dict = {}
        self.algo_name = None
        self.internal_algo_name = None
        self.problem = None

    def init_options_grammar(
        self,
        algo_name,  # type: str
    ):  # type: (...) -> JSONGrammar
        """Initialize the options grammar.

        :param algo_name: The name of the algorithm.
        """
        library_directory = Path(inspect.getfile(self.__class__)).parent
        options_directory = library_directory / self.OPTIONS_DIR
        algo_schema_file = options_directory / "{}_options.json".format(
            algo_name.upper()
        )
        lib_schema_file = options_directory / "{}_options.json".format(
            self.__class__.__name__.upper()
        )

        if algo_schema_file.exists():
            schema_file = algo_schema_file
        elif lib_schema_file.exists():
            schema_file = lib_schema_file
        else:
            msg = (
                "Neither the options grammar file {} for the algorithm '{}' "
                "nor the options grammar file {} for the library '{}' has been found."
            ).format(
                algo_schema_file, algo_name, lib_schema_file, self.__class__.__name__
            )
            raise ValueError(msg)

        descr_dict = get_options_doc(self.__class__._get_options)
        self.opt_grammar = JSONGrammar(
            algo_name, schema_file=schema_file, descriptions=descr_dict
        )

        return self.opt_grammar

    @property
    def algorithms(self):  # type: (...) -> List[str]
        """The available algorithms."""
        return list(self.lib_dict.keys())

    def _pre_run(
        self,
        problem,  # type: LinearProblem
        algo_name,  # type: str
        **options  # type: Any
    ):  # type: (...) -> None  # pragma: no cover
        """Save the solver options and name in the problem attributes.

        Args:
            problem: The problem to be solved.
            algo_name: The name of the algorithm.
            options: The options for the algorithm, see associated JSON file.
        """
        pass

    def _post_run(
        self,
        problem,  # type: LinearProblem
        algo_name,  # type: str
        result,  # type: ndarray
        **options  # type: Any
    ):  # type: (...) -> None  # pragma: no cover
        """Save the LinearProblem to the disk when required.

        If the save_when_fail option is True, save the LinearProblem to the disk when
        the system failed and print the file name in the warnings.

        Args:
            problem: The problem to be solved.
            algo_name: The name of the algorithm.
            result: The result of the run, i.e. the solution.
            options: The options for the algorithm, see associated JSON file.
        """
        pass

    def driver_has_option(
        self, option_key  # type: str
    ):  # type: (...) -> bool
        """Check if the option key exists.

        :param option_key: The name of the option.
        :return: Whether the option is in the grammar.
        """
        return self.opt_grammar.is_data_name_existing(option_key)

    def _process_specific_option(
        self,
        options,  # type: MutableMapping[str, Any]
        option_key,  # type:str
    ):  # type: (...) -> None # pragma: no cover
        """Preprocess the option specifically, to be overriden by subclasses.

        Args:
            options: The options to be preprocessed.
            option_key: The current option key to process.
        """
        pass

    def _process_options(
        self, **options  # type:Any
    ):  # type: (...) -> Dict[str, Any]
        """Convert the options to algorithm specific options and check them.

        Args:
            options: The driver options.

        Returns:
            The converted options.

        Raises:
            ValueError: If an option is invalid.
        """
        for option_key in list(options.keys()):  # Copy keys on purpose
            # Remove extra options added in the _get_option method of the
            # driver
            if not self.driver_has_option(option_key):
                del options[option_key]
            else:
                self._process_specific_option(options, option_key)

        try:
            self.opt_grammar.load_data(options)
        except InvalidDataException:
            raise ValueError("Invalid options for algorithm " + self.opt_grammar.name)

        for option_key in list(options.keys()):  # Copy keys on purpose
            lib_option_key = self.OPTIONS_MAP.get(option_key)
            # Overload with specific keys
            if lib_option_key is not None:
                options[lib_option_key] = options[option_key]
                if lib_option_key != option_key:
                    del options[option_key]
        return options

    def _check_ignored_options(
        self, options  # type:Mapping[str, Any]
    ):  # type: (...) -> None
        """Check that the user did not pass options that do not exist for this driver.

        Log a warning if it is the case.

        :param options: The options.
        """
        for option_key in options:
            if not self.driver_has_option(option_key):
                msg = "Driver %s has no option %s, option is ignored."
                LOGGER.warning(msg, self.algo_name, option_key)

    def execute(
        self,
        problem,  # type: Any
        algo_name=None,  # type: str
        **options  # type: Any
    ):  # type: (...) -> None
        """Executes the driver.

        :param problem: The problem to be solved.
        :param algo_name: The name of the algorithm>
            If None, use the algo_name attribute
            which may have been set by the factory.
        :param options: The options dict for the algorithm.
        """
        self.problem = problem

        if algo_name is not None:
            self.algo_name = algo_name

        if self.algo_name is None:
            raise ValueError(
                "Algorithm name must be either passed as "
                + "argument or set by the attribute self.algo_name"
            )

        self._check_algorithm(self.algo_name, problem)
        options = self._update_algorithm_options(**options)
        self.internal_algo_name = self.lib_dict[self.algo_name][self.INTERNAL_NAME]
        problem.check()

        self._pre_run(problem, self.algo_name, **options)
        result = self._run(**options)
        self._post_run(problem, algo_name, result, **options)

        return result

    def _update_algorithm_options(
        self, **options  # type: Any
    ):  # type: (...) -> Dict[str, Any]
        """Update the algorithm options.

        1. Load the grammar of algorithm options.
        2. Warn about the ignored initial algorithm options.
        3. Complete the initial algorithm options with the default algorithm options.

        Args:
            **options: The initial algorithm options.

        Returns:
            The updated algorithm options.
        """
        self.init_options_grammar(self.algo_name)
        self._check_ignored_options(options)
        return self._get_options(**options)

    def _get_options(
        self, **options  # type: Any
    ):  # type: (...) -> None
        """Retrieve the options of the library.

        To be overloaded by subclasses.
        Used to define default values for options using keyword arguments.

        :param options: The options of the driver.
        """
        raise NotImplementedError()

    def _run(self, **options):  # type: (...) -> Any
        """Run the algorithm.

        To be overloaded by subclasses.

        :param options: The options for the algorithm.

        :returns: The solution of the problem.
        """
        raise NotImplementedError()

    def _check_algorithm(
        self,
        algo_name,  # type: str
        problem,  # type: Any
    ):  # type: (...) -> None
        """Check that algorithm is available and adapted to the problem.

        Set the optimization library and the algorithm name according
        to the requirements of the optimization library.

        :param algo_name: The name of algorithm.
        :param problem: The problem to be solved.
        """
        # Check that the algorithm is available
        if algo_name not in self.lib_dict:
            raise KeyError(
                "Requested algorithm {} is not in list of available algorithms: "
                "{}.".format(algo_name, ", ".join(self.lib_dict.keys()))
            )

        # Check that the algorithm is suited to the problem
        algo_dict = self.lib_dict[self.algo_name]
        if not self.is_algorithm_suited(algo_dict, problem):
            raise ValueError(
                "Algorithm {} is not adapted to the problem.".format(algo_name)
            )

    @staticmethod
    def is_algorithm_suited(
        algo_dict,  # type: Mapping[str,bool]
        problem,  # type: Any
    ):  # type: (...) -> bool
        """Check if the algorithm is suited to the problem according to algo_dict.

        :param algo_dict: the algorithm characteristics
        :param problem: the opt_problem to be solved
        """
        raise NotImplementedError()

    def filter_adapted_algorithms(
        self, problem  # type: Any
    ):  # type: (...) -> bool
        """Filter the algorithms capable of solving the problem.

        :param problem: The opt_problem to be solved.
        :returns: The list of adapted algorithms names.
        """
        available = []
        for algo_name, algo_dict in self.lib_dict.items():
            if self.is_algorithm_suited(algo_dict, problem):
                available.append(algo_name)
        return available
