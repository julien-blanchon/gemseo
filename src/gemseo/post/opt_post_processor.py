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
#        :author: Francois Gallard
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
"""Base class for optimization history post-processing."""
from __future__ import annotations

import inspect
from abc import abstractmethod
from os.path import abspath
from os.path import dirname
from os.path import exists
from os.path import join
from pathlib import Path
from typing import Any
from typing import ClassVar
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Union

from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec

from gemseo.algos.database import Database
from gemseo.algos.opt_problem import OptimizationProblem
from gemseo.core.grammars.errors import InvalidDataError
from gemseo.core.grammars.json_grammar import JSONGrammar
from gemseo.post.dataset.dataset_plot import DatasetPlot
from gemseo.utils.file_path_manager import FilePathManager
from gemseo.utils.matplotlib_figure import FigSizeType
from gemseo.utils.matplotlib_figure import save_show_figure
from gemseo.utils.metaclasses import ABCGoogleDocstringInheritanceMeta
from gemseo.utils.source_parsing import get_options_doc
from gemseo.utils.string_tools import pretty_repr
from gemseo.utils.string_tools import repr_variable

OptPostProcessorOptionType = Union[int, float, str, bool, Sequence[str], FigSizeType]
PlotOutputType = List[
    Tuple[Optional[str], Union[Figure, DatasetPlot], Optional[Dict[str, Sequence[str]]]]
]


class OptPostProcessor(metaclass=ABCGoogleDocstringInheritanceMeta):
    """Abstract class for optimization post-processing methods."""

    opt_problem: OptimizationProblem
    """The optimization problem."""

    database: Database
    """The database generated by the optimization problem."""

    materials_for_plotting: dict[Any, Any]
    """The materials to eventually rebuild the plot in another framework."""

    DEFAULT_FIG_SIZE = (11.0, 11.0)
    """The default width and height of the figure, in inches."""

    _obj_name: str
    """The name of the objective function as passed by the user."""

    _standardized_obj_name: str
    """The name of the objective function stored in the database."""

    _neg_obj_name: str
    """The name of the objective function starting with a '-'."""

    _X_MARGIN: ClassVar[float] = 0.1
    """The left and right margin for the x-axis."""

    _Y_MARGIN: ClassVar[float] = 0.05
    """The left and right margin for the y-axis."""

    def __init__(
        self,
        opt_problem: OptimizationProblem,
    ) -> None:
        """
        Args:
            opt_problem: The optimization problem to be post-processed.

        Raises:
            ValueError: If the JSON grammar file
                for the options of the post-processor does not exist.
        """  # noqa: D205, D212, D415
        self.opt_problem = opt_problem
        self._obj_name = opt_problem.get_objective_name(False)
        self._standardized_obj_name = opt_problem.get_objective_name()
        self._neg_obj_name = f"-{self._obj_name}"
        self.database = opt_problem.database
        comp_dir = abspath(dirname(inspect.getfile(OptPostProcessor)))
        self.opt_grammar = JSONGrammar("OptPostProcessor")
        self.opt_grammar.update_from_file(join(comp_dir, "OptPostProcessor.json"))
        self.opt_grammar.set_descriptions(get_options_doc(self.execute))
        self._update_grammar_from_class(self.__class__)

        # The data required to eventually rebuild the plot in another framework.
        self.materials_for_plotting = {}
        default_file_name = FilePathManager.to_snake_case(self.__class__.__name__)
        self.__file_path_manager = FilePathManager(
            FilePathManager.FileType.FIGURE, default_file_name
        )
        self._output_files = []
        self.__figures = {}
        self.__nameless_figure_counter = 0

    def _update_grammar_from_class(self, cls: type) -> None:
        """Update the grammar based on another class having a JSON grammar.

        Args:
            cls: The class.
        """
        name = f"{cls.__name__}_options"
        f_class = inspect.getfile(cls)
        comp_dir = abspath(dirname(f_class))
        schema_file = join(comp_dir, f"{name}.json")
        if not exists(schema_file):
            schema_file = join(comp_dir, "options", f"{name}.json")
        if not exists(schema_file):
            raise ValueError(
                "Options grammar for optimization post-processor does not exist, "
                f"expected: {comp_dir} or {join(comp_dir, name)}.json."
            )
        descriptions = {}
        if hasattr(self.__class__, "_run"):
            descriptions.update(get_options_doc(self.__class__._run))
        if hasattr(self.__class__, "_plot"):
            descriptions.update(get_options_doc(self.__class__._plot))
        self.opt_grammar.update_from_file(schema_file)
        self.opt_grammar.set_descriptions(descriptions)

    @property
    def _change_obj(self) -> bool:
        """Whether to change the objective value and names by using the opposite."""
        return not (
            self.opt_problem.minimize_objective
            or self.opt_problem.use_standardized_objective
        )

    @property
    def figures(self) -> dict[str, Figure]:
        """The Matplotlib figures indexed by a name, or the nameless figure counter."""
        return self.__figures

    @property
    def output_files(self) -> list[str]:
        """The paths to the output files."""
        return self._output_files

    def _add_figure(
        self,
        figure: Figure,
        file_name: str | None = None,
    ) -> None:
        """Add a figure.

        Args:
            figure: The figure to be added.
            file_name: The default name of the file to save the figure.
                If ``None``, use the nameless figure counter.
        """
        if file_name is None:
            self.__nameless_figure_counter += 1
            file_name = str(self.__nameless_figure_counter)

        self.__figures[file_name] = figure

    def execute(
        self,
        save: bool = True,
        show: bool = False,
        file_path: str | Path | None = None,
        directory_path: str | Path | None = None,
        file_name: str | None = None,
        file_extension: str | None = None,
        fig_size: FigSizeType | None = None,
        **options: OptPostProcessorOptionType,
    ) -> dict[str, Figure]:
        """Post-process the optimization problem.

        Args:
            save: If True, save the figure.
            show: If True, display the figure.
            file_path: The path of the file to save the figures.
                If the extension is missing, use ``file_extension``.
                If ``None``,
                create a file path
                from ``directory_path``, ``file_name`` and ``file_extension``.
            directory_path: The path of the directory to save the figures.
                If ``None``, use the current working directory.
            file_name: The name of the file to save the figures.
                If ``None``, use a default one generated by the post-processing.
            file_extension: A file extension, e.g. 'png', 'pdf', 'svg', ...
                If ``None``, use a default file extension.
            fig_size: The width and height of the figure in inches, e.g. ``(w, h)``.
                If ``None``, use the :attr:`.OptPostProcessor.DEFAULT_FIG_SIZE`
                of the post-processor.
            **options: The options of the post-processor.

        Returns:
            The figures, to be customized if not closed.

        Raises:
            ValueError: If the ``opt_problem.database`` is empty.
        """
        # convert file_path to string before grammar-based options checking

        self.check_options(
            save=save,
            show=show,
            file_path=file_path,
            file_name=file_name,
            directory_path=directory_path,
            file_extension=file_extension,
            fig_size=fig_size,
            **options,
        )
        if not self.opt_problem.database:
            raise ValueError(
                f"The post-processor {self.__class__.__name__} cannot be solved "
                "because the optimization problem was not solved."
            )

        self.__figures = self._run(
            save=save,
            show=show,
            file_path=file_path,
            file_name=file_name,
            file_extension=file_extension,
            directory_path=directory_path,
            fig_size=fig_size,
            **options,
        )
        return self.__figures

    def check_options(self, **options: OptPostProcessorOptionType) -> None:
        """Check the options of the post-processor.

        Args:
            **options: The options of the post-processor.

        Raises:
            InvalidDataError: If an option is invalid according to the grammar.
        """
        try:
            self.opt_grammar.validate(options)
        except InvalidDataError:
            raise InvalidDataError(
                f"Invalid options for post-processor {self.__class__.__name__}; "
                f"got {pretty_repr(options)}."
            )

    def _run(
        self,
        save: bool = True,
        show: bool = False,
        file_path: Path | None = None,
        directory_path: Path | None = None,
        file_name: str | None = None,
        file_extension: str | None = None,
        fig_size: FigSizeType | None = None,
        **options: OptPostProcessorOptionType,
    ) -> dict[str, Figure]:
        """Run the post-processor.

        Args:
            save: If True, save the figure.
            show: If True, display the figure.
            file_path: The path of the file to save the figures.
                If the extension is missing, use ``file_extension``.
                If ``None``,
                create a file path
                from ``directory_path``, ``file_name`` and ``file_extension``.
            directory_path: The path of the directory to save the figures.
                If ``None``, use the current working directory.
            file_name: The name of the file to save the figures.
                If ``None``, use a default one generated by the post-processing.
            file_extension: A file extension, e.g. 'png', 'pdf', 'svg', ...
                If ``None``, use a default file extension.
            fig_size: The width and height of the figure in inches, e.g. ``(w, h)``.
                If ``None``, use the :attr:`.OptPostProcessor.DEFAULT_FIG_SIZE`
                of the post-processor.
            **options: The options of the post-processor.

        Returns:
            The figures resulting from the post-processing of the optimization problem.
        """
        self._plot(**options)

        file_path = self.__file_path_manager.create_file_path(
            file_path=file_path,
            directory_path=directory_path,
            file_name=file_name,
            file_extension=file_extension,
        )

        for figure_name, figure in self.__figures.items():
            if save:
                if len(self.__figures) > 1:
                    fig_file_path = self.__file_path_manager.add_suffix(
                        file_path, figure_name
                    )
                else:
                    fig_file_path = file_path

                self._output_files.append(str(fig_file_path))

            else:
                fig_file_path = None

            save_show_figure(figure, show, fig_file_path, fig_size)

        return self.__figures

    @abstractmethod
    def _plot(self, **options: OptPostProcessorOptionType) -> None:
        """Create the figures.

        Args:
            **options: The post-processor options.
        """

    def _get_design_variable_names(
        self, variables: Iterable[str] = (), simplify: bool = False
    ) -> list[str]:
        """Create the names of the components of design variables as ``"name[i]"``.

        Args:
            variables: The design variables of interest.
                If ``None``, use all the design variables.
            simplify: Whether to use ``"[i]"`` when ``i>0`` instead of ``"name[i]"``.

        Returns:
            The names of the components of the design variables.
        """
        if not variables:
            variables = self.opt_problem.design_space.variable_names

        design_variable_names = []
        design_variable_sizes = self.opt_problem.design_space.variable_sizes
        for variable in variables:
            design_variable_size = design_variable_sizes[variable]
            design_variable_names.extend(
                [
                    repr_variable(
                        variable, index, size=design_variable_size, simplify=simplify
                    )
                    for index in range(design_variable_size)
                ]
            )

        return design_variable_names

    @staticmethod
    def _get_grid_layout() -> GridSpec:
        """Return a grid layout to place subplots within a figure.

        Returns:
            A grid layout to place subplots within a figure.
        """
        return GridSpec(1, 2, width_ratios=[15, 1], wspace=0.04, hspace=0.6)
