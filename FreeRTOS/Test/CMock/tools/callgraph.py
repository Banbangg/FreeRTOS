#!/usr/bin/env python3
###############################################################################
# FreeRTOS
# Copyright (C) 2021 Amazon.com, Inc. or its affiliates.  All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# https://www.FreeRTOS.org
# https://github.com/FreeRTOS
###############################################################################
import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Set

target_files = sys.argv[1:]

for f in target_files:
    if not os.path.isfile(f):
        print("ERROR: Input file {} does not exist.".format(f))
        exit(1)

ret = subprocess.run(
    [
        "cflow",
        "--print-level",
        "--no-main",
        "--omit-arguments",
        "--omit-symbol-names",
        "--all",
    ]
    + target_files,
    capture_output=True,
)

lineregex = (
    r"^{\s*(?P<level>\d+)} \s*"
    r"(?P<function>\S*)\(\) \<.* at "
    r"(?P<filename>.*):\d+\>(:)?"
    r"(?P<xref> \[see \d+\])?$"
)
linepattern = re.compile(lineregex)
parent_stack = [""]
last_indent_level = 0
last_function_name = ""
callmap: Dict[str, Set[str]] = {}
callmap[""] = set()

for line in ret.stdout.decode("utf-8").splitlines():
    match = linepattern.match(line)
    # Check that the function for this line is in a target file
    if match and (match.group("filename") in target_files):
        indent_level = int(match.group("level"))
        function_name = match.group("function")

        # Add an entry for the current function
        if function_name not in callmap:
            callmap[function_name] = set()

        # Indent -> lower in the call stack
        if indent_level > last_indent_level:
            # add last function to the stack
            parent_stack.append(last_function_name)

        # Outdent -> higher in the call stack
        elif last_indent_level > indent_level:
            de_indent_steps = last_indent_level - indent_level
            # De-indent = pop off the stack
            for _i in range(0, de_indent_steps):
                parent_stack.pop()

        # Update parent function(s) dependency list
        for parent in parent_stack:
            callmap[parent].add(function_name)

        last_function_name = function_name
        last_indent_level = indent_level

# remove zero-level fake parent
callmap.pop("")

callmap_list: Dict[str, List[str]] = {}
# convert sets to lists for json output
for key in callmap:
    temp_list = list(callmap[key])
    callmap_list[key] = temp_list

print(json.dumps(callmap_list))
