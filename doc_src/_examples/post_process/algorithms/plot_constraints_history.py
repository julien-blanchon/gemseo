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
#                           documentation
#        :author: Matthias De Lozzo
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
"""
Constraints history
===================

In this example, we illustrate the use of the :class:`.ConstraintsHistory` plot
on the Sobieski's SSBJ problem.
"""
from __future__ import annotations

from gemseo import configure_logger
from gemseo import create_discipline
from gemseo import create_scenario
from gemseo.problems.sobieski.core.problem import SobieskiProblem

# %%
# Import
# ------
# The first step is to import some functions from the API
# and a method to get the design space.

configure_logger()

# %%
# Description
# -----------
#
# The :class:`.ConstraintsHistory` post-processing
# plots the constraints functions history in line charts
# with violation indication by color on the background.
#
# This plot is more precise than the constraint plot provided by the
# :ref:`opt_history_view` but scales less with the number of constraints.

# %%
# Create disciplines
# ------------------
# At this point, we instantiate the disciplines of Sobieski's SSBJ problem:
# Propulsion, Aerodynamics, Structure and Mission
disciplines = create_discipline(
    [
        "SobieskiPropulsion",
        "SobieskiAerodynamics",
        "SobieskiStructure",
        "SobieskiMission",
    ]
)

# %%
# Create design space
# -------------------
# We also read the design space from the :class:`.SobieskiProblem`.
design_space = SobieskiProblem().design_space

# %%
# Create and execute scenario
# ---------------------------
# The next step is to build an MDO scenario in order to maximize the range,
# encoded 'y_4', with respect to the design parameters, while satisfying the
# inequality constraints 'g_1', 'g_2' and 'g_3'. We can use the MDF formulation,
# the SLSQP optimization algorithm
# and a maximum number of iterations equal to 100.
scenario = create_scenario(
    disciplines,
    formulation="MDF",
    objective_name="y_4",
    maximize_objective=True,
    design_space=design_space,
)
scenario.set_differentiation_method()
all_constraints = ["g_1", "g_2", "g_3"]
for constraint in all_constraints:
    scenario.add_constraint(constraint, "ineq")
scenario.execute({"algo": "SLSQP", "max_iter": 10})

# %%
# Post-process scenario
# ---------------------
# Lastly, we post-process the scenario by means of the
# :class:`.ConstraintsHistory` plot which plots the history of constraints
# passed as argument by the user. Each constraint history is represented by
# a subplot where the value of the constraints is drawn by a line. Moreover,
# the background color represents a qualitative view of these values: active
# areas are white, violated ones are red and satisfied ones are green.

# %%
# .. tip::
#
#    Each post-processing method requires different inputs and offers a variety
#    of customization options. Use the API function
#    :func:`.get_post_processing_options_schema` to print a table with
#    the options for any post-processing algorithm.
#    Or refer to our dedicated page:
#    :ref:`gen_post_algos`.

scenario.post_process(
    "ConstraintsHistory",
    constraint_names=all_constraints,
    save=False,
    show=True,
)
