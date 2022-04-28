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
#    INITIAL AUTHORS - initial API and implementation and/or initial
#                           documentation
#        :author: Matthias De Lozzo
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
"""An abstract class to plot data from a :class:`.Dataset`.

The :mod:`~gemseo.post.dataset.dataset_plot` module
implements the abstract :class:`.DatasetPlot` class
whose purpose is to build a graphical representation of a :class:`.Dataset`
and to display it on screen or save it to a file.

This abstract class has to be overloaded by concrete ones
implementing at least method :meth:`!DatasetPlot._run`.
"""
from __future__ import annotations

from collections import namedtuple
from numbers import Number
from typing import Any
from typing import Final
from typing import Iterable
from typing import List
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import TYPE_CHECKING
from typing import Union

from docstring_inheritance import GoogleDocstringInheritanceMeta
from matplotlib.axes import Axes
from numpy import linspace

from gemseo.utils.file_path_manager import FilePathManager
from gemseo.utils.file_path_manager import FileType
from gemseo.utils.matplotlib_figure import save_show_figure

if TYPE_CHECKING:
    from gemseo.core.dataset import Dataset

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from six import string_types

from gemseo.utils.py23_compat import Path

DatasetPlotPropertyType = Union[str, int, float, Sequence[Union[str, int, float]]]


class DatasetPlot(metaclass=GoogleDocstringInheritanceMeta):
    """Abstract class for plotting a dataset."""

    dataset: Dataset
    """The dataset to be plotted."""

    COLOR: Final[str] = "color"
    COLORMAP: Final[str] = "colormap"
    FIGSIZE_X: Final[str] = "figsize_x"
    FIGSIZE_Y: Final[str] = "figsize_y"
    LINESTYLE: Final[str] = "linestyle"

    def __init__(
        self,
        dataset,  # type: Dataset
        **kwargs,  # type: Any
    ):  # type: (...) -> None
        """
        Args:
            dataset: The dataset containing the data to plot.

        Raises:
            ValueError: If the dataset is empty.
        """
        param = namedtuple(f"{self.__class__.__name__}Parameters", kwargs.keys())
        self._param = param(**kwargs)

        if dataset.is_empty():
            raise ValueError("Dataset is empty.")

        self.dataset = dataset
        self.__title = None
        self.__xlabel = None
        self.__ylabel = None
        self.__zlabel = None
        self.__font_size = 10
        self.__xmin = None
        self.__xmax = None
        self.__ymin = None
        self.__ymax = None
        self.__zmin = None
        self.__zmax = None
        self.__rmin = None
        self.__rmax = None
        self.__line_style = None
        self.__color = None
        self.__figsize = (6.4, 4.8)
        self.__colormap = "rainbow"
        self.__legend_location = "best"
        default_name = FilePathManager.to_snake_case(self.__class__.__name__)
        self.__file_path_manager = FilePathManager(
            FileType.FIGURE, default_name=default_name
        )
        self.__output_files = []
        self.__names_to_labels = {}

    @property
    def output_files(self):  # type: (...) -> List[str]
        """The paths to the output files."""
        return self.__output_files

    @property
    def legend_location(self):  # type: (...) -> str
        """The location of the legend."""
        return self.__legend_location

    @legend_location.setter
    def legend_location(self, value):
        self.__legend_location = value

    @property
    def colormap(self):  # type: (...) -> str
        """The color map."""
        return self.__colormap

    @colormap.setter
    def colormap(self, value):
        self.__colormap = value

    @property
    def figsize(self):  # type: (...) -> Tuple[float,float]
        """The figure size."""
        return self.__figsize

    @property
    def figsize_x(self):  # type: (...) -> float
        """The x-component of figure size."""
        return self.__figsize[0]

    @figsize_x.setter
    def figsize_x(self, value):
        self.__figsize = (value, self.figsize_y)

    @property
    def figsize_y(self):  # type: (...) -> float
        """The y-component of figure size."""
        return self.__figsize[1]

    @figsize_y.setter
    def figsize_y(self, value):
        self.__figsize = (self.figsize_x, value)

    @property
    def color(self):  # type: (...) -> str
        """The color of the series."""
        return self.__color

    @color.setter
    def color(self, value):
        self.__color = value

    @property
    def linestyle(self):  # type: (...) -> str
        """The line style of the series."""
        return self.__line_style

    @linestyle.setter
    def linestyle(self, value):
        self.__line_style = value

    @property
    def title(self):  # type: (...) -> str
        """The title of the plot."""
        return self.__title

    @title.setter
    def title(self, value):
        self.__title = value

    @property
    def xlabel(self):  # type: (...) -> str
        """The label for the x-axis."""
        return self.__xlabel

    @xlabel.setter
    def xlabel(self, value):
        self.__xlabel = value

    @property
    def ylabel(self):  # type: (...) -> str
        """The label for the y-axis."""
        return self.__ylabel

    @ylabel.setter
    def ylabel(self, value):
        self.__ylabel = value

    @property
    def zlabel(self):  # type: (...) -> str
        """The label for the z-axis."""
        return self.__zlabel

    @zlabel.setter
    def zlabel(self, value):
        self.__zlabel = value

    @property
    def font_size(self):  # type: (...) -> int
        """The font size."""
        return self.__font_size

    @font_size.setter
    def font_size(self, value):
        self.__font_size = value

    @property
    def xmin(self):  # type: (...) -> float
        """The minimum value on the x-axis."""
        return self.__xmin

    @xmin.setter
    def xmin(self, value):
        self.__xmin = value

    @property
    def xmax(self):  # type: (...) -> float
        """The maximum value on the x-axis."""
        return self.__xmax

    @xmax.setter
    def xmax(self, value):
        self.__xmax = value

    @property
    def ymin(self):  # type: (...) -> float
        """The minimum value on the y-axis."""
        return self.__ymin

    @ymin.setter
    def ymin(self, value):
        self.__ymin = value

    @property
    def ymax(self):  # type: (...) -> float
        """The maximum value on the y-axis."""
        return self.__ymax

    @ymax.setter
    def ymax(self, value):
        self.__ymax = value

    @property
    def rmin(self):  # type: (...) -> float
        """The minimum value on the r-axis."""
        return self.__rmin

    @rmin.setter
    def rmin(self, value):
        self.__rmin = value

    @property
    def rmax(self):  # type: (...) -> float
        """The maximum value on the r-axis."""
        return self.__rmax

    @rmax.setter
    def rmax(self, value):
        self.__rmax = value

    @property
    def zmin(self):
        """The minimum value on the z-axis."""
        return self.__zmin

    @zmin.setter
    def zmin(self, value):
        self.__zmin = value

    @property
    def zmax(self):  # type: (...) -> float
        """The maximum value on the z-axis."""
        return self.__zmax

    @zmax.setter
    def zmax(self, value):
        self.__zmax = value

    def execute(
        self,
        save=True,  # type: bool
        show=False,  # type: bool
        file_path=None,  # type: Optional[Union[str,Path]]
        directory_path=None,  # type: Optional[Union[str,Path]]
        file_name=None,  # type: Optional[str]
        file_format=None,  # type: Optional[str]
        properties=None,  # type: Optional[Mapping[str,DatasetPlotPropertyType]]
        fig: None | Figure = None,
        axes: None | Axes = None,
        **plot_options,
    ):  # type: (...) -> List[Figure]
        """Execute the post processing.

        Args:
            save: If True, save the plot.
            show: If True, display the plot.
            file_path: The path of the file to save the figures.
                If None,
                create a file path
                from ``directory_path``, ``file_name`` and ``file_format``.
            directory_path: The path of the directory to save the figures.
                If None, use the current working directory.
            file_name: The name of the file to save the figures.
                If None, use a default one generated by the post-processing.
            file_format: A file format, e.g. 'png', 'pdf', 'svg', ...
                If None, use a default file extension.
            properties: The general properties of a :class:`.DatasetPlot`.
            fig: The figure to plot the data.
                If ``None``, create a new one.
            axes: The axes to plot the data.
                If ``None``, create new ones.
            **plot_options: The options of the current class
                inheriting from :class:`.DatasetPlot`.

        Returns:
            The figures.

        Raises:
            AttributeError: When the name of a property is not the name of an attribute.
        """
        properties = properties or {}
        for name, value in properties.items():
            if not hasattr(self, name):
                raise AttributeError(
                    f"{name} is not an attribute of {self.__class__.__name__}."
                )
            setattr(self, name, value)

        if file_path is not None:
            file_path = Path(file_path)

        file_path = self.__file_path_manager.create_file_path(
            file_path=file_path,
            directory_path=directory_path,
            file_name=file_name,
            file_extension=file_format,
        )
        return self._run(save, show, file_path, fig, axes, **plot_options)

    def _run(
        self,
        save,  # type:bool
        show,  # type: bool
        file_path,  # type: Path
        fig: None | Figure,
        axes: None | Axes,
        **plot_options,
    ):  # type: (...)-> List[Figure]
        """Create the post processing and save or display it.

        Args:
            save: If True, save the plot on the disk.
            show: If True, display the plot.
            file_path: The file path.
            fig: The figure to plot the data.
                If ``None``, create a new one.
            axes: The axes to plot the data.
                If ``None``, create new ones.
            **plot_options: The options of the current class
                inheriting from :class:`.DatasetPlot`.

        Returns:
            The figures.
        """
        if plot_options:
            self._param = self._param._replace(**plot_options)

        figures = self._plot(fig=fig, axes=axes)
        if fig or axes:
            return []

        for index, sub_figure in enumerate(figures):
            if save:
                if len(figures) > 1:
                    fig_file_path = self.__file_path_manager.add_suffix(
                        file_path, index
                    )
                else:
                    fig_file_path = file_path
                self.__output_files.append(str(fig_file_path))

            else:
                fig_file_path = None

            save_show_figure(
                sub_figure,
                show,
                fig_file_path,
            )

        return figures

    def _plot(
        self,
        fig: None | Figure = None,
        axes: None | Axes = None,
    ) -> list[Figure]:
        """Define the way as the dataset is plotted.

        Args:
            fig: The figure to plot the data.
                If ``None``, create a new one.
            axes: The axes to plot the data.
                If ``None``, create new ones.

        Returns:
            The figures.
        """
        raise NotImplementedError

    def _get_variables_names(
        self,
        dataframe_columns,  # type: Iterable[Tuple]
    ):  # type: (...) -> List[str]
        """Return the names of the variables from the columns of a pandas DataFrame.

        Args:
            dataframe_columns: The columns of a pandas DataFrame.

        Returns:
            The names of the variables.
        """
        new_columns = []
        for column in dataframe_columns:
            name = self._get_component_name(column[1], column[2], self.dataset.sizes)
            new_columns.append(name)

        return new_columns

    @staticmethod
    def _get_component_name(
        name: str, component: int, names_to_sizes: Mapping[str, int]
    ) -> str:
        """Return the name of a variable component.

        Args:
            name: The name of the variable.
            component: The component of the variable.
            names_to_sizes: The sizes of the variables.

        Returns:
            The name of the variable component.
        """
        if names_to_sizes[name] == 1:
            return name
        else:
            return f"{name}({component})"

    def _get_label(
        self,
        variable,  # type: Union[str,Tuple[str,int]]
    ):  # type: (...) -> Tuple[str,Tuple[str, int]]
        """Return the label related to a variable name and a refactored variable name.

        Args:
            variable: The name of a variable,
                either a string (e.g. "x") or a (name, component) tuple (e.g. ("x", 0)).

        Returns:
            The label related to a variable, e.g. "x(0)",
            as well as the refactored variable name, e.g. (x,0).
        """
        error_message = (
            "'variable' must be either a string or a tuple"
            " whose first component is a string and second"
            " one is an integer"
        )
        if isinstance(variable, string_types):
            label = variable
            variable = (self.dataset.get_group(variable), variable, "0")
        elif hasattr(variable, "__len__") and len(variable) == 3:
            is_string = isinstance(variable[0], string_types)
            is_string = is_string and isinstance(variable[1], string_types)
            is_number = isinstance(variable[2], Number)
            if is_string and is_number:
                label = "{}({})".format(variable[1], variable[2])
                variable[2] = str(variable[2])
                variable = tuple(variable)
            else:
                raise TypeError(error_message)
        else:
            raise TypeError(error_message)
        return label, variable

    def _set_color(
        self,
        n_items,  # type: int
    ):  # type: (...) -> None
        """Set the colors of the items to be plotted.

        Args:
            n_items: The number of items to be plotted.
        """
        colormap = plt.cm.get_cmap(self.colormap)
        default_color = [colormap(color) for color in linspace(0, 1, n_items)]
        self.color = self.color or default_color
        if isinstance(self.color, string_types):
            self.color = [self.color] * n_items

    def _set_linestyle(
        self,
        n_items,  # type: int
        default_value,  # type: str
    ):  # type: (...) -> None
        """Set the line style of the items to be plotted.

        Args:
            n_items: The number of items to be plotted.
            default_value: The default line style.
        """

        self.linestyle = self.linestyle or default_value
        if isinstance(self.linestyle, string_types):
            self.linestyle = [self.linestyle] * n_items

    @property
    def labels(self):  # type: (...) -> Mapping[str,str]
        """The labels of the variables."""
        return self.__names_to_labels

    @labels.setter
    def labels(
        self, names_to_labels  # type: Mapping[str,str]
    ):  # type: (...) -> None
        self.__names_to_labels = names_to_labels

    def _get_figure_and_axes(
        self,
        fig: Figure | None,
        axes: Axes | None,
        figsize: tuple[float, float] | None = None,
    ) -> tuple[Figure, Axes]:
        """Return the figure and axes to plot the data.

        Args:
            fig: The figure to plot the data.
                If ``None``, create a new one.
            axes: The axes to plot the data.
                If ``None``, create new ones.
            figsize: The width and height of the figure in inches.
                If ``None``, use the default ``figsize``.

        Returns:
            The figure and axis to plot the data.
        """
        if fig is None:
            if axes is not None:
                raise ValueError(
                    "The figure associated with the given axes is missing."
                )

            return plt.subplots(figsize=figsize or self.figsize)

        if axes is None:
            raise ValueError("The axes associated with the given figure are missing.")

        return fig, axes
