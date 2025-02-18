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
"""Draw a variable versus another from a :class:`.Dataset`.

A :class:`.YvsX` plot represents samples of a couple :math:`(x,y)` as a set of points
whose values are stored in a :class:`.Dataset`. The user can select the style of line or
markers, as well as the color.
"""
from __future__ import annotations

from matplotlib.axes import Axes
from matplotlib.figure import Figure

from gemseo.datasets.dataset import Dataset
from gemseo.post.dataset.dataset_plot import DatasetPlot
from gemseo.post.dataset.dataset_plot import VariableType


class YvsX(DatasetPlot):
    """Plot curve y versus x."""

    def __init__(self, dataset: Dataset, x: VariableType, y: VariableType) -> None:
        """
        Args:
            x: The name of the variable on the x-axis,
                with its optional component if not ``0``,
                e.g. ``("foo", 3)`` for the fourth component of the variable ``"foo"``.
            y: The name of the variable on the y-axis,
                with its optional component if not ``0``,
                e.g. ``("bar", 3)`` for the fourth component of the variable ``"bar"``.
        """  # noqa: D205, D212, D415
        super().__init__(
            dataset,
            x=self._force_variable_to_tuple(x),
            y=self._force_variable_to_tuple(y),
        )

    def _plot(
        self,
        fig: None | Figure = None,
        axes: None | Axes = None,
    ) -> list[Figure]:
        x, x_comp = self._param.x
        y, y_comp = self._param.y
        color = self.color or "blue"
        style = self.linestyle or "o"
        x_data = self.dataset.get_view(variable_names=x).to_numpy()[:, x_comp]
        y_data = self.dataset.get_view(variable_names=y).to_numpy()[:, y_comp]

        fig, axes = self._get_figure_and_axes(fig, axes)
        axes.plot(x_data, y_data, style, color=color)

        if self.dataset.variable_names_to_n_components[x] == 1:
            axes.set_xlabel(self.xlabel or x)
        else:
            axes.set_xlabel(self.xlabel or f"{x}({x_comp})")

        if self.dataset.variable_names_to_n_components[y] == 1:
            axes.set_ylabel(self.ylabel or y)
        else:
            axes.set_ylabel(self.ylabel or f"{y}({y_comp})")

        axes.set_title(self.title)

        return [fig]
