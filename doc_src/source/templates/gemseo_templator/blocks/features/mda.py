# Copyright 2021 IRT Saint-Exupéry, https://www.irt-saintexupery.com
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
from gemseo_templator.blocks.template import Block, WebLink

block = Block(
    title="MDA",
    description=(
        "Find the coupled state of a multidisciplinary system "
        "using a Multi-Disciplinary Analysis."
    ),
    url="algorithms/mda_algos.html",
    algorithms=[
        WebLink("Gauss-Seidel", anchor="mdagaussseidel"),
        WebLink("Jacobi", anchor="mdajacobi"),
        WebLink("MDAChain", anchor="mdachain"),
        WebLink("Newton-Raphson", anchor="mdanewtonraphson"),
        WebLink("Quasi-Newton", anchor="mdaquasinewton"),
        WebLink("Gauss-Seidel / Newton", anchor="gsnewtonmda"),
    ],
    examples="examples/mda/index.html",
    info="mdo/mda.html",
    options="algorithms/mda_algos.html",
)
