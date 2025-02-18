# -*- coding: utf-8 -*-
# Copyright (c) 2009-2014, Luke Maurits <luke@maurits.id.au>
# All rights reserved.
# With contributions from:
# * Chris Clark
#  * Klein Stephane
#  * John Filleau
# PTable is forked from original Google Code page in April, 2015, and now
# maintained by Kane Blueriver <kxxoling@gmail.com>.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# * The name of the author may not be used to endorse or promote products
#   derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# Taken from :
# https://github.com/kxxoling/PTable
# https://pypi.python.org/pypi/PTable
"""
The pretty table core
*********************
"""
import copy
import math
import random
import re
import sys
import textwrap
import unicodedata

from ._compact import basestring_
from ._compact import escape
from ._compact import itermap
from ._compact import str_types
from ._compact import uni_chr
from ._compact import unicode_
from typing import Optional, Sequence

PY2 = sys.version_info.major == 2




# hrule styles
FRAME = 0
ALL = 1
NONE = 2
HEADER = 3

# Table styles
DEFAULT = 10
MSWORD_FRIENDLY = 11
PLAIN_COLUMNS = 12
RANDOM = 20

_re = re.compile("\033\[[0-9;]*m")


def _get_size(text: str):
    """

    :param text:

    """
    lines = text.split("\n")
    height = len(lines)
    width = max([_str_block_width(line) for line in lines])
    return width, height


class PrettyTable(object):

    def __init__(self, field_names: Optional[Sequence[str]]=None, **kwargs) -> None:
        """

        :param encoding: Unicode encoding scheme used to decode any encoded input
        :param title: optional table title
        :param field_names: list or tuple of field names
        :param fields: list or tuple of field names to include in displays
        :param start: index of first data row to include in output
        :param end: index of last data row to include in output PLUS ONE
        :param header: print a header showing field names
        :param header_style: stylisation to apply to field names in header
        :param border: print a border around the table
        :param hrules: controls printing of horizontal rules after rows
        :param vrules: controls printing of vertical rules between columns
        :param int_format: controls formatting of integer data
        :param float_format: controls formatting of floating point data
        :param min_table_width: minimum desired table width
        :param max_table_width: maximum desired table width
        :param padding_width: number of spaces on either side of column data
        :param left_padding_width: number of spaces on left hand side of column data
        :param right_padding_width: number of spaces on right hand side of column data
        :param vertical_char: single character string used to draw vertical lines
        :param horizontal_char: single character string used to draw horizontal lines
        :param junction_char: single character string used to draw line junctions
        :param sortby: name of field to sort rows by
        :param sort_key: sorting key function
        :param valign: default valign for each row
        :param reversesort: True or False to sort in descending or ascending order
        :param oldsortslice: Slice rows before sorting in the

        """

        self.encoding = kwargs.get("encoding", "UTF-8")

        # Data
        self._field_names = []
        self._rows = []
        self.align = {}
        self.valign = {}
        self.max_width = {}
        self.min_width = {}
        self.int_format = {}
        self.float_format = {}
        if field_names:
            self.field_names = field_names
        else:
            self._widths = []

        # Options
        self._options = "title start end fields header border sortby reversesort sort_key attributes format hrules vrules".split()
        self._options.extend(
            "int_format float_format min_table_width max_table_width padding_width left_padding_width right_padding_width".split())
        self._options.extend(
            "vertical_char horizontal_char junction_char header_style valign xhtml print_empty oldsortslice".split())
        self._options.extend("align valign max_width min_width".split())
        for option in self._options:
            if option in kwargs:
                self._validate_option(option, kwargs[option])
            else:
                kwargs[option] = None

        self._title = kwargs["title"] or None
        self._start = kwargs["start"] or 0
        self._end = kwargs["end"] or None
        self._fields = kwargs["fields"] or None

        if kwargs["header"] in (True, False):
            self._header = kwargs["header"]
        else:
            self._header = True
        self._header_style = kwargs["header_style"] or None
        if kwargs["border"] in (True, False):
            self._border = kwargs["border"]
        else:
            self._border = True
        self._hrules = kwargs["hrules"] or FRAME
        self._vrules = kwargs["vrules"] or ALL

        self._sortby = kwargs["sortby"] or None
        if kwargs["reversesort"] in (True, False):
            self._reversesort = kwargs["reversesort"]
        else:
            self._reversesort = False
        self._sort_key = kwargs["sort_key"] or (lambda x: x)

        # Column specific arguments, use property.setters
        self.align = kwargs["align"] or {}
        self.valign = kwargs["valign"] or {}
        self.max_width = kwargs["max_width"] or {}
        self.min_width = kwargs["min_width"] or {}
        self.int_format = kwargs["int_format"] or {}
        self.float_format = kwargs["float_format"] or {}

        self._min_table_width = kwargs["min_table_width"] or None
        self._max_table_width = kwargs["max_table_width"] or None
        if kwargs["padding_width"] is None:
            self._padding_width = 1
        else:
            self._padding_width = kwargs["padding_width"]
        self._left_padding_width = kwargs["left_padding_width"] or None
        self._right_padding_width = kwargs["right_padding_width"] or None

        self._vertical_char = kwargs["vertical_char"] or self._unicode("|")
        self._horizontal_char = kwargs["horizontal_char"] or self._unicode("-")
        self._junction_char = kwargs["junction_char"] or self._unicode("+")

        if kwargs["print_empty"] in (True, False):
            self._print_empty = kwargs["print_empty"]
        else:
            self._print_empty = True
        if kwargs["oldsortslice"] in (True, False):
            self._oldsortslice = kwargs["oldsortslice"]
        else:
            self._oldsortslice = False
        self._format = kwargs["format"] or False
        self._xhtml = kwargs["xhtml"] or False
        self._attributes = kwargs["attributes"] or {}

    def _unicode(self, value):
        """

        :param value:

        """
        if not isinstance(value, basestring_):
            value = str(value)
        if not isinstance(value, unicode_):
            value = unicode_(value, self.encoding, "strict")
        return value

    def _justify(self, text: str, width: int, align):
        """

        :param text: param width:
        :param align:
        :param width:

        """
        excess = width - _str_block_width(text)
        if align == "l":
            return text + excess * " "
        elif align == "r":
            return excess * " " + text
        else:
            if excess % 2:
                # Uneven padding
                # Put more space on right if text is of odd length...
                if _str_block_width(text) % 2:
                    return (excess // 2) * " " + text + (excess // 2 + 1) * " "
                # and more space on left if text is of even length
                else:
                    return (excess // 2 + 1) * " " + text + (excess // 2) * " "
                    # Why distribute extra space this way?  To match the behaviour of
                    # the inbuilt str.center() method.
            else:
                # Equal padding on either side
                return (excess // 2) * " " + text + (excess // 2) * " "

    def __getattr__(self, name: str):

        if name == "rowcount":
            return len(self._rows)
        elif name == "colcount":
            if self._field_names:
                return len(self._field_names)
            elif self._rows:
                return len(self._rows[0])
            else:
                return 0
        else:
            raise AttributeError(name)

    def __getitem__(self, index):

        new = PrettyTable()
        new.field_names = self.field_names
        for attr in self._options:
            setattr(new, "_" + attr, getattr(self, "_" + attr))
        setattr(new, "_align", getattr(self, "_align"))
        if isinstance(index, slice):
            for row in self._rows[index]:
                new.add_row(row)
        elif isinstance(index, int):
            new.add_row(self._rows[index])
        else:
            raise Exception(
                "Index %s is invalid, must be an integer or slice" %
                str(index))
        return new

    def __str__(self) -> str:
        return self.__unicode__()

    def __unicode__(self):
        return self.get_string()

    ##############################
    # ATTRIBUTE VALIDATORS       #
    ##############################

    # The method _validate_option is all that should be used elsewhere in the code base to validate options.
    # It will call the appropriate validation method for that option.  The individual validation methods should
    # never need to be called directly (although nothing bad will happen if they *are*).
    # Validation happens in TWO places.
    # Firstly, in the property setters defined in the ATTRIBUTE MANAGMENT section.
    # Secondly, in the _get_options method, where keyword arguments are mixed
    # with persistent settings

    def _validate_option(self, option, val) -> None:
        """

        :param option: param val:
        :param val:

        """
        if option in "field_names":
            self._validate_field_names(val)
        elif option in ("start", "end", "max_width", "min_width", "min_table_width", "max_table_width", "padding_width",
                        "left_padding_width", "right_padding_width", "format"):
            self._validate_nonnegative_int(option, val)
        elif option in "sortby":
            self._validate_field_name(option, val)
        elif option in "sort_key":
            self._validate_function(option, val)
        elif option in "hrules":
            self._validate_hrules(option, val)
        elif option in "vrules":
            self._validate_vrules(option, val)
        elif option in "fields":
            self._validate_all_field_names(option, val)
        elif option in ("header", "border", "reversesort", "xhtml", "print_empty", "oldsortslice"):
            self._validate_true_or_false(option, val)
        elif option in "header_style":
            self._validate_header_style(val)
        elif option in "int_format":
            self._validate_int_format(option, val)
        elif option in "float_format":
            self._validate_float_format(option, val)
        elif option in ("vertical_char", "horizontal_char", "junction_char"):
            self._validate_single_char(option, val)
        elif option in "attributes":
            self._validate_attributes(option, val)

    def _validate_field_names(self, val):
        """

        :param val:

        """
        # Check for appropriate length
        if self._field_names:
            try:
                assert len(val) == len(self._field_names)
            except AssertionError:
                raise Exception("Field name list has incorrect number of values, (actual) %d!=%d (expected)" % (
                    len(val), len(self._field_names)))
        if self._rows:
            try:
                assert len(val) == len(self._rows[0])
            except AssertionError:
                raise Exception("Field name list has incorrect number of values, (actual) %d!=%d (expected)" % (
                    len(val), len(self._rows[0])))
        # Check for uniqueness
        try:
            assert len(val) == len(set(val))
        except AssertionError:
            raise Exception("Field names must be unique!")

    def _validate_header_style(self, val):
        """

        :param val:

        """
        try:
            assert val in ("cap", "title", "upper", "lower", None)
        except AssertionError:
            raise Exception(
                "Invalid header style, use cap, title, upper, lower or None!")

    def _validate_align(self, val):
        """

        :param val:

        """
        try:
            assert val in ["l", "c", "r"]
        except AssertionError:
            raise Exception("Alignment %s is invalid, use l, c or r!" % val)

    def _validate_valign(self, val):
        """

        :param val:

        """
        try:
            assert val in ["t", "m", "b", None]
        except AssertionError:
            raise Exception(
                "Alignment %s is invalid, use t, m, b or None!" %
                val)

    def _validate_nonnegative_int(self, name: str, val):
        """

        :param name: param val:
        :param val:

        """
        try:
            assert int(val) >= 0
        except AssertionError:
            raise Exception(
                "Invalid value for %s: %s!" %
                (name, self._unicode(val)))

    def _validate_true_or_false(self, name: str, val):
        """

        :param name: param val:
        :param val:

        """
        try:
            assert val in (True, False)
        except AssertionError:
            raise Exception(
                "Invalid value for %s!  Must be True or False." %
                name)

    def _validate_int_format(self, name: str, val):
        """

        :param name: param val:
        :param val:

        """
        if val == "":
            return
        try:
            assert type(val) in str_types
            assert val.isdigit()
        except AssertionError:
            raise Exception(
                "Invalid value for %s!  Must be an integer format string." %
                name)

    def _validate_float_format(self, name: str, val):
        """

        :param name: param val:
        :param val:

        """
        return
        if val == "":
            return
        try:
            val = val.rsplit('f')[0]
            assert type(val) in str_types
            assert "." in val
            bits = val.split(".")
            assert len(bits) <= 2
            assert bits[0] == "" or bits[0].isdigit()
            assert bits[1] == "" or bits[1].isdigit()
        except AssertionError:
            raise Exception(
                "Invalid value for %s!  Must be a float format string." %
                name)

    def _validate_function(self, name: str, val):
        """

        :param name: param val:
        :param val:

        """
        try:
            assert hasattr(val, "__call__")
        except AssertionError:
            raise Exception(
                "Invalid value for %s!  Must be a function." %
                name)

    def _validate_hrules(self, name: str, val):
        """

        :param name: param val:
        :param val:

        """
        try:
            assert val in (ALL, FRAME, HEADER, NONE)
        except AssertionError:
            raise Exception(
                "Invalid value for %s!  Must be ALL, FRAME, HEADER or NONE." %
                name)

    def _validate_vrules(self, name: str, val):
        """

        :param name: param val:
        :param val:

        """
        try:
            assert val in (ALL, FRAME, NONE)
        except AssertionError:
            raise Exception(
                "Invalid value for %s!  Must be ALL, FRAME, or NONE." %
                name)

    def _validate_field_name(self, name: str, val):
        """

        :param name: param val:
        :param val:

        """
        try:
            assert (val in self._field_names) or (val is None)
        except AssertionError:
            raise Exception("Invalid field name: %s!" % val)

    def _validate_all_field_names(self, name: str, val):
        """

        :param name: param val:
        :param val:

        """
        try:
            for x in val:
                self._validate_field_name(name, x)
        except AssertionError:
            raise Exception("fields must be a sequence of field names!")

    def _validate_single_char(self, name: str, val):
        """

        :param name: param val:
        :param val:

        """
        try:
            assert _str_block_width(val) == 1
        except AssertionError:
            raise Exception(
                "Invalid value for %s!  Must be a string of length 1." %
                name)

    def _validate_attributes(self, name: str, val):
        """

        :param name: param val:
        :param val:

        """
        try:
            assert isinstance(val, dict)
        except AssertionError:
            raise Exception(
                "attributes must be a dictionary of name/value pairs!")

    ##############################
    # ATTRIBUTE MANAGEMENT       #
    ##############################

    @property
    def field_names(self):
        """List or tuple of field names"""
        return self._field_names

    @field_names.setter
    def field_names(self, val) -> None:
        """

        :param val:

        """
        val = [self._unicode(x) for x in val]
        self._validate_option("field_names", val)
        if self._field_names:
            old_names = self._field_names[:]
        self._field_names = val
        if self._align and old_names:
            for old_name, new_name in zip(old_names, val):
                self._align[new_name] = self._align[old_name]
            for old_name in old_names:
                if old_name not in self._align:
                    self._align.pop(old_name)
        else:
            self.align = "c"
        if self._valign and old_names:
            for old_name, new_name in zip(old_names, val):
                self._valign[new_name] = self._valign[old_name]
            for old_name in old_names:
                if old_name not in self._valign:
                    self._valign.pop(old_name)
        else:
            self.valign = "t"

    @property
    def align(self):
        """Controls alignment of fields

        :param align: alignment

        """
        return self._align

    @align.setter
    def align(self, val) -> None:
        """

        :param val:

        """
        if not self._field_names:
            self._align = {}
        elif val is None or (isinstance(val, dict) and len(val) == 0):
            for field in self._field_names:
                self._align[field] = "c"
        else:
            self._validate_align(val)
            for field in self._field_names:
                self._align[field] = val

    @property
    def valign(self):
        """Controls vertical alignment of fields

        :param valign: vertical alignment

        """
        return self._valign

    @valign.setter
    def valign(self, val) -> None:
        """

        :param val:

        """
        if not self._field_names:
            self._valign = {}
        elif val is None or (isinstance(val, dict) and len(val) == 0):
            for field in self._field_names:
                self._valign[field] = "t"
        else:
            self._validate_valign(val)
            for field in self._field_names:
                self._valign[field] = val

    @property
    def max_width(self):
        """Controls maximum width of fields

        :param max_width: maximum width integer

        """
        return self._max_width

    @max_width.setter
    def max_width(self, val) -> None:
        """

        :param val:

        """
        if val is None or (isinstance(val, dict) and len(val) == 0):
            self._max_width = {}
        else:
            self._validate_option("max_width", val)
            for field in self._field_names:
                self._max_width[field] = val

    @property
    def min_width(self):
        """Controls minimum width of fields

        :param min_width: minimum width integer

        """
        if self.header:
            fields = self._field_names
        else:
            fields = self._rows[0] if self._rows else []
        result = {
            # minimum column width can't be lesser
            # than header's length
            name: max(
                _str_block_width(unicode_(name)),
                self._min_width.get(name, 0)
            )
            for name in fields
        }
        return result

    @min_width.setter
    def min_width(self, val) -> None:
        """

        :param val:

        """
        if val is None or (isinstance(val, dict) and len(val) == 0):
            self._min_width = {}
        else:
            self._validate_option("min_width", val)
            for field in self._field_names:
                self._min_width[field] = val

    @property
    def min_table_width(self):
        """ """
        return self._min_table_width

    @min_table_width.setter
    def min_table_width(self, val) -> None:
        """

        :param val:

        """
        self._validate_option("min_table_width", val)
        self._min_table_width = val

    @property
    def max_table_width(self):
        """ """
        return self._max_table_width

    @max_table_width.setter
    def max_table_width(self, val) -> None:
        """

        :param val:

        """
        self._validate_option("max_table_width", val)
        self._max_table_width = val

    @property
    def fields(self):
        """List or tuple of field names to include in displays"""
        return self._fields

    @fields.setter
    def fields(self, val) -> None:
        """

        :param val:

        """
        self._validate_option("fields", val)
        self._fields = val

    @property
    def title(self):
        """Optional table title

        :param title: table title

        """
        return self._title

    @title.setter
    def title(self, val) -> None:
        """

        :param val:

        """
        self._title = self._unicode(val)

    @property
    def start(self):
        """Start index of the range of rows to print

        :param start: index of first data row to include in output

        """
        return self._start

    @start.setter
    def start(self, val) -> None:
        """

        :param val:

        """
        self._validate_option("start", val)
        self._start = val

    @property
    def end(self):
        """End index of the range of rows to print

        :param end: index of last data row to include in output PLUS ONE

        """
        return self._end

    @end.setter
    def end(self, val) -> None:
        """

        :param val:

        """
        self._validate_option("end", val)
        self._end = val

    @property
    def sortby(self):
        """Name of field by which to sort rows

        :param sortby: field name to sort by

        """
        return self._sortby

    @sortby.setter
    def sortby(self, val) -> None:
        """

        :param val:

        """
        self._validate_option("sortby", val)
        self._sortby = val

    @property
    def reversesort(self):
        """Controls direction of sorting (ascending vs descending)

        :param reveresort: set to True to sort by descending order

        """
        return self._reversesort

    @reversesort.setter
    def reversesort(self, val) -> None:
        """

        :param val:

        """
        self._validate_option("reversesort", val)
        self._reversesort = val

    @property
    def sort_key(self):
        """Sorting key function, applied to data points before sorting

        :param sort_key: a function which takes one argument and returns something to be sorted

        """
        return self._sort_key

    @sort_key.setter
    def sort_key(self, val) -> None:
        """

        :param val:

        """
        self._validate_option("sort_key", val)
        self._sort_key = val

    @property
    def header(self):
        """Controls printing of table header with field names

        :param header: print a header showing field names

        """
        return self._header

    @header.setter
    def header(self, val) -> None:
        """

        :param val:

        """
        self._validate_option("header", val)
        self._header = val

    @property
    def header_style(self):
        """Controls stylisation applied to field names in header

        :param header_style: stylisation to apply to field names in header

        """
        return self._header_style

    @header_style.setter
    def header_style(self, val) -> None:
        """

        :param val:

        """
        self._validate_header_style(val)
        self._header_style = val

    @property
    def border(self):
        """Controls printing of border around table

        :param border: print a border around the table

        """
        return self._border

    @border.setter
    def border(self, val) -> None:
        """

        :param val:

        """
        self._validate_option("border", val)
        self._border = val

    @property
    def hrules(self):
        """Controls printing of horizontal rules after rows

        :param hrules: horizontal rules style

        """
        return self._hrules

    @hrules.setter
    def hrules(self, val) -> None:
        """

        :param val:

        """
        self._validate_option("hrules", val)
        self._hrules = val

    @property
    def vrules(self):
        """Controls printing of vertical rules between columns

        :param vrules: vertical rules style

        """
        return self._vrules

    @vrules.setter
    def vrules(self, val) -> None:
        """

        :param val:

        """
        self._validate_option("vrules", val)
        self._vrules = val

    @property
    def int_format(self):
        """Controls formatting of integer data

        :param int_format: integer format string

        """
        return self._int_format

    @int_format.setter
    def int_format(self, val) -> None:
        """

        :param val:

        """
        if val is None or (isinstance(val, dict) and len(val) == 0):
            self._int_format = {}
        else:
            self._validate_option("int_format", val)
            for field in self._field_names:
                self._int_format[field] = val

    @property
    def float_format(self):
        """Controls formatting of floating point data

        :param float_format: floating point format string

        """
        return self._float_format

    @float_format.setter
    def float_format(self, val) -> None:
        """

        :param val:

        """
        if val is None or (isinstance(val, dict) and len(val) == 0):
            self._float_format = {}
        else:
            self._validate_option("float_format", val)
            for field in self._field_names:
                self._float_format[field] = val

    @property
    def padding_width(self):
        """The number of empty spaces between a column's edge and its content

        :param padding_width: number of spaces

        """
        return self._padding_width

    @padding_width.setter
    def padding_width(self, val) -> None:
        """

        :param val:

        """
        self._validate_option("padding_width", val)
        self._padding_width = val

    @property
    def left_padding_width(self):
        """The number of empty spaces between a column's left edge and its content

        :param left_padding: number of spaces

        """
        return self._left_padding_width

    @left_padding_width.setter
    def left_padding_width(self, val) -> None:
        """

        :param val:

        """
        self._validate_option("left_padding_width", val)
        self._left_padding_width = val

    @property
    def right_padding_width(self):
        """The number of empty spaces between a column's right edge and its content

        :param right_padding: number of spaces

        """
        return self._right_padding_width

    @right_padding_width.setter
    def right_padding_width(self, val) -> None:
        """

        :param val:

        """
        self._validate_option("right_padding_width", val)
        self._right_padding_width = val

    @property
    def vertical_char(self):
        """The charcter used when printing table borders to draw vertical lines

        :param vertical_char: single character string used to draw vertical lines

        """
        return self._vertical_char

    @vertical_char.setter
    def vertical_char(self, val) -> None:
        """

        :param val:

        """
        val = self._unicode(val)
        self._validate_option("vertical_char", val)
        self._vertical_char = val

    @property
    def horizontal_char(self):
        """The charcter used when printing table borders to draw horizontal lines

        :param horizontal_char: single character string used to draw horizontal lines

        """
        return self._horizontal_char

    @horizontal_char.setter
    def horizontal_char(self, val) -> None:
        """

        :param val:

        """
        val = self._unicode(val)
        self._validate_option("horizontal_char", val)
        self._horizontal_char = val

    @property
    def junction_char(self):
        """The charcter used when printing table borders to draw line junctions

        :param junction_char: single character string used to draw line junctions

        """
        return self._junction_char

    @junction_char.setter
    def junction_char(self, val) -> None:
        """

        :param val:

        """
        val = self._unicode(val)
        self._validate_option("vertical_char", val)
        self._junction_char = val

    @property
    def format(self):
        """Controls whether or not HTML tables are formatted to match styling options

        :param format: True or False

        """
        return self._format

    @format.setter
    def format(self, val) -> None:
        """

        :param val:

        """
        self._validate_option("format", val)
        self._format = val

    @property
    def print_empty(self):
        """Controls whether or not empty tables produce a header and frame or just an empty string

        :param print_empty: True or False

        """
        return self._print_empty

    @print_empty.setter
    def print_empty(self, val) -> None:
        """

        :param val:

        """
        self._validate_option("print_empty", val)
        self._print_empty = val

    @property
    def attributes(self):
        """A dictionary of HTML attribute name/value pairs to be included in the <table> tag when printing HTML

        Arguments:

        attributes - dictionary of attributes


        """
        return self._attributes

    @attributes.setter
    def attributes(self, val) -> None:
        """

        :param val:

        """
        self._validate_option("attributes", val)
        self._attributes = val

    @property
    def oldsortslice(self):
        """oldsortslice - Slice rows before sorting in the 'old style'
        """
        return self._oldsortslice

    @oldsortslice.setter
    def oldsortslice(self, val) -> None:
        """

        :param val:

        """
        self._validate_option("oldsortslice", val)
        self._oldsortslice = val

    ##############################
    # OPTION MIXER               #
    ##############################

    def _get_options(self, kwargs):
        """

        :param kwargs:

        """

        options = {}
        for option in self._options:
            if option in kwargs:
                self._validate_option(option, kwargs[option])
                options[option] = kwargs[option]
            else:
                options[option] = getattr(self, "_" + option)
        return options

    ##############################
    # PRESET STYLE LOGIC         #
    ##############################

    def set_style(self, style):
        """

        :param style:

        """

        if style == DEFAULT:
            self._set_default_style()
        elif style == MSWORD_FRIENDLY:
            self._set_msword_style()
        elif style == PLAIN_COLUMNS:
            self._set_columns_style()
        elif style == RANDOM:
            self._set_random_style()
        else:
            raise Exception("Invalid pre-set style!")

    def _set_default_style(self) -> None:
        """ """

        self.header = True
        self.border = True
        self._hrules = FRAME
        self._vrules = ALL
        self.padding_width = 1
        self.left_padding_width = 1
        self.right_padding_width = 1
        self.vertical_char = "|"
        self.horizontal_char = "-"
        self.junction_char = "+"

    def _set_msword_style(self) -> None:
        """ """

        self.header = True
        self.border = True
        self._hrules = NONE
        self.padding_width = 1
        self.left_padding_width = 1
        self.right_padding_width = 1
        self.vertical_char = "|"

    def _set_columns_style(self) -> None:
        """ """

        self.header = True
        self.border = False
        self.padding_width = 1
        self.left_padding_width = 0
        self.right_padding_width = 8

    def _set_random_style(self) -> None:
        """ """

        # Just for fun!
        self.header = random.choice((True, False))
        self.border = random.choice((True, False))
        self._hrules = random.choice((ALL, FRAME, HEADER, NONE))
        self._vrules = random.choice((ALL, FRAME, NONE))
        self.left_padding_width = random.randint(0, 5)
        self.right_padding_width = random.randint(0, 5)
        self.vertical_char = random.choice("~!@#$%^&*()_+|-=\{}[];':\",./;<>?")
        self.horizontal_char = random.choice(
            "~!@#$%^&*()_+|-=\{}[];':\",./;<>?")
        self.junction_char = random.choice("~!@#$%^&*()_+|-=\{}[];':\",./;<>?")

    ##############################
    # DATA INPUT METHODS         #
    ##############################

    def add_row(self, row):
        """Add a row to the table

        :param row: row of data
        :param has: fields

        """

        if self._field_names and len(row) != len(self._field_names):
            raise Exception(
                "Row has incorrect number of values, (actual) %d!=%d (expected)" % (len(row), len(self._field_names)))
        if not self._field_names:
            self.field_names = [
                ("Field %d" % (n + 1)) for n in range(0, len(row))]
        self._rows.append(list(row))

    def del_row(self, row_index):
        """Delete a row to the table

        :param row_index: The index of the row you want to delete

        """

        if row_index > len(self._rows) - 1:
            raise Exception(
                "Cant delete row at index %d, table only has %d rows!" %
                (row_index, len(
                    self._rows)))
        del self._rows[row_index]

    def add_column(self, fieldname: str, column, align: str="c", valign: str="t"):
        """Add a column to the table.

        :param fieldname: name of the field to contain the new column of data
        :param column: column of data
        :param table: has rows
        :param align: desired alignment for this column (Default value = "c")
        :param valign: desired vertical alignment for new columns (Default value = "t")

        """

        if len(self._rows) in (0, len(column)):
            self._validate_align(align)
            self._validate_valign(valign)
            self._field_names.append(fieldname)
            self._align[fieldname] = align
            self._valign[fieldname] = valign
            for i in range(0, len(column)):
                if len(self._rows) < i + 1:
                    self._rows.append([])
                self._rows[i].append(column[i])
        else:
            raise Exception(
                "Column length %d does not match number of rows %d!" %
                (len(column), len(
                    self._rows)))

    def clear_rows(self) -> None:
        """Delete all rows from the table but keep the current field names"""

        self._rows = []

    def clear(self) -> None:
        """Delete all rows and field names from the table, maintaining nothing but styling options"""

        self._rows = []
        self._field_names = []
        self._widths = []

    ##############################
    # MISC PUBLIC METHODS        #
    ##############################

    def copy(self):
        """ """
        return copy.deepcopy(self)

    ##############################
    # MISC PRIVATE METHODS       #
    ##############################

    def _format_value(self, field, value):
        """

        :param field: param value:
        :param value:

        """
        if isinstance(value, int) and field in self._int_format:
            value = self._unicode(("%%%sd" % self._int_format[field]) % value)
        elif isinstance(value, float) and field in self._float_format:
            value = self._unicode(
                (self._float_format[field]) %
                value)
        return self._unicode(value)

    def _compute_table_width(self, options):
        """

        :param options:

        """
        table_width = 2 if options["vrules"] in (FRAME, ALL) else 0
        per_col_padding = sum(self._get_padding_widths(options))
        for index, fieldname in enumerate(self.field_names):
            if not options["fields"] or (
                    options["fields"] and fieldname in options["fields"]):
                table_width += self._widths[index] + per_col_padding
        return table_width

    def _compute_widths(self, rows, options) -> None:
        """

        :param rows: param options:
        :param options:

        """
        if options["header"]:
            widths = [_get_size(field)[0] for field in self._field_names]
        else:
            widths = len(self.field_names) * [0]

        for row in rows:
            for index, value in enumerate(row):
                fieldname = self.field_names[index]
                if fieldname in self.max_width:
                    widths[index] = max(
                        widths[index], min(
                            _get_size(value)[0], self.max_width[fieldname]))
                else:
                    widths[index] = max(widths[index], _get_size(value)[0])
                if fieldname in self.min_width:
                    widths[index] = max(
                        widths[index],
                        self.min_width[fieldname])
        self._widths = widths

        # Are we exceeding max_table_width?
        if self._max_table_width:
            table_width = self._compute_table_width(options)
            if table_width > self._max_table_width:
                # get dict with minimum widths for fields
                min_width = self.min_width

                # first calculate width for paddings and vrules this
                # space we can't shrink.

                # Space for vrules
                nonshrinkable = 2 if options["vrules"] in (FRAME, ALL) else 0
                # Space for vrules between columns
                nonshrinkable += len(self._field_names) - 1
                # Space for padding in each column
                per_col_padding = sum(self._get_padding_widths(options))
                nonshrinkable += len(widths) * per_col_padding
                # Min space for each column
                nonshrinkable += sum(min_width.values())

                # Shrink widths in proportion
                scale = float(
                    self._max_table_width - nonshrinkable) / (table_width -
                                                              nonshrinkable)

                def calculate_new_width(field_name: str, old_width):
                    """

                    :param field_name: param old_width:
                    :param old_width:

                    """
                    width = min_width[field_name]
                    # scale according to recalculated table width
                    scaled_part = int(math.floor((old_width - width) * scale))
                    # enforce minimum column width as 1 symbol
                    return max(1, width + scaled_part)

                widths = list(map(
                    calculate_new_width,
                    self._field_names,
                    widths
                ))
                self._widths = widths

        # Are we under min_table_width or title width?
        if self._min_table_width or options["title"]:
            if options["title"]:
                title_width = len(
                    options["title"]) + sum(self._get_padding_widths(options))
                if options["vrules"] in (FRAME, ALL):
                    title_width += 2
            else:
                title_width = 0
            min_table_width = self.min_table_width or 0
            min_width = max(title_width, min_table_width)
            table_width = self._compute_table_width(options)
            if table_width < min_width:
                # Grow widths in proportion
                scale = 1.0 * min_width / table_width
                widths = [int(math.ceil(w * scale)) for w in widths]
                self._widths = widths

    def _get_padding_widths(self, options):
        """

        :param options:

        """

        if options["left_padding_width"] is not None:
            lpad = options["left_padding_width"]
        else:
            lpad = options["padding_width"]
        if options["right_padding_width"] is not None:
            rpad = options["right_padding_width"]
        else:
            rpad = options["padding_width"]
        return lpad, rpad

    def _get_rows(self, options):
        """

        :param options: dictionary of option settings

        """

        if options["oldsortslice"]:
            rows = copy.deepcopy(self._rows[options["start"]:options["end"]])
        else:
            rows = copy.deepcopy(self._rows)

        # Sort
        if options["sortby"]:
            sortindex = self._field_names.index(options["sortby"])
            # Decorate
            rows = [[row[sortindex]] + row for row in rows]
            # Sort
            rows.sort(reverse=options["reversesort"], key=options["sort_key"])
            # Undecorate
            rows = [row[1:] for row in rows]

        # Slice if necessary
        if not options["oldsortslice"]:
            rows = rows[options["start"]:options["end"]]

        return rows

    def _format_row(self, row, options):
        """

        :param row: param options:
        :param options:

        """
        return [self._format_value(field, value)
                for (field, value) in zip(self._field_names, row)]

    def _format_rows(self, rows, options):
        """

        :param rows: param options:
        :param options:

        """
        return [self._format_row(row, options) for row in rows]

    ##############################
    # PLAIN TEXT STRING METHODS  #
    ##############################

    def get_string(self, **kwargs):
        """

        :param title: optional table title
        :param start: index of first data row to include in output
        :param end: index of last data row to include in output PLUS ONE
        :param fields: names of fields
        :param header: print a header showing field names
        :param border: print a border around the table
        :param hrules: controls printing of horizontal rules after rows
        :param vrules: controls printing of vertical rules between columns
        :param int_format: controls formatting of integer data
        :param float_format: controls formatting of floating point data
        :param padding_width: number of spaces on either side of column data
        :param left_padding_width: number of spaces on left hand side of column data
        :param right_padding_width: number of spaces on right hand side of column data
        :param vertical_char: single character string used to draw vertical lines
        :param horizontal_char: single character string used to draw horizontal lines
        :param junction_char: single character string used to draw line junctions
        :param sortby: name of field to sort rows by
        :param sort_key: sorting key function
        :param reversesort: True or False to sort in descending or ascending order
        :param print: empty

        """

        options = self._get_options(kwargs)

        lines = []

        # Don't think too hard about an empty table
        # Is this the desired behaviour?  Maybe we should still print the
        # header?
        if self.rowcount == 0 and (
                not options["print_empty"] or not options["border"]):
            return ""

        # Get the rows we need to print, taking into account slicing, sorting,
        # etc.
        rows = self._get_rows(options)

        # Turn all data in all rows into Unicode, formatted as desired
        formatted_rows = self._format_rows(rows, options)

        # Compute column widths
        self._compute_widths(formatted_rows, options)
        self._hrule = self._stringify_hrule(options)

        # Add title
        title = options["title"] or self._title
        if title:
            lines.append(self._stringify_title(title, options))

        # Add header or top of border
        if options["header"]:
            lines.append(self._stringify_header(options))
        elif options["border"] and options["hrules"] in (ALL, FRAME):
            lines.append(self._hrule)

        # Add rows
        for row in formatted_rows:
            lines.append(self._stringify_row(row, options))

        # Add bottom of border
        if options["border"] and options["hrules"] == FRAME:
            lines.append(self._hrule)

        return self._unicode("\n").join(lines)

    def _stringify_hrule(self, options):
        """

        :param options:

        """

        if not options["border"]:
            return ""
        lpad, rpad = self._get_padding_widths(options)
        if options['vrules'] in (ALL, FRAME):
            bits = [options["junction_char"]]
        else:
            bits = [options["horizontal_char"]]
        # For tables with no data or fieldnames
        if not self._field_names:
            bits.append(options["junction_char"])
            return "".join(bits)
        for field, width in zip(self._field_names, self._widths):
            if options["fields"] and field not in options["fields"]:
                continue
            bits.append((width + lpad + rpad) * options["horizontal_char"])
            if options['vrules'] == ALL:
                bits.append(options["junction_char"])
            else:
                bits.append(options["horizontal_char"])
        if options["vrules"] == FRAME:
            bits.pop()
            bits.append(options["junction_char"])
        return "".join(bits)

    def _stringify_title(self, title, options):
        """

        :param title: param options:
        :param options:

        """

        lines = []
        lpad, rpad = self._get_padding_widths(options)
        if options["border"]:
            if options["vrules"] == ALL:
                options["vrules"] = FRAME
                lines.append(self._stringify_hrule(options))
                options["vrules"] = ALL
            elif options["vrules"] == FRAME:
                lines.append(self._stringify_hrule(options))
        bits = []
        endpoint = options["vertical_char"] if options[
            "vrules"] in (ALL, FRAME) else " "
        bits.append(endpoint)
        title = " " * lpad + title + " " * rpad
        bits.append(self._justify(title, len(self._hrule) - 2, "c"))
        bits.append(endpoint)
        lines.append("".join(bits))
        return "\n".join(lines)

    def _stringify_header(self, options):
        """

        :param options:

        """

        bits = []
        lpad, rpad = self._get_padding_widths(options)
        if options["border"]:
            if options["hrules"] in (ALL, FRAME):
                bits.append(self._hrule)
                bits.append("\n")
            if options["vrules"] in (ALL, FRAME):
                bits.append(options["vertical_char"])
            else:
                bits.append(" ")
        # For tables with no data or field names
        if not self._field_names:
            if options["vrules"] in (ALL, FRAME):
                bits.append(options["vertical_char"])
            else:
                bits.append(" ")
        for field, width, in zip(self._field_names, self._widths):
            if options["fields"] and field not in options["fields"]:
                continue
            if self._header_style == "cap":
                fieldname = field.capitalize()
            elif self._header_style == "title":
                fieldname = field.title()
            elif self._header_style == "upper":
                fieldname = field.upper()
            elif self._header_style == "lower":
                fieldname = field.lower()
            else:
                fieldname = field
            bits.append(
                " " *
                lpad +
                self._justify(
                    fieldname,
                    width,
                    self._align[field]) +
                " " *
                rpad)
            if options["border"]:
                if options["vrules"] == ALL:
                    bits.append(options["vertical_char"])
                else:
                    bits.append(" ")
        # If vrules is FRAME, then we just appended a space at the end
        # of the last field, when we really want a vertical character
        if options["border"] and options["vrules"] == FRAME:
            bits.pop()
            bits.append(options["vertical_char"])
        if options["border"] and options["hrules"] != NONE:
            bits.append("\n")
            bits.append(self._hrule)
        return "".join(bits)

    def _stringify_row(self, row, options):
        """

        :param row: param options:
        :param options:

        """

        for index, field, value, width, in zip(
                list(range(0, len(row))), self._field_names, row, self._widths):
            # Enforce max widths
            lines = value.split("\n")
            new_lines = []
            for line in lines:
                if _str_block_width(line) > width:
                    line = textwrap.fill(line, width)
                new_lines.append(line)
            lines = new_lines
            value = "\n".join(lines)
            row[index] = value

        row_height = 0
        for c in row:
            h = _get_size(c)[1]
            if h > row_height:
                row_height = h

        bits = []
        lpad, rpad = self._get_padding_widths(options)
        for y in range(0, row_height):
            bits.append([])
            if options["border"]:
                if options["vrules"] in (ALL, FRAME):
                    bits[y].append(self.vertical_char)
                else:
                    bits[y].append(" ")

        for field, value, width, in zip(self._field_names, row, self._widths):

            valign = self._valign[field]
            lines = value.split("\n")
            dHeight = row_height - len(lines)
            if dHeight:
                if valign == "m":
                    lines = [
                        ""] * int(dHeight / 2) + lines + [""] * (dHeight - int(dHeight / 2))
                elif valign == "b":
                    lines = [""] * dHeight + lines
                else:
                    lines += [""] * dHeight

            y = 0
            for l in lines:
                if options["fields"] and field not in options["fields"]:
                    continue

                bits[y].append(
                    " " *
                    lpad +
                    self._justify(
                        l,
                        width,
                        self._align[field]) +
                    " " *
                    rpad)
                if options["border"]:
                    if options["vrules"] == ALL:
                        bits[y].append(self.vertical_char)
                    else:
                        bits[y].append(" ")
                y += 1

        # If vrules is FRAME, then we just appended a space at the end
        # of the last field, when we really want a vertical character
        for y in range(0, row_height):
            if options["border"] and options["vrules"] == FRAME:
                bits[y].pop()
                bits[y].append(options["vertical_char"])

        if options["border"] and options["hrules"] == ALL:
            bits[row_height - 1].append("\n")
            bits[row_height - 1].append(self._hrule)

        for y in range(0, row_height):
            bits[y] = "".join(bits[y])

        return "\n".join(bits)

    def paginate(self, page_length: int=58, **kwargs):
        """

        :param page_length: Default value = 58)

        """

        pages = []
        kwargs["start"] = kwargs.get("start", 0)
        true_end = kwargs.get("end", self.rowcount)
        while True:
            kwargs["end"] = min(kwargs["start"] + page_length, true_end)
            pages.append(self.get_string(**kwargs))
            if kwargs["end"] == true_end:
                break
            kwargs["start"] += page_length
        return "\f".join(pages)

    ##############################
    # HTML STRING METHODS        #
    ##############################

    def get_html_string(self, **kwargs):
        """

        :param title: optional table title
        :param start: index of first data row to include in output
        :param end: index of last data row to include in output PLUS ONE
        :param fields: names of fields
        :param header: print a header showing field names
        :param border: print a border around the table
        :param hrules: controls printing of horizontal rules after rows
        :param vrules: controls printing of vertical rules between columns
        :param int_format: controls formatting of integer data
        :param float_format: controls formatting of floating point data
        :param padding_width: number of spaces on either side of column data
        :param left_padding_width: number of spaces on left hand side of column data
        :param right_padding_width: number of spaces on right hand side of column data
        :param sortby: name of field to sort rows by
        :param sort_key: sorting key function
        :param attributes: dictionary of name
        :param xhtml: print

        """

        options = self._get_options(kwargs)

        if options["format"]:
            string = self._get_formatted_html_string(options)
        else:
            string = self._get_simple_html_string(options)

        return string

    def _get_simple_html_string(self, options):
        """

        :param options:

        """

        lines = []
        if options["xhtml"]:
            linebreak = "<br/>"
        else:
            linebreak = "<br>"

        open_tag = list()
        open_tag.append("<table")
        if options["attributes"]:
            for attr_name in options["attributes"]:
                open_tag.append(
                    " %s=\"%s\"" %
                    (attr_name, options["attributes"][attr_name]))
        open_tag.append(">")
        lines.append("".join(open_tag))

        # Title
        title = options["title"] or self._title
        if title:
            cols = len(
                options["fields"]) if options["fields"] else len(
                self.field_names)
            lines.append("    <tr>")
            lines.append("        <td colspan=%d>%s</td>" % (cols, title))
            lines.append("    </tr>")

        # Headers
        if options["header"]:
            lines.append("    <tr>")
            for field in self._field_names:
                if options["fields"] and field not in options["fields"]:
                    continue
                lines.append(
                    "        <th style='text-align: left;'>%s</th>" %
                    escape(field).replace(
                        "\n",
                        linebreak))
            lines.append("    </tr>")

        # Data
        rows = self._get_rows(options)
        formatted_rows = self._format_rows(rows, options)
        for row in formatted_rows:
            lines.append("    <tr>")
            for field, datum in zip(self._field_names, row):
                if options["fields"] and field not in options["fields"]:
                    continue
                lines.append(
                    "        <td>%s</td>" %
                    escape(datum).replace(
                        "\n",
                        linebreak))
            lines.append("    </tr>")

        lines.append("</table>")

        return self._unicode("\n").join(lines)

    def _get_formatted_html_string(self, options):
        """

        :param options:

        """

        lines = []
        lpad, rpad = self._get_padding_widths(options)
        if options["xhtml"]:
            linebreak = "<br/>"
        else:
            linebreak = "<br>"

        open_tag = list()
        open_tag.append("<table")
        if options["border"]:
            if options["hrules"] == ALL and options["vrules"] == ALL:
                open_tag.append(" frame=\"box\" rules=\"all\"")
            elif options["hrules"] == FRAME and options["vrules"] == FRAME:
                open_tag.append(" frame=\"box\"")
            elif options["hrules"] == FRAME and options["vrules"] == ALL:
                open_tag.append(" frame=\"box\" rules=\"cols\"")
            elif options["hrules"] == FRAME:
                open_tag.append(" frame=\"hsides\"")
            elif options["hrules"] == ALL:
                open_tag.append(" frame=\"hsides\" rules=\"rows\"")
            elif options["vrules"] == FRAME:
                open_tag.append(" frame=\"vsides\"")
            elif options["vrules"] == ALL:
                open_tag.append(" frame=\"vsides\" rules=\"cols\"")
        if options["attributes"]:
            for attr_name in options["attributes"]:
                open_tag.append(
                    " %s=\"%s\"" %
                    (attr_name, options["attributes"][attr_name]))
        open_tag.append(">")
        lines.append("".join(open_tag))

        # Title
        title = options["title"] or self._title
        if title:
            cols = len(
                options["fields"]) if options["fields"] else len(
                self.field_names)
            lines.append("    <tr>")
            lines.append("        <td colspan=%d>%s</td>" % (cols, title))
            lines.append("    </tr>")

        # Headers
        if options["header"]:
            lines.append("    <tr>")
            for field in self._field_names:
                if options["fields"] and field not in options["fields"]:
                    continue
                lines.append(
                    "        <th style=\"padding-left: %dem; padding-right: %dem; text-align: left;\">%s</th>" % (
                        lpad, rpad, escape(field).replace("\n", linebreak)))
            lines.append("    </tr>")

        # Data
        rows = self._get_rows(options)
        formatted_rows = self._format_rows(rows, options)
        aligns = []
        valigns = []
        for field in self._field_names:
            aligns.append(
                {"l": "left", "r": "right", "c": "center"}[self._align[field]])
            valigns.append(
                {"t": "top", "m": "middle", "b": "bottom"}[self._valign[field]])
        for row in formatted_rows:
            lines.append("    <tr>")
            for field, datum, align, valign in zip(
                    self._field_names, row, aligns, valigns):
                if options["fields"] and field not in options["fields"]:
                    continue
                lines.append(
                    "        <td style=\"padding-left: %dem; padding-right: %dem; text-align: %s; vertical-align: %s\">%s</td>" % (
                        lpad, rpad, align, valign, escape(datum).replace("\n", linebreak)))
            lines.append("    </tr>")
        lines.append("</table>")

        return self._unicode("\n").join(lines)


##############################
# UNICODE WIDTH FUNCTIONS    #
##############################

def _char_block_width(char: str):
    """

    :param char:

    """
    # Basic Latin, which is probably the most common case
    # if char in range(0x0021, 0x007e):
    # if char >= 0x0021 and char <= 0x007e:
    if 0x0021 <= char <= 0x007e:
        return 1
    # Chinese, Japanese, Korean (common)
    if 0x4e00 <= char <= 0x9fff:
        return 2
    # Hangul
    if 0xac00 <= char <= 0xd7af:
        return 2
    # Combining?
    if unicodedata.combining(uni_chr(char)):
        return 0
    # Hiragana and Katakana
    if 0x3040 <= char <= 0x309f or 0x30a0 <= char <= 0x30ff:
        return 2
    # Full-width Latin characters
    if 0xff01 <= char <= 0xff60:
        return 2
    # CJK punctuation
    if 0x3000 <= char <= 0x303e:
        return 2
    # Backspace and delete
    if char in (0x0008, 0x007f):
        return -1
    # Other control characters
    elif char in (0x0000, 0x000f, 0x001f):
        return 0
    # Take a guess
    return 1


def _str_block_width(val):
    """

    :param val:

    """
    return sum(itermap(_char_block_width, itermap(ord, _re.sub("", val))))
