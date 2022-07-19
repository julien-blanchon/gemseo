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
#
# Contributors:
# - Pierre-Jean Barjhoux
# - Matthias De Lozzo
# - Jean-Christophe Giret
# - Gilberto Ruiz Jiménez
# - François Gallard
# - Charlie Vanaret
# - Antoine DECHAUME
import pytest
from gemseo.post.obj_constr_hist import ObjConstrHist
from gemseo.utils.testing import image_comparison

TEST_PARAMETERS = {
    "standardized": (True, ["ObjConstrHist_standardized"]),
    "unstandardized": (False, ["ObjConstrHist_unstandardized"]),
}


@pytest.mark.parametrize(
    "use_standardized_objective, baseline_images",
    TEST_PARAMETERS.values(),
    indirect=["baseline_images"],
    ids=TEST_PARAMETERS.keys(),
)
@image_comparison(None)
def test_common_scenario(
    use_standardized_objective, baseline_images, common_problem, pyplot_close_all
):
    """Check ObjConstrHist."""
    opt = ObjConstrHist(common_problem)
    common_problem.use_standardized_objective = use_standardized_objective
    opt.execute(constraint_names=["eq", "neg", "pos"], show=False, save=False)
