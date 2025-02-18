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
#    INITIAL AUTHORS - API and implementation and/or documentation
#       :author: Remi Lafage
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
"""Creation of a XDSM diagram from a scenario.

The :class:`.XDSMizer` generates a JSON file.

The latter is used by the
`XDSMjs javascript library <https://github.com/OneraHub/XDSMjs>`_
to produce an interactive web XDSM
and by the pyxdsm python library
to produce TIKZ and PDF versions of the XDSM.

For more information, see:
A. B. Lambe and J. R. R. A. Martins, “Extensions to the Design Structure Matrix for
the Description of Multidisciplinary Design, Analysis, and Optimization Processes”,
Structural and Multidisciplinary Optimization, vol. 46, no. 2, p. 273-284, 2012.
"""
from __future__ import annotations

import logging
from json import dumps
from multiprocessing import RLock
from pathlib import Path
from tempfile import mkdtemp
from typing import Any
from typing import Dict
from typing import List
from typing import Mapping
from typing import Union

from gemseo.core.discipline import MDODiscipline
from gemseo.core.doe_scenario import DOEScenario
from gemseo.core.execution_sequence import AtomicExecSequence
from gemseo.core.execution_sequence import CompositeExecSequence
from gemseo.core.execution_sequence import LoopExecSequence
from gemseo.core.execution_sequence import ParallelExecSequence
from gemseo.core.execution_sequence import SerialExecSequence
from gemseo.core.mdo_scenario import MDOScenario
from gemseo.core.monitoring import Monitoring
from gemseo.core.scenario import Scenario
from gemseo.disciplines.scenario_adapters.mdo_scenario_adapter import MDOScenarioAdapter
from gemseo.mda.mda import MDA
from gemseo.utils.locks import synchronized
from gemseo.utils.show_utils import generate_xdsm_html
from gemseo.utils.xdsm import XDSM
from gemseo.utils.xdsm_to_pdf import xdsm_data_to_pdf

LOGGER = logging.getLogger(__name__)

OPT_NAME = OPT_ID = "Opt"
USER_NAME = USER_ID = "_U_"

EdgeType = Dict[str, Union[MDODiscipline, List[str]]]
NodeType = Dict[str, str]
IdsType = Any


class XDSMizer:
    """Build the XDSM diagram of a scenario as a JSON structure."""

    def __init__(
        self,
        scenario: Scenario,
        hashref: str = "root",
        level: int = 0,
        expected_workflow: CompositeExecSequence | None = None,
    ) -> None:
        """
        Args:
            scenario: The scenario to be represented as an XDSM diagram.
            hashref: The keyword used in the JSON structure
                to reference the dictionary data structure
                whose keys are "nodes", "edges", "workflow" and "optpb".
            level: The depth of the scenario. Root scenario is level 0.
            expected_workflow: The expected workflow,
                describing the sequence of execution of the different disciplines
                (:class:`.MDODiscipline`, :class:`.Scenario`, :class:`.MDA`, etc.)
        """  # noqa:D205 D212 D415
        self.scenario = scenario
        self.level = level
        self.hashref = hashref
        self.lock = RLock()
        self._monitor = None
        self.directory_path = "."
        self.json_file_name = "xdsm.json"
        self.to_hashref = {}
        self.to_id = {}  # dictionary to map AtomicExecSequence to XDSM id
        self.initialize(expected_workflow)
        self.log_workflow_status = False
        self.save_pdf = False

    def initialize(
        self,
        workflow: CompositeExecSequence | None = None,
    ) -> None:
        """Initialize the XDSM from a workflow.

        The initialization also creates sub-XDSM diagram accordingly.

        Args:
            workflow: The composite execution sequence.
                If None, use the scenario's one.
        """
        self.sub_xdsmizers = []
        # Find disciplines from workflow structure
        if workflow:
            self.workflow = workflow
        else:
            self.workflow = self.scenario.get_expected_workflow()
        self.atoms = XDSMizer._get_single_level_atoms(self.workflow)

        self.to_hashref = {}
        level = self.level + 1
        num = 1
        for atom in self.atoms:
            if atom.discipline.is_scenario():
                if atom.discipline == self.scenario:
                    self.to_hashref[atom] = "root"
                    self.root_atom = atom
                else:  # sub-scenario
                    name = atom.discipline.name
                    self.to_hashref[atom] = f"{name}_scn-{level}-{num}"
                    sub_workflow = XDSMizer._find_sub_workflow(self.workflow, atom)
                    self.sub_xdsmizers.append(
                        XDSMizer(
                            atom.discipline, self.to_hashref[atom], level, sub_workflow
                        )
                    )
                    num += 1

    def monitor(
        self,
        directory_path: str | Path = ".",
        file_name: str = "xdsm",
        log_workflow_status: bool = False,
        save_pdf: bool = False,
    ) -> None:
        """Generate XDSM json file on discipline status update.

        Args:
            directory_path: The path of the directory to save the files.
            file_name: The file name to be suffixed by a file extension.
            log_workflow_status: Whether to log the evolution of the workflow's status.
            save_pdf: Whether to save the XDSM as a PDF file.
        """
        self._monitor = Monitoring(self.scenario)
        self._monitor.add_observer(self)
        # have to reinitialize with monitored workflow
        self.initialize(self._monitor.workflow)
        self.directory_path = directory_path
        self.json_file_name = f"{file_name}.json"
        self.log_workflow_status = log_workflow_status
        self.save_pdf = save_pdf

    def update(
        self,
        atom: AtomicExecSequence,
    ) -> None:  # pylint: disable=unused-argument
        """Generate a new XDSM regarding the atom status update.

        Args:
            atom: The discipline which status is monitored.
        """
        self.run(
            directory_path=self.directory_path,
            file_name=self.json_file_name,
            save_pdf=self.save_pdf,
        )
        if self.log_workflow_status:
            LOGGER.info(str(self._monitor))

    def run(
        self,
        directory_path: str | Path = ".",
        file_name: str = "xdsm",
        show_html: bool = False,
        save_html: bool = True,
        save_json: bool = False,
        save_pdf: bool = False,
    ) -> XDSM:
        """Generate a XDSM diagram of the :attr:`.scenario`.

        By default,
        a self-contained HTML file is generated,
        that can be viewed in a browser.

        Args:
            directory_path: The path of the directory to save the files.
            file_name: The file name to be suffixed by a file extension.
            show_html: Whether to open the web browser and display the XDSM.
            save_html: Whether to save the XDSM as a HTML file.
            save_json: Whether to save the XDSM as a JSON file.
            save_pdf: Whether to save the XDSM as a PDF file.

        Returns:
            A XDSM diagram.
        """
        xdsm = self.xdsmize()
        xdsm_json = dumps(xdsm, indent=2, ensure_ascii=False)

        directory_path = Path(directory_path)
        if save_json:
            with (directory_path / f"{file_name}.json").open("w") as file_stream:
                file_stream.write(xdsm_json)

        if save_pdf:
            xdsm_data_to_pdf(xdsm, directory_path, file_name)

        html_file_path = None
        if save_html or show_html:
            if save_html:
                html_directory_path = directory_path
            else:
                html_directory_path = Path(mkdtemp(suffix="", prefix="tmp"))

            html_file_path = (html_directory_path / file_name).with_suffix(".html")
            generate_xdsm_html(xdsm, html_file_path)

        xdsm = XDSM(xdsm_json, html_file_path)
        if show_html:
            xdsm.visualize()

        return xdsm

    def get_all_sub_xdsmizers(self) -> list[XDSMizer]:
        """Retrieve all the sub-xdsmizers corresponding to the sub-scenarios.

        Returns:
            The sub-xdsmizers.
        """
        result = []
        for sub in self.sub_xdsmizers:
            result.append(sub)
            result.extend(sub.get_all_sub_xdsmizers())
        return result

    @synchronized
    def xdsmize(
        self,
        algoname: str = "Optimizer",
    ) -> dict[str, Any]:
        """Build the data structure to be used to generate the JSON file.

        Args:
            algoname: The name under which a scenario appears in an XDSM.

        Returns:
            The XDSM structure expressed as a dictionary
            whose keys are "nodes", "edges", "workflow" and "optpb".
        """
        nodes = self._create_nodes(algoname)
        edges = self._create_edges()
        workflow = self._create_workflow()
        optpb = str(self.scenario.formulation.opt_problem)

        if self.level == 0:
            res = {
                self.hashref: {
                    "nodes": nodes,
                    "edges": edges,
                    "workflow": workflow,
                    "optpb": optpb,
                }
            }
            for sub_xdsmizer in self.get_all_sub_xdsmizers():
                if sub_xdsmizer.scenario.name.endswith("ing"):
                    name = f"{sub_xdsmizer.scenario.name[:-3]}er"
                elif sub_xdsmizer.scenario.name.endswith("Scenario"):
                    if isinstance(sub_xdsmizer.scenario, DOEScenario):
                        name = "Trade-Off"
                    elif isinstance(sub_xdsmizer.scenario, MDOScenario):
                        name = "Optimizer"
                    else:
                        name = sub_xdsmizer.scenario.name
                else:
                    name = sub_xdsmizer.scenario.name
                res[sub_xdsmizer.hashref] = sub_xdsmizer.xdsmize(name)
            return res
        return {"nodes": nodes, "edges": edges, "workflow": workflow, "optpb": optpb}

    def _create_nodes(
        self,
        algoname: str,
    ) -> list[NodeType]:  # pylint: disable=too-many-branches
        """Create the nodes of the XDSM from the scenarios and the disciplines.

        Args:
            algoname: The name under which a scenario appears in an XDSM.
        """
        nodes = []
        self.to_id = {}

        statuses = self.workflow.get_statuses()

        # Optimization
        self.to_id[self.root_atom] = OPT_ID
        opt_node = {"id": OPT_ID, "name": algoname, "type": "optimization"}
        if statuses[self.root_atom.uuid]:
            opt_node["status"] = statuses[self.root_atom.uuid]

        nodes.append(opt_node)

        # Disciplines
        for atom_id, atom in enumerate(
            self.atoms
        ):  # pylint: disable=too-many-nested-blocks
            # if a node already created from an atom with same discipline
            # at one level just reference the same node
            for ref_atom in self.to_id:
                if atom.discipline == ref_atom.discipline:
                    self.to_id[atom] = self.to_id[ref_atom]

                    if (
                        atom.status
                        and atom.parent.status is MDODiscipline.ExecutionStatus.RUNNING
                    ):
                        node = None
                        for a_node in nodes:
                            if a_node["id"] == self.to_id[atom]:
                                node = a_node
                                break

                        if not node:
                            # TODO: add specific exception?
                            raise "Node " + self.to_id[
                                atom
                            ] + " not found in " + nodes  # pragma: no cover

                        node["status"] = atom.status

                    break

            if atom in self.to_id:
                continue

            self.to_id[atom] = "Dis" + str(atom_id)
            node = {"id": self.to_id[atom], "name": atom.discipline.name}

            # node type
            if isinstance(atom.discipline, MDA):
                node["type"] = "mda"
            elif atom.discipline.is_scenario():
                node["type"] = "mdo"
                node["subxdsm"] = self.to_hashref[atom]
                node["name"] = self.to_hashref[atom]
            else:
                node["type"] = "analysis"

            if statuses[atom.uuid]:
                node["status"] = statuses[atom.uuid]

            nodes.append(node)

        return nodes

    def _create_edges(self) -> list[EdgeType]:
        """Create the edges of the XDSM from the dataflow of the scenario."""
        edges = []
        # convenient method to factorize code for creating and appending edges

        def add_edge(
            from_edge: MDODiscipline,
            to_edge: MDODiscipline,
            varnames: list[str],
        ) -> None:
            """Add an edge from a discipline to another with variables names as label.

            Args:
                from_edge: The starting discipline.
                to_edge: The end discipline.
                varnames: The names of the variables
                    going from the starting discipline to the end one.
            """
            edge = {"from": from_edge, "to": to_edge, "name": ", ".join(varnames)}
            edges.append(edge)

        # For User to/from optimization
        opt_pb = self.scenario.formulation.opt_problem

        # fct names such as -y4
        function_name = opt_pb.get_all_function_name()

        # output variables used by the fonction (eg y4)
        fct_varnames = [f.output_names for f in opt_pb.get_all_functions()]
        function_varnames = []
        for fvars in fct_varnames:
            function_varnames.extend(fvars)

        to_user = function_name
        to_opt = self.scenario.get_optim_variable_names()

        user_pattern = "L({})" if self.scenario.name == "Sampling" else "{}^(0)"
        opt_pattern = "{}^(1:N)" if self.scenario.name == "Sampling" else "{}^*"
        add_edge(USER_ID, OPT_ID, [user_pattern.format(x) for x in to_opt])
        add_edge(OPT_ID, USER_ID, [opt_pattern.format(x) for x in to_user])

        # Disciplines to/from optimization
        for atom in self.atoms:
            if atom is not self.root_atom:
                varnames = set(atom.discipline.get_input_data_names()) & set(
                    self.scenario.get_optim_variable_names()
                )
                if varnames:
                    add_edge(OPT_ID, self.to_id[atom], varnames)

                varnames = set(atom.discipline.get_output_data_names()) & set(
                    function_varnames
                )
                if varnames:
                    add_edge(self.to_id[atom], OPT_ID, varnames)

        # Disciplines to User/Optimization (from User is already handled at
        # optimizer level)
        disc_to_opt = function_varnames
        for atom in self.atoms:
            if atom is not self.root_atom:
                # special case MDA : skipped
                if isinstance(atom.discipline, MDA):
                    continue
                out_to_user = [
                    o
                    for o in atom.discipline.get_output_data_names()
                    if o not in disc_to_opt
                ]
                out_to_opt = [
                    o
                    for o in atom.discipline.get_output_data_names()
                    if o in disc_to_opt
                ]
                if out_to_user:
                    add_edge(self.to_id[atom], USER_ID, [x + "^*" for x in out_to_user])
                if out_to_opt:
                    add_edge(self.to_id[atom], OPT_ID, out_to_opt)

        # Disciplines to/from disciplines
        for coupling in self.scenario.get_expected_dataflow():
            (disc1, disc2, varnames) = coupling
            add_edge(
                self.to_id[self._find_atom(disc1)],
                self.to_id[self._find_atom(disc2)],
                varnames,
            )

        return edges

    @staticmethod
    def _get_single_level_atoms(
        workflow: CompositeExecSequence,
    ) -> list[AtomicExecSequence]:
        """Retrieve the list of atoms of the given workflow.

        This method does not look into the loop execution sequences
        coming from the scenario.
        Thus, it retrieves the atoms for a one level XDSM diagram.

        Args:
            The composite execution sequence.

        Returns:
            The atomic execution sequences.
        """
        atoms = []
        for sequence in workflow.sequences:
            if isinstance(sequence, LoopExecSequence):
                atoms.append(sequence.atom_controller)
                if not sequence.atom_controller.discipline.is_scenario():
                    atoms += XDSMizer._get_single_level_atoms(
                        sequence.iteration_sequence
                    )
            elif isinstance(sequence, AtomicExecSequence):
                atoms.append(sequence)
            else:
                atoms += XDSMizer._get_single_level_atoms(sequence)
        return atoms

    def _find_atom(
        self,
        discipline: MDODiscipline,
    ) -> AtomicExecSequence:
        """Find the atomic sequence corresponding to a given discipline.

        Args:
            discipline: A discipline.

        Returns:
            The atomic sequence corresponding to the given discipline.

        Raises:
            ValueError: If the atomic sequence is not found.
        """
        atom = None
        if isinstance(discipline, MDOScenarioAdapter):
            atom = self._find_atom(discipline.scenario)
        else:
            for atom_i in self.atoms:
                if discipline == atom_i.discipline:
                    atom = atom_i
        if atom is None:
            disciplines = [a.discipline for a in self.atoms]
            raise ValueError(f"Discipline {discipline} not found in {disciplines}")
        return atom

    @staticmethod
    def _find_sub_workflow(
        workflow: CompositeExecSequence,
        atom_controller: AtomicExecSequence,
    ) -> LoopExecSequence | None:
        """Find the sub-workflow from a workflow and controller atom in it.

        Args:
            workflow: The workflow from which to find a sub-workflow.
            atom_controller: The atomic execution sequence that controls
                the loop execution sequence to find.

        Returns:
            The sub-workflow.
            None if the list of execution sequences of the original workflow is empty.
        """
        sub_workflow = None
        for sequence in workflow.sequences:
            if isinstance(sequence, LoopExecSequence):
                if sequence.atom_controller.uuid == atom_controller.uuid:
                    sub_workflow = sequence
                    return sub_workflow

                sub_workflow = sub_workflow or XDSMizer._find_sub_workflow(
                    sequence.iteration_sequence, atom_controller
                )
            elif not isinstance(sequence, AtomicExecSequence):
                sub_workflow = sub_workflow or XDSMizer._find_sub_workflow(
                    sequence, atom_controller
                )

        return sub_workflow

    def _create_workflow(self) -> list[str, IdsType]:
        """Manage the creation of the XDSM workflow creation from a formulation one."""
        workflow = [USER_ID, expand(self.workflow, self.to_id)]
        return workflow


def expand(
    wks: CompositeExecSequence,
    to_id: Mapping[str, str],
) -> IdsType:
    """Expand the workflow structure as an ids structure using to_id mapping.

    The expansion preserve the structure
    while replacing the object by its id in all case
    except when a tuple is encountered as cdr
    then the expansion transforms loop[A, (B,C)] in [idA, {'parallel': [idB, idC]}].

    Args:
        wks: The workflow structure.
        to_id: The mapping dict from object to id.

    Returns:
        The ids structure valid to be used as XDSM json chains.
    """
    if isinstance(wks, SerialExecSequence):
        res = []
        for sequence in wks.sequences:
            res += expand(sequence, to_id)
        ids = res
    elif isinstance(wks, ParallelExecSequence):
        res = []
        for sequence in wks.sequences:
            if isinstance(sequence, AtomicExecSequence):
                res += expand(sequence, to_id)
            else:
                res.append(expand(sequence, to_id))
        ids = [{"parallel": res}]
    elif isinstance(wks, LoopExecSequence):
        if (
            wks.atom_controller.discipline.is_scenario()
            and to_id[wks.atom_controller] != OPT_ID
        ):
            # sub-scnario consider only the controller
            ids = [to_id[wks.atom_controller]]
        else:
            ids = [to_id[wks.atom_controller], expand(wks.iteration_sequence, to_id)]
    elif isinstance(wks, AtomicExecSequence):
        ids = [to_id[wks]]
    else:
        raise Exception(f"Bad execution sequence: found {wks}")
    return ids
