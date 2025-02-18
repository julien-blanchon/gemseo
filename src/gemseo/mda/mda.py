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
#        :author: Francois Gallard, Charlie Vanaret
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
"""Base class for all Multi-disciplinary Design Analyses (MDA)."""
from __future__ import annotations

import logging
from abc import abstractmethod
from enum import auto
from multiprocessing import cpu_count
from pathlib import Path
from typing import Any
from typing import ClassVar
from typing import Iterable
from typing import Mapping

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from numpy import abs
from numpy import array
from numpy import concatenate
from numpy import ndarray
from numpy.linalg import norm
from numpy.typing import NDArray
from strenum import LowercaseStrEnum

from gemseo.core.coupling_structure import DependencyGraph
from gemseo.core.coupling_structure import MDOCouplingStructure
from gemseo.core.derivatives.jacobian_assembly import JacobianAssembly
from gemseo.core.discipline import MDODiscipline
from gemseo.core.execution_sequence import ExecutionSequenceFactory
from gemseo.core.execution_sequence import LoopExecSequence
from gemseo.utils.matplotlib_figure import FigSizeType
from gemseo.utils.matplotlib_figure import save_show_figure
from gemseo.utils.metaclasses import ABCGoogleDocstringInheritanceMeta

LOGGER = logging.getLogger(__name__)


class MDA(MDODiscipline, metaclass=ABCGoogleDocstringInheritanceMeta):
    """An MDA analysis."""

    N_CPUS = cpu_count()

    RESIDUALS_NORM: ClassVar[str] = "MDA residuals norm"

    activate_cache = True

    tolerance: float
    """The tolerance of the iterative direct coupling solver."""

    linear_solver: str
    """The name of the linear solver."""

    linear_solver_tolerance: float
    """The tolerance of the linear solver in the adjoint equation."""

    linear_solver_options: dict[str, Any]
    """The options of the linear solver."""

    _max_mda_iter: int
    """The maximum iterations number for the MDA algorithm."""

    coupling_structure: MDOCouplingStructure
    """The coupling structure to be used by the MDA."""

    assembly: JacobianAssembly

    residual_history: list[float]
    """The history of MDA residuals."""

    reset_history_each_run: bool
    """Whether to reset the history of MDA residuals before each run."""

    warm_start: bool
    """Whether the second iteration and ongoing start from the previous solution."""

    scaling: ResidualScaling
    """The scaling method applied to MDA residuals for convergence monitoring."""

    _scaling_data: float | list[tuple[slice, float]] | NDArray[float] | None
    """The data required to perform the scaling of the MDA residuals."""

    norm0: float | None
    """The reference residual, if any."""

    normed_residual: float
    """The normed residual."""

    strong_couplings: list[str]
    """The names of the strong coupling variables."""

    all_couplings: list[str]
    """The names of the coupling variables."""

    matrix_type: JacobianAssembly.JacobianType
    """The type of the matrix."""

    use_lu_fact: bool
    """Whether to store a LU factorization of the matrix."""

    lin_cache_tol_fact: float
    """The tolerance factor to cache the Jacobian."""

    _starting_indices: list[int]
    """The indices of the residual history where a new execution starts."""

    class ResidualScaling(LowercaseStrEnum):
        """The scaling method applied to MDA residuals for convergence monitoring."""

        NO_SCALING = auto()
        r"""The residual is not scaled and the MDA is considered converged when,

        .. math::
            \|R_k\|_2 \leq \text{tol}.
        """

        INITIAL_RESIDUAL_NORM = auto()
        r"""The residual is scaled by the norm of the initial residual if it is not null,
        and not scaled otherwise. The MDA is considered converged when,

        .. math::
            \frac{ \|R_k\|_2 }{ \|R_0\|_2 } \leq \text{tol}.
        """

        INITIAL_SUBRESIDUAL_NORM = auto()
        r"""The residual is scaled by considering the convergence of each sub-residual
        individually. The MDA is considered converged when,

        .. math::
            \max_i \left| \frac{\|r^i_k\|_2}{\|r^i_0\|_2} \right| \leq \text{tol}.
        """

        N_COUPLING_VARIABLES = auto()
        r"""The residual is scaled by the number of coupling variables. The MDA is
        considered converged when,

        .. math::
            \frac{ \|R_k\|_2 }{ \sqrt{n_\text{coupl.}} } \leq \text{tol}.
        """

        INITIAL_RESIDUAL_COMPONENT = auto()
        r"""The residual is scaled component-wise with the initial residual if not null,
        and not scaled otherwise. The MDA is considered converged when,

        .. math::
            \max_i \left| \frac{(R_k)_i}{(R_0)_i} \right| \leq \text{tol}.
        """

        SCALED_INITIAL_RESIDUAL_COMPONENT = auto()
        r"""The residual is not scaled and the MDA is considered converged when.

        .. math::
            \frac{1}{\sqrt{n_\text{coupl.}}} \| R_k \div R_0 \|_2 \leq \text{tol}.
        """

    def __init__(
        self,
        disciplines: list[MDODiscipline],
        max_mda_iter: int = 10,
        name: str | None = None,
        grammar_type: MDODiscipline.GrammarType = MDODiscipline.GrammarType.JSON,
        tolerance: float = 1e-6,
        linear_solver_tolerance: float = 1e-12,
        warm_start: bool = False,
        use_lu_fact: bool = False,
        coupling_structure: MDOCouplingStructure | None = None,
        log_convergence: bool = False,
        linear_solver: str = "DEFAULT",
        linear_solver_options: Mapping[str, Any] = None,
    ) -> None:
        """
        Args:
            disciplines: The disciplines from which to compute the MDA.
            max_mda_iter: The maximum iterations number for the MDA algorithm.
            name: The name to be given to the MDA.
                If None, use the name of the class.
            grammar_type: The type of the input and output grammars.
            tolerance: The tolerance of the iterative direct coupling solver;
                the norm of the current residuals divided by initial residuals norm
                shall be lower than the tolerance to stop iterating.
            linear_solver_tolerance: The tolerance of the linear solver
                in the adjoint equation.
            warm_start: Whether the second iteration and ongoing start
                from the previous coupling solution.
            use_lu_fact: Whether to store a LU factorization of the matrix
                when using adjoint/forward differentiation.
                to solve faster multiple RHS problem.
            coupling_structure: The coupling structure to be used by the MDA.
                If None, it is created from `disciplines`.
            log_convergence: Whether to log the MDA convergence,
                expressed in terms of normed residuals.
            linear_solver: The name of the linear solver.
            linear_solver_options: The options passed to the linear solver factory.
        """  # noqa:D205 D212 D415
        super().__init__(name, grammar_type=grammar_type)
        self.tolerance = tolerance
        self.linear_solver = linear_solver
        self.linear_solver_tolerance = linear_solver_tolerance
        self.linear_solver_options = linear_solver_options or {}
        self.max_mda_iter = max_mda_iter
        self._disciplines = disciplines
        if coupling_structure is None:
            self.coupling_structure = MDOCouplingStructure(disciplines)
        else:
            self.coupling_structure = coupling_structure
        self.assembly = JacobianAssembly(self.coupling_structure)
        self.residual_history = []
        self._starting_indices = []
        self.reset_history_each_run = False
        self.warm_start = warm_start

        self.scaling = self.ResidualScaling.INITIAL_RESIDUAL_NORM
        self._scaling_data = None

        # Don't erase coupling values before calling _compute_jacobian

        self._linearize_on_last_state = True
        self.norm0 = None
        self._current_iter = 0
        self.normed_residual = 1.0
        self.strong_couplings = self.coupling_structure.strong_couplings
        self.all_couplings = self.coupling_structure.all_couplings
        self._input_couplings = []
        self.matrix_type = JacobianAssembly.JacobianType.MATRIX
        self.use_lu_fact = use_lu_fact
        # By default don't use an approximate cache for linearization
        self.lin_cache_tol_fact = 0.0

        self._initialize_grammars()
        self._check_consistency()
        self.__check_linear_solver_options()
        self._check_coupling_types()
        self._log_convergence = log_convergence

    @property
    def max_mda_iter(self) -> int:
        """The maximum iterations number of the MDA algorithm."""
        return self._max_mda_iter

    @max_mda_iter.setter
    def max_mda_iter(self, max_mda_iter: int) -> None:
        self._max_mda_iter = max_mda_iter

    def _initialize_grammars(self) -> None:
        """Define all the inputs and outputs of the MDA.

        Add all the outputs of all the disciplines to the outputs.
        """
        for discipline in self.disciplines:
            self.input_grammar.update(discipline.input_grammar)
            self.output_grammar.update(discipline.output_grammar)

        self._add_residuals_norm_to_output_grammar()

    def _add_residuals_norm_to_output_grammar(self) -> None:
        """Add RESIDUALS_NORM to the output grammar."""
        self.output_grammar.update_from_names([self.RESIDUALS_NORM])

    @property
    def log_convergence(self) -> bool:
        """Whether to log the MDA convergence."""
        return self._log_convergence

    @log_convergence.setter
    def log_convergence(
        self,
        value: bool,
    ) -> None:
        self._log_convergence = value

    def __check_linear_solver_options(self) -> None:
        """Check the linear solver options.

        The linear solver tolerance cannot be set
        using the linear solver option dictionary,
        as it is set using the linear_solver_tolerance keyword argument.

        Raises:
            ValueError: If the ``tol`` keyword is in :attr:`.linear_solver_options`.
        """
        if "tol" in self.linear_solver_options:
            msg = (
                "The linear solver tolerance shall be set"
                " using the linear_solver_tolerance argument."
            )
            raise ValueError(msg)

    def _check_consistency(self) -> None:
        """Check if there are not more than one equation per variable.

        For instance if a strong coupling is not also a self coupling, or if outputs are
        defined multiple times.
        """
        strong_c_disc = self.coupling_structure.get_strongly_coupled_disciplines(
            add_self_coupled=False
        )
        also_strong = [
            disc
            for disc in strong_c_disc
            if self.coupling_structure.is_self_coupled(disc)
        ]
        if also_strong:
            for disc in also_strong:
                in_outs = sorted(
                    set(disc.get_input_data_names()) & set(disc.get_output_data_names())
                )
                LOGGER.warning(
                    "Self coupling variables in discipline %s are: %s.",
                    disc.name,
                    in_outs,
                )

            also_strong_n = sorted(disc.name for disc in also_strong)
            LOGGER.warning(
                "The following disciplines contain self-couplings and strong couplings:"
                " %s. This is not a problem as long as their self-coupling variables "
                "are not strongly coupled to another discipline.",
                also_strong_n,
            )

        all_outs = {}
        multiple_outs = []
        for disc in self.disciplines:
            for out in disc.get_output_data_names():
                if out in all_outs:
                    multiple_outs.append(out)
                all_outs[out] = disc

        if multiple_outs:
            LOGGER.warning(
                "The following outputs are defined multiple times: %s.",
                sorted(multiple_outs),
            )

    def _compute_input_couplings(self) -> None:
        """Compute the strong couplings that are inputs of the MDA."""
        input_couplings = set(self.strong_couplings) & set(self.get_input_data_names())
        self._input_couplings = sorted(input_couplings)

    def _current_input_couplings(self) -> ndarray:
        """Return the current values of the input coupling variables."""
        input_couplings = list(self.get_outputs_by_name(self._input_couplings))
        if not input_couplings:
            return array([])
        return concatenate(input_couplings)

    def _current_strong_couplings(self) -> ndarray:
        """Return the current values of the strong coupling variables."""
        couplings = list(self.get_outputs_by_name(self.strong_couplings))
        if not couplings:
            return array([])
        return concatenate(couplings)

    def _retrieve_diff_inouts(
        self, compute_all_jacobians: bool = False
    ) -> tuple[set[str] | list[str], set[str] | list[str]]:
        if compute_all_jacobians:
            strong_cpl = set(self.strong_couplings)
            inputs = set(self.get_input_data_names())
            outputs = self.get_output_data_names()
            # Don't linearize wrt
            inputs -= strong_cpl & inputs
            # Don't do this with output couplings because
            # their derivatives wrt design variables may be needed
            # outputs = outputs - (strong_cpl & outputs)
        else:
            inputs, outputs = MDODiscipline._retrieve_diff_inouts(self)

        if self.RESIDUALS_NORM in outputs:
            outputs = list(outputs)
            outputs.remove(self.RESIDUALS_NORM)
        return inputs, outputs

    def _couplings_warm_start(self) -> None:
        """Load the previous couplings values to local data."""
        cached_outputs = self.cache.last_entry.outputs
        if not cached_outputs:
            return
        for input_name in self._input_couplings:
            input_value = cached_outputs.get(input_name)
            if input_value is not None:
                self.local_data[input_name] = input_value

    def _check_coupling_types(self) -> None:
        """Check that the coupling variables are of type array in the grammars.

        Raises:
            TypeError: When at least one of the coupling variables is not an array.
        """
        not_arrays = []
        for discipline in self.disciplines:
            for grammar in (discipline.input_grammar, discipline.output_grammar):
                for coupling in self.all_couplings:
                    if coupling in grammar and not grammar.is_array(
                        coupling, numeric_only=True
                    ):
                        not_arrays.append(coupling)

        if not_arrays:
            not_arrays = sorted(set(not_arrays))
            raise TypeError(
                f"The coupling variables {not_arrays} must be of type array."
            )

    def reset_disciplines_statuses(self) -> None:
        """Reset all the statuses of the disciplines."""
        for discipline in self.disciplines:
            discipline.reset_statuses_for_run()

    def reset_statuses_for_run(self) -> None:  # noqa:D102
        MDODiscipline.reset_statuses_for_run(self)
        self.reset_disciplines_statuses()

    def get_expected_workflow(self) -> LoopExecSequence:  # noqa:D102
        disc_exec_seq = ExecutionSequenceFactory.serial()
        for disc in self.disciplines:
            disc_exec_seq.extend(disc.get_expected_workflow())
        return ExecutionSequenceFactory.loop(self, disc_exec_seq)

    def get_expected_dataflow(  # noqa:D102
        self,
    ) -> list[tuple[MDODiscipline, MDODiscipline, list[str]]]:
        all_disc = [self]
        all_disc.extend(self.disciplines)
        graph = DependencyGraph(all_disc)
        res = graph.get_disciplines_couplings()
        for discipline in self.disciplines:
            res.extend(discipline.get_expected_dataflow())
        return res

    def _compute_jacobian(
        self,
        inputs: Iterable[str] | None = None,
        outputs: Iterable[str] | None = None,
    ) -> None:
        # Do not re-execute disciplines if inputs error is beyond self tol
        # Apply a safety factor on this (mda is a loop, inputs
        # of first discipline
        # have changed at convergence, therefore the cache is not exactly
        # the same as the current value
        exec_cache_tol = self.lin_cache_tol_fact * self.tolerance
        self.__check_linear_solver_options()
        residual_variables = {}
        for disc in self.disciplines:
            residual_variables.update(disc.residual_variables)

        couplings_adjoint = sorted(
            set(self.all_couplings)
            - residual_variables.keys()
            - set(residual_variables.values())
        )

        self.jac = self.assembly.total_derivatives(
            self.local_data,
            outputs,
            inputs,
            couplings_adjoint,
            tol=self.linear_solver_tolerance,
            mode=self.linearization_mode,
            matrix_type=self.matrix_type,
            use_lu_fact=self.use_lu_fact,
            exec_cache_tol=exec_cache_tol,
            execute=exec_cache_tol == 0.0,
            linear_solver=self.linear_solver,
            residual_variables=residual_variables,
            **self.linear_solver_options,
        )

    def _compute_residual(
        self,
        current_couplings: ndarray,
        new_couplings: ndarray,
        store_it: bool = True,
        log_normed_residual: bool = False,
    ) -> float:
        """Compute the residual on the inputs of the MDA.

        Args:
            current_couplings: The values of the couplings before the execution.
            new_couplings: The values of the couplings after the execution.
            store_it: Whether to store the normed residual.
            log_normed_residual: Whether to log the normed residual.

        Returns:
            The normed residual.
        """
        if self._current_iter == 0 and self.reset_history_each_run:
            self.residual_history = []
            self._starting_indices = []

        residual = (current_couplings - new_couplings).real

        if self.scaling == self.ResidualScaling.NO_SCALING:
            normed_residual = norm(residual)

            self.normed_residual = normed_residual

        elif self.scaling == self.ResidualScaling.INITIAL_RESIDUAL_NORM:
            normed_residual = norm(residual)

            if self._scaling_data is None:
                self._scaling_data = normed_residual + (normed_residual == 0)

            self.normed_residual = normed_residual / self._scaling_data

        elif self.scaling == self.ResidualScaling.N_COUPLING_VARIABLES:
            normed_residual = norm(residual)

            if self._scaling_data is None:
                self._scaling_data = new_couplings.size**0.5

            self.normed_residual = normed_residual / self._scaling_data

        elif self.scaling == self.ResidualScaling.INITIAL_SUBRESIDUAL_NORM:
            if self._scaling_data is None:
                self._scaling_data = list()

                index = 0
                for output in self.get_outputs_by_name(self._input_couplings):
                    current_slice = slice(index, index + output.size)
                    initial_norm = norm(residual[current_slice])
                    self._scaling_data.append(
                        (current_slice, initial_norm + (initial_norm == 0))
                    )
                    index += output.size

            normalized_norms = list()
            for index, initial_norm in self._scaling_data:
                normalized_norms.append(norm(residual[index]) / initial_norm)

            self.normed_residual = max(normalized_norms)

        elif self.scaling == self.ResidualScaling.INITIAL_RESIDUAL_COMPONENT:
            if self._scaling_data is None:
                self._scaling_data = residual + (residual == 0)

            self.normed_residual = abs(residual / self._scaling_data).max()

        elif self.scaling == self.ResidualScaling.SCALED_INITIAL_RESIDUAL_COMPONENT:
            if self._scaling_data is None:
                self._scaling_data = residual + (residual == 0)

            self.normed_residual = norm(residual / self._scaling_data)
            self.normed_residual /= new_couplings.size**0.5

        else:
            # Use the strEnum casting to raise an explicit error
            self.ResidualScaling(self.scaling)

        if log_normed_residual:
            LOGGER.info(
                "%s running... Normed residual = %s (iter. %s)",
                self.name,
                f"{self.normed_residual:.2e}",
                self._current_iter,
            )

        if store_it:
            if self._current_iter == 0:
                self._starting_indices.append(len(self.residual_history))
            self.residual_history.append(self.normed_residual)
            self._current_iter += 1

        self.local_data[self.RESIDUALS_NORM] = array([self.normed_residual])
        return self.normed_residual

    def check_jacobian(
        self,
        input_data: Mapping[str, ndarray] | None = None,
        derr_approx: MDODiscipline.ApproximationMode = MDODiscipline.ApproximationMode.FINITE_DIFFERENCES,  # noqa:B950
        step: float = 1e-7,
        threshold: float = 1e-8,
        linearization_mode: str = "auto",
        inputs: Iterable[str] | None = None,
        outputs: Iterable[str] | None = None,
        parallel: bool = False,
        n_processes: int = N_CPUS,
        use_threading: bool = False,
        wait_time_between_fork: int = 0,
        auto_set_step: bool = False,
        plot_result: bool = False,
        file_path: str | Path = "jacobian_errors.pdf",
        show: bool = False,
        fig_size_x: float = 10,
        fig_size_y: float = 10,
        reference_jacobian_path: None | Path | str = None,
        save_reference_jacobian: bool = False,
        indices: Iterable[int] | None = None,
    ) -> bool:
        """Check if the analytical Jacobian is correct with respect to a reference one.

        If `reference_jacobian_path` is not `None`
        and `save_reference_jacobian` is `True`,
        compute the reference Jacobian with the approximation method
        and save it in `reference_jacobian_path`.

        If `reference_jacobian_path` is not `None`
        and `save_reference_jacobian` is `False`,
        do not compute the reference Jacobian
        but read it from `reference_jacobian_path`.

        If `reference_jacobian_path` is `None`,
        compute the reference Jacobian without saving it.

        Args:
            input_data: The input values.
                If None, use the default input values.
            derr_approx: The derivative approximation method.
            threshold: The acceptance threshold for the Jacobian error.
            linearization_mode: The mode of linearization,
                either "direct", "adjoint" or "auto" switch
                depending on dimensions of inputs and outputs.
            inputs: The names of the inputs with respect to which to differentiate.
                If None, use the inputs of the MDA.
            outputs: The outputs to differentiate.
                If None, use all the outputs of the MDA.
            step: The step
                for finite differences or complex step differentiation methods.
            parallel: Whether to execute the MDA in parallel.
            n_processes: The maximum simultaneous number of threads,
                if ``use_threading`` is True, or processes otherwise,
                used to parallelize the execution.
            use_threading: Whether to use threads instead of processes
                to parallelize the execution;
                multiprocessing will copy (serialize) all the disciplines,
                while threading will share all the memory.
                This is important to note
                if you want to execute the same discipline multiple times,
                you shall use multiprocessing.
            wait_time_between_fork: The time waited between two forks
                of the process / thread.
            auto_set_step: Whether to compute the optimal step
                for a forward first order finite differences gradient approximation.
            plot_result: Whether to plot the result of the validation
                comparing the exact and approximated Jacobians.
            file_path: The path to the output file if `plot_result` is `True`.
            show: Whether to open the figure.
            fig_size_x: The *x* size of the figure in inches.
            fig_size_y: The *y* size of the figure in inches.
            reference_jacobian_path: The path of the reference Jacobian file.
            save_reference_jacobian: Whether to save the reference Jacobian.
            indices: The indices of the inputs and outputs
                for the different sub-Jacobian matrices,
                formatted as ``{variable_name: variable_components}``
                where ``variable_components`` can be either
                an integer, e.g. `2`
                a sequence of integers, e.g. `[0, 3]`,
                a slice, e.g. `slice(0,3)`,
                the ellipsis symbol (`...`)
                or `None`, which is the same as ellipsis.
                If a variable name is missing, consider all its components.
                If None, consider all the components of all the ``inputs`` and ``outputs``.

        Returns:
            Whether the passed Jacobian is correct.
        """
        # Strong couplings are not linearized
        if inputs is None:
            inputs = self.get_input_data_names()
        if outputs is None:
            outputs = self.get_output_data_names()

        inputs = list(inputs)
        outputs = list(outputs)

        for coupling in self.all_couplings:
            if coupling in outputs:
                outputs.remove(coupling)
            if coupling in inputs:
                inputs.remove(coupling)

        if self.RESIDUALS_NORM in outputs:
            outputs.remove(self.RESIDUALS_NORM)

        return super().check_jacobian(
            input_data=input_data,
            derr_approx=derr_approx,
            step=step,
            threshold=threshold,
            linearization_mode=linearization_mode,
            inputs=inputs,
            outputs=outputs,
            parallel=parallel,
            n_processes=n_processes,
            use_threading=use_threading,
            wait_time_between_fork=wait_time_between_fork,
            auto_set_step=auto_set_step,
            plot_result=plot_result,
            file_path=file_path,
            show=show,
            fig_size_x=fig_size_x,
            fig_size_y=fig_size_y,
            reference_jacobian_path=reference_jacobian_path,
            save_reference_jacobian=save_reference_jacobian,
            indices=indices,
        )

    def execute(  # noqa:D102
        self, input_data: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        self._current_iter = 0
        return super().execute(input_data=input_data)

    def _warn_convergence_criteria(self) -> tuple[bool, bool]:
        """Log a warning if max_iter is reached and if max residuals is above tolerance.

        Returns:
            * Whether the normed residual is lower than the tolerance.
            * Whether the maximum number of iterations is reached.
        """
        residual_is_small = self.normed_residual <= self.tolerance
        max_iter_is_reached = self.max_mda_iter <= self._current_iter
        if max_iter_is_reached and not residual_is_small:
            msg = (
                "%s has reached its maximum number of iterations "
                "but the normed residual %s is still above the tolerance %s."
            )
            LOGGER.warning(msg, self.name, self.normed_residual, self.tolerance)
        return residual_is_small, max_iter_is_reached

    @property
    def _stop_criterion_is_reached(self) -> bool:
        """Whether a stop criterion is reached."""
        residual_is_small, max_iter_is_reached = self._warn_convergence_criteria()
        return residual_is_small or max_iter_is_reached

    def _set_cache_tol(
        self,
        cache_tol: float,
    ) -> None:
        """Set to the cache input tolerance.

        To be overloaded by subclasses.

        Args:
            cache_tol: The cache tolerance.
        """
        super()._set_cache_tol(cache_tol)
        for disc in self.disciplines:
            disc.cache_tol = cache_tol or 0.0

    def plot_residual_history(
        self,
        show: bool = False,
        save: bool = True,
        n_iterations: int | None = None,
        logscale: tuple[int, int] | None = None,
        filename: str | None = None,
        fig_size: FigSizeType | None = None,
    ) -> Figure:
        """Generate a plot of the residual history.

        The first iteration of each new execution is marked with a red dot.

        Args:
            show: Whether to display the plot on screen.
            save: Whether to save the plot as a PDF file.
            n_iterations: The number of iterations on the *x* axis.
                If None, use all the iterations.
            logscale: The limits of the *y* axis.
                If None, do not change the limits of the *y* axis.
            filename: The name of the file to save the figure.
                If None, use "{mda.name}_residual_history.pdf".
            fig_size: The width and height of the figure in inches, e.g. `(w, h)`.

        Returns:
            The figure, to be customized if not closed.
        """
        fig = plt.figure()
        fig_ax = fig.add_subplot(1, 1, 1)

        history_length = len(self.residual_history)
        n_iterations = n_iterations or history_length

        if n_iterations > history_length:
            msg = (
                "Requested %s iterations but the residual history contains only %s, "
                "plotting all the residual history."
            )
            LOGGER.info(msg, n_iterations, history_length)
            n_iterations = history_length

        # red dot for first iteration
        colors = ["black"] * n_iterations
        for index in self._starting_indices:
            colors[index] = "red"

        fig_ax.scatter(
            list(range(n_iterations)),
            self.residual_history[:n_iterations],
            s=20,
            color=colors,
            zorder=2,
        )
        fig_ax.plot(
            self.residual_history[:n_iterations], linestyle="-", c="k", zorder=1
        )
        fig_ax.axhline(y=self.tolerance, c="blue", linewidth=0.5, zorder=0)
        fig_ax.set_title(f"{self.name}: residual plot")

        fig_ax.set_yscale("log")
        fig_ax.set_xlabel(r"iterations", fontsize=14)
        fig_ax.set_xlim([-1, n_iterations])
        fig_ax.get_xaxis().set_major_locator(MaxNLocator(integer=True))
        fig_ax.set_ylabel(r"$\log(||residuals||/||y_0||)$", fontsize=14)
        if logscale is not None:
            fig_ax.set_ylim(logscale)

        if save and filename is None:
            filename = f"{self.name}_residual_history.pdf"

        save_show_figure(fig, show, filename, fig_size=fig_size)

        return fig

    @abstractmethod
    def _run(self) -> None:  # noqa:D103
        # MDODiscipline does not declare this method as abstract on purpose,
        # but for MDAs this makes sense.
        pass
