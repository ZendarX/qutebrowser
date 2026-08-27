# SPDX-FileCopyrightText: ZendarX <zendarx@x4.network>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for qutebrowser.browser.webengine.webextensions."""

import dataclasses
import pathlib

import pytest

from qutebrowser.browser.webengine import webextensions
from qutebrowser.qt.core import QObject, QUrl


class FakeSignal:

    def __init__(self) -> None:
        self._callbacks = []

    def connect(self, callback) -> None:
        self._callbacks.append(callback)

    def emit(self, *args) -> None:
        for callback in self._callbacks:
            callback(*args)


class FakeExtensionInfo:

    def name(self) -> str:
        return "Test extension"

    def id(self) -> str:
        return "test-id"

    def description(self) -> str:
        return "A test extension"

    def path(self) -> str:
        return "/tmp/test-extension"

    def error(self) -> str:
        return ""

    def actionPopupUrl(self) -> QUrl:
        return QUrl("chrome-extension://test-id/popup.html")

    def isEnabled(self) -> bool:
        return True

    def isLoaded(self) -> bool:
        return True

    def isInstalled(self) -> bool:
        return False


class FakeQtManager:

    def __init__(self) -> None:
        self.loadFinished = FakeSignal()
        self.loaded_paths = []

    def extensions(self):
        return [FakeExtensionInfo()]

    def loadExtension(self, path: str) -> None:
        self.loaded_paths.append(path)


class FakeProfile(QObject):

    def __init__(self, manager=None) -> None:
        super().__init__()
        self._manager = manager

    def extensionManager(self):
        return self._manager


@pytest.fixture
def qt_manager():
    return FakeQtManager()


@pytest.fixture
def manager(qt_manager):
    return webextensions.ExtensionManager(FakeProfile(qt_manager))


def test_extensions(manager):
    assert manager.extensions() == (
        webextensions.ExtensionInfo(
            name="Test extension",
            extension_id="test-id",
            description="A test extension",
            path="/tmp/test-extension",
            error="",
            action_popup_url="chrome-extension://test-id/popup.html",
            enabled=True,
            loaded=True,
            installed=False,
        ),
    )


def test_extension_info_is_immutable(manager):
    extension = manager.extensions()[0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        extension.enabled = False


def test_load_unpacked(manager, qt_manager):
    manager.load_unpacked(pathlib.Path("/tmp/test-extension"))
    assert qt_manager.loaded_paths == ["/tmp/test-extension"]


def test_load_finished(manager, qt_manager, qtbot):
    with qtbot.waitSignal(manager.load_finished) as blocker:
        qt_manager.loadFinished.emit(FakeExtensionInfo())

    extension = blocker.args[0]
    assert extension.extension_id == "test-id"
    assert extension.loaded


@pytest.mark.parametrize("profile", [object(), FakeProfile()])
def test_unavailable(profile):
    manager = webextensions.ExtensionManager(profile)

    assert not manager.available
    with pytest.raises(webextensions.UnsupportedError, match="6.10 or newer"):
        manager.extensions()
    with pytest.raises(webextensions.UnsupportedError, match="6.10 or newer"):
        manager.load_unpacked("/tmp/test-extension")


def test_init(monkeypatch, qt_manager):
    profile = FakeProfile(qt_manager)
    monkeypatch.setattr(webextensions, "manager", None)

    webextensions.init(profile)

    assert webextensions.manager is not None
    assert webextensions.manager.available
