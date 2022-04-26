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
"""Draw lines from a :class:`.Dataset`.

A :class:`.Lines` plot represents variables vs samples using lines.
"""
from __future__ import division
from __future__ import unicode_literals

from typing import Optional
from typing import Sequence

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from gemseo.core.dataset import Dataset
from gemseo.post.dataset.dataset_plot import DatasetPlot


class Lines(DatasetPlot):
    """Plot sampled variables as lines."""

    def __init__(
        self,
        dataset,  # type: Dataset
        variables=None,  # type: Optional[Sequence[str]]
    ):  # type: (...) -> None
        """
        Args:
            variables: The names of the variables to plot.
        """
        super().__init__(dataset, variables=variables)

    def _plot(self) -> list[Figure]:
        x_data = range(len(self.dataset))
        variables = self._param.variables
        if variables is None:
            y_data = self.dataset.get_all_data(False, True)
            variables = y_data.keys()
        else:
            y_data = self.dataset[variables]

        plt.figure(figsize=self.figsize)
        self._set_color(len(variables))
        self._set_linestyle(len(variables), "-")
        for index, (name, value) in enumerate(y_data.items()):
            plt.plot(
                x_data,
                value,
                linestyle=self.linestyle[index],
                color=self.color[index],
                label=name,
            )

        plt.xlabel(self.xlabel)
        plt.ylabel(self.ylabel)
        plt.title(self.title)
        plt.legend(loc=self.legend_location)
        return [plt.gcf()]
