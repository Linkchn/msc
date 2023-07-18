#
# Copyright 2016 Chris Cummins <chrisc.101@gmail.com>.
#
# This file is part of CLgen.
#
# CLgen is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# CLgen is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with CLgen.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Deep learning program generator
"""
from __future__ import absolute_import, print_function, with_statement

import json
import os
import re
import six
import tarfile

from copy import deepcopy
from contextlib import contextmanager
from hashlib import sha1
from pkg_resources import resource_filename, resource_string, require

import labm8
from labm8 import fs

from clgen import config as cfg


class CLgenError(Exception):
    """
    Module error.
    """
    pass


class InternalError(CLgenError):
    """
    An internal module error. This class of errors should not leak outside
    of the module into user code.
    """
    pass


class UserError(CLgenError):
    """
    Raised in case of bad user interaction, e.g. an invalid argument.
    """
    pass


class NotImplementedError(InternalError):
    """
    Code not found.
    """
    pass


class File404(InternalError):
    """
    Data not found.
    """
    pass


class InvalidFile(UserError):
    """
    Raised in case a file contains invalid contents.
    """
    pass


class CLgenObject(object):
    """
    Base object for CLgen classes.
    """
    pass


def version():
    """
    Get the package version.

    *DO NOT* try to parse this or derive any special major/minor version
    information from it. Treat it as an opaque char array. The only valid
    operators for comparing versions are == and !=.

    Returns:
        str: Version string.
    """
    return "clgen"


def must_exist(*path_components, **kwargs):
    """
    Require that a file exists.

    Arguments:
        *path_components (str): Components of the path.
        **kwargs (optional): Key "Error" specifies the exception type to throw.

    Returns:
        str: Path.
    """
    assert(len(path_components))

    path = os.path.expanduser(os.path.join(*path_components))
    if not os.path.exists(path):
        Error = kwargs.get("Error", File404)
        e = Error("path '{}' does not exist".format(path))
        e.path = path
        raise e
    return path


def checksum(data):
    """
    Checksum a byte stream.

    Arguments:
        data (bytes): Data.

    Returns:
        str: Checksum.
    """
    try:
        return sha1(data).hexdigest()
    except Exception:
        raise InternalError("failed to checksum '{}'".format(data[:100]))


def checksum_str(string):
    """
    Checksum a string.

    Arguments:
        string (str): String.

    Returns:
        str: Checksum.
    """
    try:
        return checksum(str(string).encode('utf-8'))
    except UnicodeEncodeError:
        raise InternalError("failed to encode '{}'".format(string[:100]))


def checksum_file(*path_components):
    """
    Checksum a file.

    Arguments:
        path_components (str): Path.

    Returns:
        str: Checksum.
    """
    path = must_exist(*path_components)

    try:
        with open(path, 'rb') as infile:
            return checksum(infile.read())
    except Exception:
        raise CLgenError("failed to read '{}'".format(path))


def unpack_archive(*components, **kwargs):
    """
    Unpack a compressed archive.

    Arguments:
        *components (str[]): Absolute path.
        **kwargs (dict, optional): Set "compression" to compression type.
            Default: bz2. Set "dir" to destination directory. Defaults to the
            directory of the archive.
    """
    path = fs.abspath(*components)
    compression = kwargs.get("compression", "bz2")
    dir = kwargs.get("dir", fs.dirname(path))

    fs.cd(dir)
    tar = tarfile.open(path, "r:" + compression)
    tar.extractall()
    tar.close()
    fs.cdpop()

    return dir


def get_substring_idxs(substr, s):
    """
    Return a list of indexes of substr. If substr not found, list is
    empty.

    Arguments:
        substr (str): Substring to match.
        s (str): String to match in.

    Returns:
        list of int: Start indices of substr.
    """
    return [m.start() for m in re.finditer(substr, s)]


def package_path(*path):
    """
    Path to package file.

    Arguments:

        *path (str[]): Path components.

    Returns:

        str: Path.
    """
    path = os.path.expanduser(os.path.join(*path))
    abspath = resource_filename(__name__, path)
    return must_exist(abspath)


def data_path(*path):
    """
    Path to package file.

    Arguments:

        *path (str[]): Path components.

    Returns:

        str: Path.
    """
    return package_path("data", *path)


def package_data(*path):
    """
    Read package data file.

    Arguments:
        path (str): The relative path to the data file, e.g. 'share/foo.txt'.

    Returns:
        bytes: File contents.

    Raises:
        InternalError: In case of IO error.
    """
    # throw exception if file doesn't exist
    package_path(*path)

    try:
        return resource_string(__name__, fs.path(*path))
    except Exception:
        raise InternalError("failed to read package data '{}'".format(path))


def package_str(*path):
    """
    Read package data file as a string.

    Arguments:
        path (str): The relative path to the text file, e.g. 'share/foo.txt'.

    Returns:
        str: File contents.

    Raises:
        InternalError: In case of IO error.
    """
    try:
        return package_data(*path).decode('utf-8')
    except UnicodeDecodeError:
        raise InternalError("failed to decode package data '{}'".format(path))


def sql_script(name):
    """
    Read SQL script to string.

    Arguments:
        name (str): The name of the SQL script (without file extension).

    Returns:
        str: SQL script.
    """
    path = fs.path('data', 'sql', str(name) + ".sql")
    return package_str(path)


def format_json(data):
    """
    Pretty print JSON.

    Arguments:
        data (dict): JSON blob.
    """
    return json.dumps(data, sort_keys=True, indent=2, separators=(',', ': '))


def loads(text, **kwargs):
    """
    Deserialize `text` (a `str` or `unicode` instance containing a JSON
    document with Python or JavaScript like comments) to a Python object.

    Taken from `commentjson <https://github.com/vaidik/commentjson>`_, written
    by `Vaidik Kapoor <https://github.com/vaidik>`_.

    Copyright (c) 2014 Vaidik Kapoor, MIT license.

    :param text: serialized JSON string with or without comments.
    :param kwargs: all the arguments that `json.loads
                   <http://docs.python.org/2/library/json.html#json.loads>`_
                   accepts.
    :returns: `dict` or `list`.
    """
    regex = r'\s*(#|\/{2}).*$'
    regex_inline = r'(:?(?:\s)*([A-Za-z\d\.{}]*)|((?<=\").*\"),?)(?:\s)*(((#|(\/{2})).*)|)$'
    lines = text.split('\n')

    for index, line in enumerate(lines):
        if re.search(regex, line):
            if re.search(r'^' + regex, line, re.IGNORECASE):
                lines[index] = ""
            elif re.search(regex_inline, line):
                lines[index] = re.sub(regex_inline, r'\1', line)

    return json.loads('\n'.join(lines), **kwargs)


def load_json_file(path):
    """
    Load a JSON data blob.

    Arguments:
        path (str): Path to file.

    Returns:
        array or dict: JSON data.

    Raises:
        File404: If path does not exist.
        InvalidFile: If JSON is malformed.
    """
    try:
        with open(must_exist(path)) as infile:
            return loads(infile.read())
    except ValueError as e:
        raise InvalidFile(
            "malformed JSON file '{path}'. Message from parser: {err}"
            .format(path=os.path.basename(path)), err=str(e))


@contextmanager
def terminating(thing):
    """
    Context manager to terminate object at end of scope.
    """
    try:
        yield thing
    finally:
        thing.terminate()


def write_file(path, contents):
    fs.mkdir(fs.dirname(path))
    with open(path, 'w') as outfile:
        outfile.write(contents)


def main(model, sampler):
    """
    Main entry point for clgen.

    Arguments:
        model (str): Path to model.
        sample (str): Path to sampler.
    """
    import clgen.model
    import clgen.sampler

    if model.endswith(".tar.bz2"):
        model = clgen.model.from_tar(model)
    else:
        model_json = load_json_file(model)
        model = clgen.model.from_json(model_json)
    model.train()

    sampler_json = load_json_file(sampler)
    sampler = clgen.sampler.from_json(sampler_json)
    sampler.sample(model)
