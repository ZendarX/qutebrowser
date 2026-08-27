# SPDX-FileCopyrightText: ZendarX <zendarx@x4.network>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""QtWebEngine WebExtension integration."""

import dataclasses
import os
from typing import Any, Optional, Union

from qutebrowser.qt.core import QObject, pyqtSignal
from qutebrowser.qt.webenginecore import QWebEngineProfile


class UnsupportedError(Exception):

    """Raised when the current QtWebEngine has no WebExtension support."""


@dataclasses.dataclass(frozen=True)
class ExtensionInfo:

    """A Qt-independent snapshot of a WebExtension's state."""

    name: str
    extension_id: str
    description: str
    path: str
    error: str
    action_popup_url: str
    enabled: bool
    loaded: bool
    installed: bool

    @classmethod
    def from_qt(cls, extension: Any) -> "ExtensionInfo":
        """Create a snapshot from a QWebEngineExtensionInfo object."""
        return cls(
            name=extension.name(),
            extension_id=extension.id(),
            description=extension.description(),
            path=extension.path(),
            error=extension.error(),
            action_popup_url=extension.actionPopupUrl().toString(),
            enabled=extension.isEnabled(),
            loaded=extension.isLoaded(),
            installed=extension.isInstalled(),
        )


class ExtensionManager(QObject):

    """Small wrapper around a profile's QWebEngineExtensionManager.

    The Qt API was added in Qt 6.10. Keeping the availability check and Qt
    value objects behind this wrapper lets the rest of qutebrowser remain
    importable with older Qt versions.

    Signals:
        load_finished: Emitted with an ExtensionInfo snapshot when an
                       asynchronous unpacked-extension load finishes.
    """

    load_finished = pyqtSignal(object)

    def __init__(
        self,
        profile: QWebEngineProfile,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)

        extension_manager_getter = getattr(profile, "extensionManager", None)
        if extension_manager_getter is None:
            self._qt_manager = None
            return

        self._qt_manager = extension_manager_getter()
        if self._qt_manager is not None:
            self._qt_manager.loadFinished.connect(self._on_load_finished)

    @property
    def available(self) -> bool:
        """Whether the current QtWebEngine exposes WebExtension support."""
        return self._qt_manager is not None

    def extensions(self) -> tuple[ExtensionInfo, ...]:
        """Return snapshots of all extensions known to the profile."""
        qt_manager = self._manager()
        return tuple(
            ExtensionInfo.from_qt(info) for info in qt_manager.extensions())

    def load_unpacked(self, path: Union[os.PathLike[str], str]) -> None:
        """Start asynchronously loading an unpacked extension from *path*."""
        self._manager().loadExtension(os.fspath(path))

    def _manager(self) -> Any:
        if self._qt_manager is None:
            raise UnsupportedError(
                "WebExtensions require QtWebEngine 6.10 or newer")
        return self._qt_manager

    def _on_load_finished(self, extension: Any) -> None:
        self.load_finished.emit(ExtensionInfo.from_qt(extension))


manager: Optional[ExtensionManager] = None


def init(profile: QWebEngineProfile) -> None:
    """Initialize WebExtension support for the default profile."""
    global manager
    manager = ExtensionManager(profile, parent=profile)
