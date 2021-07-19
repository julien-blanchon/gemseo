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

"""Test the class Curves plotting samples of a 1D variable with curves."""

from __future__ import division, unicode_literals

import pytest
from matplotlib.testing.decorators import image_comparison
from numpy import array

from gemseo.core.dataset import Dataset
from gemseo.post.dataset.curves import Curves
from gemseo.utils.py23_compat import PY2

pytestmark = pytest.mark.skipif(
    PY2, reason="image comparison does not work with python 2"
)


@pytest.fixture(scope="module")
def dataset():
    """Dataset: A dataset containing two samples of the 1D variable 'output'.

    This variable is plotted over the 1D mesh: [[0], [1]].

    The samples are [0., 1.] and [1., 0.].
    """
    dataset = Dataset()
    sample1 = [0.0, 1.0]
    sample2 = [1.0, 0.0]
    data_array = array([sample1, sample2])
    dataset.set_from_array(data_array, variables=["output"], sizes={"output": 2})
    dataset.metadata["mesh"] = array([[0.0], [1.0]])
    return dataset


# the test parameters, it maps a test name to the inputs and references outputs:
# - the kwargs to be passed to Curves._plot
# - the expected file names without extension to be compared
TEST_PARAMETERS = {
    "without_option": ({}, ["Curves"]),
    "with_subsamples": ({"samples": [1]}, ["Curves_with_subsamples"]),
}


@pytest.mark.parametrize(
    "kwargs, baseline_images",
    TEST_PARAMETERS.values(),
    indirect=["baseline_images"],
    ids=TEST_PARAMETERS.keys(),
)
@image_comparison(None, extensions=["png"])
def test_plot(kwargs, baseline_images, dataset, pyplot_close_all):
    """Test images created by Curves._plot against references.

    Args:
        kwargs (dict): The optional arguments to pass to Curves._plot.
        baseline_images (list): The images to be compared with.
        dataset (Dataset): A dataset.
        pyplot_close_all: Prevents figures aggregation.
    """
    Curves(dataset)._plot(properties={}, mesh="mesh", variable="output", **kwargs)
