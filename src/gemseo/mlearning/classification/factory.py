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
#        :author: Matthias De Lozzo, Syver Doving Agdestein
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
"""
Classification model factory
============================

This module contains a factory to instantiate a :class:`.MLClassificationAlgo`
from its class name. The class can be internal to |g| or located in an
external module whose path is provided to the constructor. It also provides a
list of available classification models and allows you to test if a
classification model type is available.
"""
from __future__ import absolute_import, division, unicode_literals

import logging

from gemseo.core.factory import Factory
from gemseo.mlearning.classification.classification import MLClassificationAlgo
from gemseo.mlearning.core.factory import MLAlgoFactory

LOGGER = logging.getLogger(__name__)


class ClassificationModelFactory(MLAlgoFactory):
    """This factory instantiates a :class:`.MLRegressionAlgo` from its class name.

    The class can be internal to |g| or located in an external module whose path is
    provided to the constructor.
    """

    def __init__(self):
        """Initializes the factory: scans the directories to search for subclasses of
        :class:`.MLClassificationAlgo`.

        Searches in "GEMSEO_PATH" and gemseo.mlearning.classification.
        """
        super(ClassificationModelFactory, self).__init__()
        self.factory = Factory(
            MLClassificationAlgo, ("gemseo.mlearning.classification",)
        )
