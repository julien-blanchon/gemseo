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
#                         documentation
#        :author: Matthias De Lozzo, Syver Doving Agdestein
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
r"""Scaling a variable with a statistical linear transformation.

The :class:`.StandardScaler` class implements the Standard scaling method
applying to some parameter :math:`z`:

.. math::

    \bar{z} := \text{offset} + \text{coefficient}\times z
    = \frac{z-\text{mean}(z)}{\text{std}(z)}

where :math:`\text{offset}=-\text{mean}(z)/\text{std}(z)` and
:math:`\text{coefficient}=1/\text{std}(z)`.

In this standard scaling method,
the scaling operation linearly transforms the original variable math:`z`
such that in the scaled space,
the original data have zero mean and unit standard deviation.

Warnings:

    When :math:`\text{std}(z)=0` and :math:`\text{mean}(z)\neq 0`,
    we use :math:`\bar{z}=\frac{z}{\text{mean}(z)}-1`.
    When :math:`\text{std}(z)=0` and :math:`\text{mean}(z)=0`,
    we use :math:`\bar{z}=z`.
"""
from __future__ import annotations

from numpy import ndarray
from numpy import where

from gemseo.mlearning.transformers.scaler.scaler import Scaler
from gemseo.mlearning.transformers.transformer import TransformerFitOptionType


class StandardScaler(Scaler):
    """Standard scaler."""

    def __init__(
        self,
        name: str = "StandardScaler",
        offset: float = 0.0,
        coefficient: float = 1.0,
    ) -> None:
        """
        Args:
            name: A name for this transformer.
            offset: The offset of the linear transformation.
            coefficient: The coefficient of the linear transformation.
        """
        super().__init__(name, offset, coefficient)

    def _fit(self, data: ndarray, *args: TransformerFitOptionType) -> None:
        _mean = data.mean(0)
        _std = data.std(0)
        is_constant = _std == 0
        self.coefficient = where(is_constant, 1 / where(_mean == 0, 1, _mean), 1 / _std)
        self.offset = where(is_constant, where(_mean == 0, 0, -1), -_mean / _std)
