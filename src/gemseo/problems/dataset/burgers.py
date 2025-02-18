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
#        :author: Syver Doving Agdestein
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
r"""
Burgers dataset
===============

This :class:`.Dataset` contains solutions to the Burgers' equation with
periodic boundary conditions on the interval :math:`[0, 2\pi]` for different
time steps:

.. math::

   u_t + u u_x = \nu u_{xx},

An analytical expression can be obtained for the solution, using the Cole-Hopf
transform:

.. math::

   u(t, x) = - 2 \nu \frac{\phi'}{\phi},

where :math:`\phi` is solution to the heat equation
:math:`\phi_t = \nu \phi_{xx}`.

This :class:`.Dataset` is based on a full-factorial
design of experiments. Each sample corresponds to a given time step :math:`t`,
while each feature corresponds to a given spatial point :math:`x`.

`More information about Burgers' equation
<https://en.wikipedia.org/wiki/Burgers%27_equation>`_
"""
from __future__ import annotations

from numpy import exp
from numpy import hstack
from numpy import linspace
from numpy import newaxis
from numpy import pi
from numpy import square

from gemseo.core.discipline import MDODiscipline
from gemseo.datasets.io_dataset import IODataset


class BurgersDiscipline(MDODiscipline):
    def __init__(self) -> None:
        super().__init__()
        self.input_grammar.initialize_from_data_names(["x", "z"])
        self.output_grammar.initialize_from_data_names(["f", "g"])


def create_burgers_dataset(
    n_samples: int = 30,
    n_x: int = 501,
    fluid_viscosity: float = 0.1,
    categorize: bool = True,
) -> IODataset:
    """Burgers dataset parametrization.

    Args:
        n_samples: The number of samples.
        n_x: The number of spatial points.
        fluid_viscosity: The fluid viscosity.
        categorize: Whether to distinguish
            between the different groups of variables.

    Returns:
        The Burgers dataset.
    """
    time = linspace(0, 2, n_samples)[:, newaxis]
    space = linspace(0, 2 * pi, n_x)[newaxis, :]
    visc = fluid_viscosity

    alpha = space - 4 * time
    alpha_2 = square(alpha)
    beta = 4 * visc * (time + 1)
    gamma = space - 4 * time - 2 * pi
    gamma_2 = square(gamma)
    phi = exp(-alpha_2 / beta) + exp(-gamma_2 / beta)
    phi_deriv = -2 * alpha / beta * exp(-alpha_2 / beta)
    phi_deriv -= 2 * gamma / beta * exp(-gamma_2 / beta)
    u_t = -2 * visc / phi * phi_deriv

    if categorize:
        groups = {"t": IODataset.INPUT_GROUP, "u_t": IODataset.OUTPUT_GROUP}
    else:
        groups = None

    data = hstack([time, u_t])

    dataset = IODataset.from_array(data, ["t", "u_t"], {"t": 1, "u_t": n_x}, groups)
    dataset.name = "Burgers"
    dataset.misc["x"] = [[node] for node in space[0]]
    dataset.misc["nu"] = visc
    return dataset
