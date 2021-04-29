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

"""Capabilities to run a sensitivity analysis.

This package contains:

- an abstract class :class:`.SensitivityAnalysis`
  to define the concept of sensitivity analysis,
- a factory :class:`.SensitivityAnalysisFactory`
  to create instances of :class:`.SensitivityAnalysis`,
- concrete classes implementing this abstract class:

  - :class:`.CorrelationAnalysis` (based on OpenTURNS capabilities)
  - :class:`.MorrisAnalysis`,
  - :class:`.SobolAnalysis` (based on OpenTURNS capabilities),
"""

from gemseo.uncertainty.sensitivity.correlation import CorrelationAnalysis  # noqa: F401
from gemseo.uncertainty.sensitivity.factory import (  # noqa: F401
    SensitivityAnalysisFactory,
)
from gemseo.uncertainty.sensitivity.morris import MorrisAnalysis  # noqa: F401
from gemseo.uncertainty.sensitivity.sobol import SobolAnalysis  # noqa: F401
