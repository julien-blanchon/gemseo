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
#        :author: Pierre-Jean Barjhoux
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
"""Plot the constraints on a radar chart at a given database index."""
from __future__ import annotations

import logging
from typing import Iterable

from numpy import vstack
from numpy import zeros

from gemseo.datasets.dataset import Dataset
from gemseo.post.dataset.radar_chart import RadarChart as RadarChartPost
from gemseo.post.opt_post_processor import OptPostProcessor

LOGGER = logging.getLogger(__name__)


class RadarChart(OptPostProcessor):
    """Plot the constraints on a radar chart at a given database index."""

    OPTIMUM = "opt"
    """str: The tag related to the database index at which the optimum is located."""

    def _plot(
        self,
        constraint_names: Iterable[str] | None = None,
        iteration: int | RadarChart.OPTIMUM = OPTIMUM,
        show_names_radially: bool = False,
    ) -> None:
        r"""
        Args:
            constraint_names: The names of the constraints.
                If None, use all the constraints.
            iteration: Either an iteration in :math:`-N,\ldots,-1,1,`ldots,N`
                or the tag :attr:`.OPTIMUM` for the iteration
                at which the optimum is located,
                where :math:`N` is the length of the database.
            show_names_radially: Whether to write the names of the constraints
                in the radial direction.
                Otherwise, write them horizontally.
                The radial direction can be useful for a high number of constraints.

        Raises:
            ValueError: When a requested name is not a constraint
                or when the requested iteration is neither a database index
                nor the tag ``"opt"``.
        """  # noqa: D205, D212, D415
        if constraint_names is None:
            constraint_names = self.opt_problem.get_constraint_names()
        else:
            constraint_names = self.opt_problem.get_function_names(constraint_names)
            invalid_names = sorted(
                set(constraint_names) - set(self.opt_problem.get_constraint_names())
            )
            if invalid_names:
                raise ValueError(
                    f"The names {invalid_names} are not names of constraints "
                    "stored in the database."
                )

        n_iterations = len(self.database)
        if iteration != self.OPTIMUM and not 1 <= abs(iteration) <= n_iterations:
            raise ValueError(
                f"The requested iteration {iteration} is neither "
                f"in ({-n_iterations},...,-1,1,...,{n_iterations}) "
                f"nor equal to the tag {self.OPTIMUM}."
            )

        constraint_values, constraint_names, _ = self.database.get_history_array(
            function_names=constraint_names, with_x_vect=False
        )

        if iteration == self.OPTIMUM:
            title_suffix = " (optimum)"
            iteration = self.opt_problem.solution.optimum_index
        else:
            title_suffix = ""

        constraint_values = constraint_values[iteration, :].ravel()

        dataset = Dataset(dataset_name="Constraints")
        values = vstack((constraint_values, zeros(len(constraint_values))))
        dataset.add_group(
            dataset.DEFAULT_GROUP,
            values,
            constraint_names,
            {name: 1 for name in constraint_names},
        )
        dataset.index = ["computed constraints", "limit constraint"]

        if iteration < 0:
            iteration = n_iterations + iteration

        radar = RadarChartPost(dataset)
        radar.linestyle = ["-", "--"]
        radar.color = ["k", "r"]
        radar.title = f"Constraints at iteration {iteration}{title_suffix}"

        figures = radar.execute(
            save=False, display_zero=False, radial_ticks=show_names_radially
        )
        for figure in figures:
            self._add_figure(figure)
