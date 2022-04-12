# -*- coding: utf-8 -*-
# Copyright 2021 IRT Saint Exupéry, https://www.irt-saintexupery.com
#
# This work is licensed under a BSD 0-Clause License.
#
# Permission to use, copy, modify, and/or distribute this software
# for any purpose with or without fee is hereby granted.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL
# WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL
# THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT,
# OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING
# FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
# NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION
# WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
# Contributors:
#    INITIAL AUTHORS - initial API and implementation and/or initial
#                         documentation
#        :author: Matthias De Lozzo
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
"""
Plug a surrogate discipline in a Scenario
=========================================

In this section we describe the usage of surrogate model in |g|,
which is implemented in the :class:`.SurrogateDiscipline` class.

A :class:`.SurrogateDiscipline` can be used to substitute a
:class:`.MDODiscipline` within a :class:`.Scenario`. This
:class:`.SurrogateDiscipline` is an evaluation of the :class:`.MDODiscipline`
and is faster to compute than the original discipline. It relies on a
:class:`.MLRegressionAlgo`. This comes at the price of computing a :term:`DOE`
on the original :class:`.MDODiscipline`, and validating the approximation. The
computations from which the approximation is built can be available, or can be
built using |g|' :term:`DOE` capabilities. See :ref:`sobieski_doe` and
:ref:`sellar_mdo`.

In |g|'s, the data used to build the surrogate model is taken from a
:class:`.Dataset` containing both inputs and outputs of the :term:`DOE`. This
:class:`.Dataset` may have been generated by |g| from a cache, using the
:meth:`.AbstractFullCache.export_to_dataset` method,
from a database, using the :meth:`.OptimizationProblem.export_to_dataset` method,
or from a NumPy array or
a text file using the :meth:`.Dataset.set_from_array` and
:meth:`.Dataset.set_from_file`.

Then, the surrogate discipline can be used as any other discipline in a
:class:`.MDOScenario`, a :class:`.DOEScenario`, or a :class:`.MDA`.
"""
from __future__ import division
from __future__ import unicode_literals

from gemseo.api import configure_logger
from gemseo.api import create_discipline
from gemseo.api import create_scenario
from gemseo.api import create_surrogate
from gemseo.core.dataset import Dataset
from gemseo.problems.sobieski.core.problem import SobieskiProblem
from numpy import array
from numpy import hstack
from numpy import vstack

configure_logger()


###############################################################################
# Create a surrogate discipline
# -----------------------------
#
# Create the learning dataset
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# If you already have available data from a :term:`DOE` produced externally,
# it is possible to create a :class:`.Dataset` and Step 1 ends here.
# For example, let us consider a synthetic dataset, with :math:`x`
# as input and :math:`y` as output, described as a numpy
# array. Then, we store these data in a :class:`.Dataset`:
#
variables = ["x", "y"]
sizes = {"x": 1, "y": 1}
groups = {"x": "inputs", "y": "outputs"}
data = vstack(
    (
        hstack((array([1.0]), array([1.0]))),
        hstack((array([2.0]), array([2.0]))),
    )
)
synthetic_dataset = Dataset()
synthetic_dataset.set_from_array(data, variables, sizes, groups)

#############################################################################
# If you do not have available data,the following paragraphs of Step 1 concern you.
#
# Here, we illustrate the generation of the training data using a :class:`.DOEScenario`,
# similarly to :ref:`sobieski_doe`, where more details are given.
#
# In this basic example, an :class:`.MDODiscipline` computing the mission
# performance (range) in the :ref:`SSBJ test case <sobieski_problem>` is
# sampled with a :class:`.DOEScenario`. Then, the generated database is used to
# build a :class:`.SurrogateDiscipline`.
#
# But more complex scenarios can be used in the same way: complete optimization
# processes or MDAs can be replaced by their surrogate counterparts. The right
# cache or database shall then be used to build the
# :class:`.SurrogateDiscipline`, but the main logic won't differ from this
# example.
#
# Firstly, we create the :class:`.MDODiscipline` by means of the API function
# :meth:`~gemseo.api.create_discipline`:
#

discipline = create_discipline("SobieskiMission")

##############################################################################
#
# .. _surrogates_design_space:
#
# Then, we read the :class:`.DesignSpace` of the :ref:`Sobieski problem
# <sobieski_problem>` and keep only the inputs of the Sobieski Mission
# "x_shared", "y_24", "y_34"
# as inputs of the DOE:
#
design_space = SobieskiProblem().design_space
design_space = design_space.filter(["x_shared", "y_24", "y_34"])

##############################################################################
#
# From this :class:`.MDODiscipline` and this :class:`.DesignSpace`,
# we build a :class:`.DOEScenario`
# by means of the API function :meth:`~gemseo.api.create_scenario`:
#
scenario = create_scenario(
    [discipline],
    "DisciplinaryOpt",
    objective_name="y_4",
    design_space=design_space,
    scenario_type="DOE",
)

##############################################################################
# Lastly, we execute the process with the :term:`LHS` algorithm and 30 samples.
scenario.execute({"n_samples": 30, "algo": "lhs"})
mission_dataset = scenario.export_to_dataset(opt_naming=False)

##############################################################################
# .. seealso::
#
#    In this tutorial, the :term:`DOE` is based on `pyDOE
#    <https://pythonhosted.org/pyDOE/>`_, however, several other designs are
#    available, based on the package or `OpenTURNS
#    <http://www.openturns.org/>`_. Some examples of these designs are plotted
#    in :ref:`doe_algos`.  To list the available :term:`DOE` algorithms in the
#    current |g| configuration, use
#    :meth:`gemseo.api.get_available_doe_algorithms`.

##############################################################################
# Create the :class:`.SurrogateDiscipline`
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# From this :class:`.Dataset`, we can build a :class:`.SurrogateDiscipline`
# of the :class:`.MDODiscipline`.
#
# Indeed, by means of the API function :class:`~gemseo.api.create_surrogate`,
# we create the :class:`.SurrogateDiscipline` from the dataset,
# which can be executed as any other :term:`discipline`.
#
# Precisely,
# by means of the API function :meth:`~gemseo.api.create_surrogate`,
# we create a :class:`.SurrogateDiscipline` relying on a :class:`.LinearRegression`
# and inheriting from :class:`.MDODiscipline`:

synthetic_surrogate = create_surrogate("LinearRegression", synthetic_dataset)

##############################################################################
# .. seealso::
#
#    Note that a subset of the inputs and outputs to be used to build the
#    :class:`.SurrogateDiscipline` may be specified by the user if needed,
#    mainly to avoid unnecessary computations.
#
# Then, we execute it as any :class:`.MDODiscipline`:
input_data = {"x": array([2.0])}
out = synthetic_surrogate.execute(input_data)
print(out["y"])

##############################################################################
# In our study case, from the :term:`DOE` built at Step 1,
# we build a :class:`.RBFRegression`  of :math:`y_4`
# representing the range in function of L/D:
range_surrogate = create_surrogate("RBFRegression", mission_dataset)

##############################################################################
# Use the :class:`.SurrogateDiscipline` in MDO
# --------------------------------------------
#
# The obtained :class:`.SurrogateDiscipline` can be used in any
# :class:`.Scenario`, such as a :class:`.DOEScenario` or :class:`.MDOScenario`.
# We see here that the :meth:`.MDODiscipline.execute` method can be used as in
# any other discipline to compute the outputs for given inputs:

for i in range(5):
    lod = i * 2.0
    y_4_pred = range_surrogate.execute({"y_24": array([lod])})["y_4"]
    print("Surrogate range (L/D = {}) = {}".format(lod, y_4_pred))

##############################################################################
# And we can build and execute an optimization scenario from it.
# The design variables are "y_24". The Jacobian matrix is computed by finite
# differences by default for surrogates, except for the
# :class:`.SurrogateDiscipline` relying on :class:`.LinearRegression` which has
# an analytical (and constant) Jacobian.
design_space = design_space.filter(["y_24"])
scenario = create_scenario(
    range_surrogate,
    formulation="DisciplinaryOpt",
    objective_name="y_4",
    design_space=design_space,
    scenario_type="MDO",
    maximize_objective=True,
)
scenario.execute({"max_iter": 30, "algo": "L-BFGS-B"})

##############################################################################
# Available surrogate models
# --------------------------
#
# Currently, the following surrogate models are available:
#
# - Linear regression,
#   based on the `Scikit-learn <http://scikit-learn.org/stable/>`_ library,
#   for that use the :class:`.LinearRegression` class.
# - Polynomial regression,
#   based on the `Scikit-learn  <http://scikit-learn.org/stable/>`_ library,
#   for that use the :class:`.PolynomialRegression` class,
# - Gaussian processes (also known as Kriging),
#   based on the `Scikit-learn  <http://scikit-learn.org/stable/>`_ library,
#   for that use the :class:`.GaussianProcessRegression` class,
# - Mixture of experts, for that use the :class:`.MixtureOfExperts` class,
# - Random forest models,
#   based on the `Scikit-learn # <http://scikit-learn.org/stable/>`_ library,
#   for that use the :class:`.RandomForestRegressor` class.
# - RBF models (Radial Basis Functions),
#   using the `SciPy  <http://www.scipy.org/>`_ library,
#   for that use the :class:`.RBFRegression` class.
# - PCE models (Polynomial Chaos Expansion),
#   based on the `OpenTURNS  <http://www.openturns.org/>`_ library,
#   for that use the :class:`.PCERegression` class.
#
# To understand the detailed behavior of the models, please go to the
# documentation of the used packages.
#
# Extending surrogate models --------------------------
#
# All surrogate models work the same way: the :class:`.MLRegressionAlgo` base
# class shall be extended. See :ref:`extending-gemseo` to learn how to run
# |g|
# with external Python modules. Then, the :class:`.RegressionModelFactory` can
# build the new :class:`.MLRegressionAlgo` automatically from its regression
# algorithm name and options. This factory is called by the constructor of
# :class:`.SurrogateDiscipline`.
#
# .. seealso::
#
#    More generally, |g| provides extension mechanisms to integrate external :DOE
#    and optimization algorithms, disciplines, MDAs and surrogate models.
