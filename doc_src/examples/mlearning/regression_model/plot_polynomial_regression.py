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
#        :author: Matthias De Lozzo, Syver Doving Agdestein
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
"""
Polynomial regression
=====================

We want to approximate a discipline with two inputs and two outputs:

- :math:`y_1=1+2x_1+3x_2`
- :math:`y_2=-1-2x_1-3x_2`

over the unit hypercube :math:`[0,1]\\times[0,1]`.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from numpy import array

from gemseo.api import (
    configure_logger,
    create_design_space,
    create_discipline,
    create_scenario,
)
from gemseo.mlearning.api import create_regression_model

configure_logger()


###############################################################################
# Create the discipline to learn
# ------------------------------
# We can implement this analytic discipline by means of the
# :class:`~gemseo.core.analytic_discipline.AnalyticDiscipline` class.
expressions_dict = {
    "y_1": "1 + 2*x_1 + 3*x_2 + x_1**2",
    "y_2": "-1 - 2*x_1 + x_1*x_2 - 3*x_2**2",
}
discipline = create_discipline(
    "AnalyticDiscipline", name="func", expressions_dict=expressions_dict
)

###############################################################################
# Create the input sampling space
# -------------------------------
# We create the input sampling space by adding the variables one by one.
design_space = create_design_space()
design_space.add_variable("x_1", l_b=0.0, u_b=1.0)
design_space.add_variable("x_2", l_b=0.0, u_b=1.0)

###############################################################################
# Create the learning set
# -----------------------
# We can build a learning set by means of a
# :class:`~gemseo.core.doe_scenario.DOEScenario` with a full factorial design of
# experiments. The number of samples can be equal to 9 for example.
discipline.set_cache_policy(discipline.MEMORY_FULL_CACHE)
scenario = create_scenario(
    [discipline], "DisciplinaryOpt", "y_1", design_space, scenario_type="DOE"
)
scenario.execute({"algo": "fullfact", "n_samples": 9})

###############################################################################
# Create the regression model
# ---------------------------
# Then, we build the linear regression model from the discipline cache and
# displays this model.
dataset = discipline.cache.export_to_dataset()
model = create_regression_model(
    "PolynomialRegression", data=dataset, degree=2, transformer=None
)
model.learn()
print(model)

###############################################################################
# Predict output
# --------------
# Once it is built, we can use it for prediction.
input_value = {"x_1": array([1.0]), "x_2": array([2.0])}
output_value = model.predict(input_value)
print(output_value)

###############################################################################
# Predict Jacobian
# ----------------
# We can also use it to predict the jacobian of the discipline.
jacobian_value = model.predict_jacobian(input_value)
print(jacobian_value)

###############################################################################
# Get intercept
# -------------
# In addition, it is possible to access the intercept of the model,
# either directly or by means of a method returning either a dictionary
# (default option) or an array.
print(model.intercept)
print(model.get_intercept())

###############################################################################
# Get coefficients
# ----------------
# In addition, it is possible to access the coefficients of the model,
# either directly or by means of a method returning either a dictionary
# (default option) or an array.
print(model.coefficients)
