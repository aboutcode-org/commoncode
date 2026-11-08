#
# Copyright (c) nexB Inc. and others. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/aboutcode-org/commoncode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import io
import tarfile
import warnings

import pytest

from commoncode.archive import extract_tar
from commoncode.archive import extract_tar_raw


def make_tar(location, name="file.txt", content=b"hello"):
    with tarfile.open(location, "w") as tar:
        info = tarfile.TarInfo(name)
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))


def has_tar_deprecation_warning(caught):
    return [
        warning
        for warning in caught
        if issubclass(warning.category, DeprecationWarning)
        and "tar archive" in str(warning.message).lower()
    ]


def test_extract_tar_does_not_emit_a_deprecation_warning(tmp_path):
    archive = str(tmp_path / "test.tar")
    make_tar(archive)
    target_dir = str(tmp_path / "target")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        extract_tar(archive, target_dir)

    assert not has_tar_deprecation_warning(caught)
    with open(str(tmp_path / "target" / "file.txt")) as extracted:
        assert extracted.read() == "hello"


def test_extract_tar_raw_does_not_emit_a_deprecation_warning(tmp_path):
    archive = str(tmp_path / "test.tar")
    make_tar(archive)
    target_dir = str(tmp_path / "target")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        extract_tar_raw(archive, target_dir)

    assert not has_tar_deprecation_warning(caught)
    with open(str(tmp_path / "target" / "file.txt")) as extracted:
        assert extracted.read() == "hello"


def test_extract_tar_honors_an_explicit_filter(tmp_path):
    if not hasattr(tarfile, "FilterError"):
        pytest.skip("tarfile extraction filters require Python 3.12+")

    archive = str(tmp_path / "test.tar")
    make_tar(archive, name="../escaped.txt")
    target_dir = tmp_path / "target"
    target_dir.mkdir()

    # The "data" filter rejects members that would escape the target directory
    try:
        extract_tar(str(archive), str(target_dir), filter="data")
    except tarfile.FilterError:
        pass
    else:
        raise AssertionError("expected the 'data' filter to reject ../escaped.txt")

    assert not (tmp_path / "escaped.txt").exists()


class LegacyTar:
    """
    Simulate a tarfile.TarFile from a Python without tar extraction filters.
    """

    def __init__(self):
        self.calls = []

    def extractall(self, path, members=None, **kwargs):
        if "filter" in kwargs:
            raise TypeError("TarFile.extractall() got an unexpected keyword argument 'filter'")
        self.calls.append((path, members))


def test_extractall_falls_back_on_pythons_without_filters(tmp_path):
    from commoncode.archive import _extractall

    tar = LegacyTar()
    target_dir = str(tmp_path)

    _extractall(tar, target_dir, members=["member"], filter="data")
    _extractall(tar, target_dir, members=["member"])

    assert tar.calls == [
        (target_dir, ["member"]),
        (target_dir, ["member"]),
    ]
