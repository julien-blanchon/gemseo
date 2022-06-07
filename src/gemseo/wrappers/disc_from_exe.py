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
#    INITIAL AUTHORS - initial API and implementation and/or
#                      initial documentation
#        :author:  Francois Gallard
#    OTHER AUTHORS   - MACROSCOPIC CHANGES
"""Make a discipline from an executable."""
from __future__ import annotations

import logging
import re
import subprocess
import sys
from ast import literal_eval
from copy import deepcopy
from multiprocessing import Lock
from multiprocessing import Manager
from os import listdir
from os import mkdir
from os.path import join
from pathlib import Path
from typing import Mapping
from typing import Sequence
from uuid import uuid1

from numpy import array
from numpy import ndarray

from gemseo.core.data_processor import DataProcessor  # noqa: F401
from gemseo.core.data_processor import FloatDataProcessor
from gemseo.core.discipline import MDODiscipline
from gemseo.utils.base_enum import BaseEnum

LOGGER = logging.getLogger(__name__)

NUMERICS = [str(j) for j in range(10)]
INPUT_REGEX = r"GEMSEO_INPUT\{(.*)\}"
OUTPUT_REGEX = r"GEMSEO_OUTPUT\{(.*)\}"


class FoldersIter(BaseEnum):
    NUMBERED = 0
    UUID = 1


class Parsers(BaseEnum):
    KEY_VALUE_PARSER = 0
    TEMPLATE_PARSER = 1
    CUSTOM_CALLABLE = 2


class DiscFromExe(MDODiscipline):
    """Generic wrapper for executables.

    The DiscFromExe is a generic wrapper for executables. It generates a
    MDODiscipline from an executable and in inputs/output files wrappers.  The
    input and output files are described by templates.  The templates can be
    generated by executing the module
    :mod:`~gemseo.wrappers.template_grammar_editor` to open a GUI.

    It requires the creation of templates for input and output file,
    for instance, from the following input JSON file:

    .. code::

       {
       "a": 1.01515112125,
       "b": 2.00151511213,
       "c": 3.00151511213
       }

    A template that declares the inputs must be generated under this format,
    where "a" is the name of the input, and "1.0" is the default input.
    GEMSEO_INPUT declares an input, GEMSEO_OUTPUT declares an output, similarly.

    .. code::

       {
       "a": GEMSEO_INPUT{a::1.0},
       "b": GEMSEO_INPUT{b::2.0},
       "c": GEMSEO_INPUT{c::3.0}
       }

    The current limitations are

    - Only one input and one output file, otherwise,
      inherit from this class and modify the parsers.
      Only limited input writing and output parser strategies
      are implemented. To change that, you can pass custom parsing and
      writing methods to the constructor.
    - The only limitation in the current file format is that
      it must be a plain text file and not a binary file.
      In this case, the way of interfacing it is
      to provide a specific parser to the DiscFromExe,
      with the write_input_file_method
      and parse_outfile_method arguments of the constructor.

    Attributes:
        input_template (str): The path to the input template file.
        output_template (str): The path to the output template file.
        input_filename (str): The name of the input file.
        output_filename (str): The name of the output file.
        executable_command (str): The executable command.
        parse_outfile (Callable[Mapping[str, Tuple[int]], Sequence[str]]):
            The function used to parse the output file.
        write_input_file
            (Callable[[str, Mapping[str, ndarray], Mapping[str, Tuple[int]],
            Sequence[int]], str]):
            The function used to write the input file.
        output_folder_basepath (str): The base path of the execution directories.
        data_processor (DataProcessor): A data processor to be used before the execution
            of the discipline.
    """

    def __init__(
        self,
        input_template: str,
        output_template: str,
        output_folder_basepath: str,
        executable_command: str,
        input_filename: str,
        output_filename: str,
        folders_iter: str | FoldersIter = FoldersIter.NUMBERED,
        name: str | None = None,
        parse_outfile_method: str | Parsers = Parsers.TEMPLATE_PARSER,
        write_input_file_method: str | None = None,
        parse_out_separator: str = "=",
        use_shell: bool = True,
    ) -> None:
        """
        Args:
            input_template: The path to the input file template.
                The input locations in the file are marked
                by GEMSEO_INPUT{input_name::1.0},
                where "input_name" is the input name, and 1.0 is here
                the default input.
            output_template: The path to the output file template.
                The input locations in the file are marked
                by GEMSEO_OUTPUT{output_name::1.0},
                where "output_name" is the input name.
            executable_command: The command to run the executable.
                Will be called through a system call.
                Example: "python myscript.py -i input.txt -o output.txt
            input_filename: The name of the input file.
                This will determine the name
                of the input file generated in the output folder.
                Example "input.txt".
            output_filename: The name of the output file.
                This will determine the name
                of the output file generated in the output folder.
                Example "output.txt".
            folders_iter (Union[str, FoldersIter]: The type of unique identifiers
                for the output folders. If NUMBERED the generated output folders
                will be "output_folder_basepath"+str(i+1),
                where i is the maximum value of the already existing
                "output_folder_basepath"+str(i) folders.
                Otherwise, a unique number based on the UUID function is
                generated. This last option shall be used if multiple MDO
                processes are run in the same work directory.
            name: the name of the discipline. If None,
                use the class name.
            parse_outfile_method: The optional method that can be provided
                by the user to parse the output file. To see the signature of
                the method, see the parse_outfile method of this file.
                If the KEY_VALUE_PARSER is used as
                output parser, specify the separator key (default : "=").
            write_input_file_method: The method to write the input file.
                If None, use these modules' write_input_file. To see the signature
                of the method, see the write_input_file method of this file.
            parse_out_separator: The separator used for the output parser.
            use_shell: If True, run the command using the default shell. Otherwise,
                run directly the command.

        Raises:
            TypeError: If the provided write_input_file_method is not callable.
        """
        super().__init__(name=name)
        self.input_template = input_template
        self.output_template = output_template
        self.input_filename = input_filename
        self.output_filename = output_filename
        self.executable_command = executable_command
        self.__use_shell = use_shell

        use_template_parse = parse_outfile_method == Parsers.TEMPLATE_PARSER
        if parse_outfile_method is None or use_template_parse:
            self.parse_outfile = parse_outfile
            self._parse_outfile_method = Parsers.TEMPLATE_PARSER
        elif parse_outfile_method == Parsers.KEY_VALUE_PARSER:
            self.parse_outfile = lambda a, b: parse_key_value_file(
                a, b, parse_out_separator
            )
            self._parse_outfile_method = Parsers.KEY_VALUE_PARSER
        else:
            self.parse_outfile = parse_outfile_method
            self._parse_outfile_method = Parsers.CUSTOM_CALLABLE

        if not callable(self.parse_outfile):
            raise TypeError("The parse_outfile_method must be callable")

        self.write_input_file = write_input_file_method or write_input_file

        if not callable(self.write_input_file):
            raise TypeError("The write_input_file_method must be callable")

        self.__lock = Lock()

        self.__folders_iter = None
        self.folders_iter = folders_iter

        self.output_folder_basepath = output_folder_basepath

        self.__check_basepath_on_windows()

        self._out_pos = None
        self._in_dict = None
        self._out_dict = None
        self._in_lines = None
        self._out_lines = None

        n_dirs = self._get_max_outdir()
        self._counter = Manager().Value("i", n_dirs)

        self.data_processor = FloatDataProcessor()

        self.__parse_templates_and_set_grammars()

    @property
    def folders_iter(self) -> FoldersIter:
        """The names of the new execution directories.

        The setter will check that the value provided for folder_iter is valid.
        This check is done by checking its presence in FOLDERS_ITER.

        Raises:
            ValueError: If the value provided to the setter is not present
                in the accepted list of folders_iters list.
        """
        return self.__folders_iter

    @folders_iter.setter
    def folders_iter(
        self,
        value: str | FoldersIter,
    ) -> None:
        if value not in FoldersIter:
            msg = f"{value} is not a valid folder_iter value."
            raise ValueError(msg)
        self.__folders_iter = FoldersIter.get_member_from_name(value)

    def __check_basepath_on_windows(self) -> None:
        """Check that the basepath can be used.

        If the user use shell=True under Windows with a basepath
            that is on a network location, raise an error.

        Raises:
            ValueError: The basepath is located on a network location
                and cannot be run with cmd.exe.
        """
        if sys.platform.startswith("win") and self.__use_shell:
            resolved_basepath = Path(self.output_folder_basepath).resolve()
            if not resolved_basepath.parts[0].startswith("\\\\"):
                return

            msg = (
                "A network basepath and use_shell cannot be used together"
                " under Windows, as cmd.exe cannot change the current directory"
                " to a UNC path."
                " Please try use_shell=False or use a local base path."
            )
            raise ValueError(msg)

    def __parse_templates_and_set_grammars(self) -> None:
        """Parse the templates and set the grammar of the discipline."""
        with open(self.input_template) as infile:
            self._in_lines = infile.readlines()
        with open(self.output_template) as outfile:
            self._out_lines = outfile.readlines()

        self._in_dict, self._in_pos = parse_template(self._in_lines, True)
        self.input_grammar.update(self._in_dict.keys())

        out_dict, self._out_pos = parse_template(self._out_lines, False)

        self.output_grammar.update(out_dict.keys())

        msg = "Initialize discipline from template. \
                Input grammar: {}".format(
            self._in_dict.keys()
        )
        LOGGER.debug(msg)
        msg = "Initialize discipline from template. \
                Output grammar: {}".format(
            out_dict.keys()
        )
        LOGGER.debug(msg)
        self.default_inputs = {
            k: array([literal_eval(v)]) for k, v in self._in_dict.items()
        }

    def _run(self) -> None:
        """Run the wrapper."""
        uuid = self.generate_uid()

        out_dir = join(self.output_folder_basepath, uuid)

        mkdir(out_dir)
        input_file_path = join(out_dir, self.input_filename)

        self.write_input_file(
            input_file_path, self.local_data, self._in_pos, self._in_lines
        )

        if self.__use_shell:
            executable_command = self.executable_command
        else:
            executable_command = self.executable_command.split()

        err = subprocess.call(
            executable_command,
            shell=self.__use_shell,
            stderr=subprocess.STDOUT,
            cwd=out_dir,
        )
        if err != 0:
            raise RuntimeError("Execution failed and returned error code : " + str(err))
        outfile = join(out_dir, self.output_filename)
        with open(outfile) as outfile:
            out_lines = outfile.readlines()

        if len(out_lines) != len(self._out_lines):
            raise ValueError(
                "The number of lines of the output file changed."
                "This is not supported yet"
            )

        out_vals = self.parse_outfile(self._out_pos, out_lines)
        self.local_data.update(out_vals)

    def generate_uid(self) -> str:
        """Generate a unique identifier for the execution directory.

        Generate a unique identifier for the current execution.
        If the folders_iter strategy is NUMBERED,
        the successive iterations are named by an integer 1, 2, 3 etc.
        This is multiprocess safe.
        Otherwise, a unique number based on the UUID function is generated.
        This last option shall be used if multiple MDO processes are runned
        in the same workdir.

        Returns:
            An unique string identifier (either a number or a UUID).
        """
        if self.folders_iter == FoldersIter.NUMBERED:
            with self.__lock:
                self._counter.value += 1
                return str(self._counter.value)
        elif self.folders_iter == FoldersIter.UUID:
            return str(uuid1()).split("-")[-1]
        else:
            msg = (
                "{} is not a valid method for creating the execution"
                " directories.".format(self.folders_iter)
            )
            raise ValueError(msg)

    def _list_out_dirs(self) -> list[str]:
        """Return the directories in the output folder path.

        Returns:
             The list of the directories in the output folder path.
        """
        return listdir(self.output_folder_basepath)

    def _get_max_outdir(self) -> int:
        """Get the maximum current index of output folders.

        Returns:
             The maximum index in the output folders.
        """
        outs = list(self._list_out_dirs())
        if not outs:
            return 0
        return max(literal_eval(n) for n in outs)


def parse_template(
    template_lines: Sequence[str],
    grammar_is_input: bool,
) -> tuple[dict[str, ndarray], dict[str, tuple[int]]]:
    """Parse the input or output template.

    This function parses the input (or output) template.
    It returns the tuple (data_dict, pos_dict), where:

    - `data_dict` is the `{name:value}` dict:

       - name is the data name
       - value is the parsed input or output value in the template

    - `pos_dict` describes the template format {data_name:(start,end,line_number)}:

       - `data_name` is the name of the input data
       - `start` is the index of the starting point in the input file template.
         This index is a line index (character number on the line)
       - `end` is the index of the end character in the template
       - `line_number` is the index of the line in the file

    Args:
        template_lines: The lines of the template file.
        grammar_is_input: True for an input template, False otherwise.

    Returns:
        A data structure containing the parsed inpout or output template.
    """
    pattern_re = INPUT_REGEX if grammar_is_input else OUTPUT_REGEX

    regex = re.compile(pattern_re)  # , re.MULTILINE
    data_dict = {}
    pos_dict = {}

    for lineid, line in enumerate(template_lines):
        for match in regex.finditer(line):
            data = match.groups()[0]
            spl = data.split("::")
            name = spl[0]
            val = spl[1]
            data_dict[name] = val
            # When input mode: erase the template value
            if grammar_is_input:
                start, end = match.start(), match.end()
            else:
                # In output mode : catch all
                # the output lenght and not more
                start = match.start()
                end = start + len(val)

            pos_dict[name] = (start, end, lineid)

    return data_dict, pos_dict


def write_input_file(
    input_file_path: str,
    data: Mapping[str, ndarray],
    input_positions: Mapping[str, tuple[int]],
    input_lines: Sequence[str],
    float_format: str = "{:1.18g}",
) -> None:
    """Write the input file from the input data.

    Args:
        input_file_path: The absolute path to the file to be written.
        data: The local data of the discipline.
        input_positions: The information from the template
         format {data_name:(start,end,line_number)}, where name is the name of the input data,
         start is the index of the starting point in the input file template.
         This index is a line index (character number on the line).
         end is the index of the end character in the template,
         line_number is the index of the line in the file.
        input_lines: The lines of the input file template.
        float_format: The formating of the input data in the file (Default value = "{:1.18g}").
    """
    f_text = deepcopy(input_lines)
    for name, pos in input_positions.items():
        start, end, lineid = pos
        data_str = float_format.format(data[name])
        cline = f_text[lineid]
        f_text[lineid] = cline[:start] + data_str + cline[end:]

    with open(input_file_path, "w") as infile_o:
        infile_o.writelines(f_text)


def parse_key_value_file(
    _,
    out_lines: Sequence[str],
    separator: str = "=",
) -> dict[str, float]:
    """Parse the output file from the expected text positions.

    Args:
        out_lines: The lines of the output file template.
        separator: The separating characters of the key=value format.

    Returns:
        The output data in `.MDODiscipline` friendly data structure.
    """
    data = {}
    for line in out_lines:
        if separator in line:
            spl = line.strip().split(separator)
            if len(spl) != 2:
                raise ValueError("unbalanced = in line " + str(line))
            key = spl[0].strip()
            try:
                data[key] = float(literal_eval(spl[1].strip()))
            except Exception:
                raise ValueError("Failed to parse value as float " + str(spl[1]))

    return data


def parse_outfile(
    output_positions: Mapping[str, tuple[int]],
    out_lines: Sequence[str],
) -> dict[str, ndarray]:
    """Parse the output file from the expected text positions.

    Args:
        output_positions: The output position for each data name.
         The information from the template format
         {data_name:(start,end,dictionary)}, where
         name is the name of the output
         data, start is the index of the starting point
         in the input file template.
         This index is a line index (character number on the line)
         end is the index of the end character in the template
         line_number is the index of the line in the file
        out_lines: The lines of the output file template.

    Returns:
        The output data in `.MDODiscipline` friendly data structure.
    """
    values = {}
    for name, pos in output_positions.items():
        start, _, lineid = pos

        found_dot = False
        found_e = False
        # In case generated files has fewer lines
        if lineid > len(out_lines) - 1:
            break
        out_text = out_lines[lineid]
        i = start
        maxi = len(out_text)
        while True:
            # The problem is that the output file used for the template may be
            # using an output that is longer or shorter than the one generated
            # at runtime. We must find the proper end of the expression...
            i += 1
            char = out_text[i]
            if char == ".":
                # We found the . in float notation
                if found_dot or found_e:
                    break
                found_dot = True
                continue
            # We found the e in exp notation
            if char in ("E", "e"):
                if found_e:
                    break
                found_e = True
                continue
            # Check that we have nout reached EOL or space or whatever
            if char not in NUMERICS:
                break
            if i == maxi - 1:
                break
        outv = out_text[pos[0] : i]

        LOGGER.info("Parsed %s got output %s", name, outv)
        values[name] = array([float(outv)])
    return values
