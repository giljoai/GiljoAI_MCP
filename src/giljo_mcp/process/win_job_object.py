# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Windows Job Object wrapper for orphan-process containment.

On Windows: creates a Job Object with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE so
every child assigned to the job is killed automatically when this process
(the launcher) exits — even on crash or SIGKILL.

On Linux/macOS: no-op class; the caller should use os.setsid() on the child
and register a process-group kill at atexit.  This module provides a
consistent interface across platforms so startup.py needs no conditional
branches at call sites.

Usage (Windows)::

    job = WindowsJobObject()
    proc = subprocess.Popen(...)
    job.assign(proc.pid)
    # Hold `job` for the launcher's lifetime; close() is called by atexit or
    # via the context manager.

    # — or —

    with WindowsJobObject() as job:
        proc = subprocess.Popen(...)
        job.assign(proc.pid)
"""

from __future__ import annotations

import atexit
import platform
from typing import Self


__all__ = ["WindowsJobObject"]

_IS_WINDOWS = platform.system() == "Windows"


if _IS_WINDOWS:
    import ctypes
    import ctypes.wintypes

    # -----------------------------------------------------------------------
    # Win32 constants
    # -----------------------------------------------------------------------
    _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
    _JobObjectBasicLimitInformation = 2  # unused — we use Extended
    _JobObjectExtendedLimitInformation = 9

    # -----------------------------------------------------------------------
    # Win32 structures
    # -----------------------------------------------------------------------
    class _JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):  # noqa: N801
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", ctypes.wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", ctypes.wintypes.DWORD),
            ("Affinity", ctypes.POINTER(ctypes.c_ulong)),
            ("PriorityClass", ctypes.wintypes.DWORD),
            ("SchedulingClass", ctypes.wintypes.DWORD),
        ]

    class _IO_COUNTERS(ctypes.Structure):  # noqa: N801
        _fields_ = [
            ("ReadOperationCount", ctypes.c_uint64),
            ("WriteOperationCount", ctypes.c_uint64),
            ("OtherOperationCount", ctypes.c_uint64),
            ("ReadTransferCount", ctypes.c_uint64),
            ("WriteTransferCount", ctypes.c_uint64),
            ("OtherTransferCount", ctypes.c_uint64),
        ]

    class _JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):  # noqa: N801
        _fields_ = [
            ("BasicLimitInformation", _JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ("IoInfo", _IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    # -----------------------------------------------------------------------
    # Win32 API bindings
    # -----------------------------------------------------------------------
    _kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

    _kernel32.CreateJobObjectW.restype = ctypes.wintypes.HANDLE
    _kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p]

    _kernel32.SetInformationJobObject.restype = ctypes.wintypes.BOOL
    _kernel32.SetInformationJobObject.argtypes = [
        ctypes.wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.wintypes.DWORD,
    ]

    _kernel32.AssignProcessToJobObject.restype = ctypes.wintypes.BOOL
    _kernel32.AssignProcessToJobObject.argtypes = [
        ctypes.wintypes.HANDLE,
        ctypes.wintypes.HANDLE,
    ]

    _kernel32.OpenProcess.restype = ctypes.wintypes.HANDLE
    _kernel32.OpenProcess.argtypes = [
        ctypes.wintypes.DWORD,
        ctypes.wintypes.BOOL,
        ctypes.wintypes.DWORD,
    ]

    _kernel32.CloseHandle.restype = ctypes.wintypes.BOOL
    _kernel32.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]

    _PROCESS_ALL_ACCESS = 0x1F0FFF

    class WindowsJobObject:
        """
        Context-manager / explicit-handle wrapper around a Windows Job Object.

        The job is created with ``JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`` so the
        OS kills all assigned processes when the handle is closed (i.e. when
        the launcher exits).
        """

        def __init__(self) -> None:
            self._handle: int | None = None
            self._create()
            atexit.register(self.close)

        def _create(self) -> None:
            handle = _kernel32.CreateJobObjectW(None, None)
            if not handle:
                raise OSError(f"CreateJobObjectW failed: {ctypes.GetLastError()}")

            info = _JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE

            ok = _kernel32.SetInformationJobObject(
                handle,
                _JobObjectExtendedLimitInformation,
                ctypes.byref(info),
                ctypes.sizeof(info),
            )
            if not ok:
                _kernel32.CloseHandle(handle)
                raise OSError(f"SetInformationJobObject failed: {ctypes.GetLastError()}")

            self._handle = handle

        def assign(self, pid: int) -> None:
            """Assign a process (by PID) to this job."""
            if self._handle is None:
                return
            _inherit_handle = ctypes.wintypes.BOOL(0)  # False: don't inherit handle
            proc_handle = _kernel32.OpenProcess(_PROCESS_ALL_ACCESS, _inherit_handle, pid)
            if not proc_handle:
                raise OSError(f"OpenProcess({pid}) failed: {ctypes.GetLastError()}")
            try:
                ok = _kernel32.AssignProcessToJobObject(self._handle, proc_handle)
                if not ok:
                    raise OSError(f"AssignProcessToJobObject(pid={pid}) failed: {ctypes.GetLastError()}")
            finally:
                _kernel32.CloseHandle(proc_handle)

        def close(self) -> None:
            """Close the job handle.  All assigned processes are killed by the OS."""
            if self._handle is not None:
                _kernel32.CloseHandle(self._handle)
                self._handle = None

        # Context-manager protocol
        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_: object) -> None:
            self.close()

else:
    # ------------------------------------------------------------------
    # Non-Windows stub — no-op implementation with identical interface
    # ------------------------------------------------------------------

    class WindowsJobObject:  # type: ignore[no-redef]
        """
        No-op stub on non-Windows platforms.

        On Linux/macOS the caller should use ``os.setsid()`` on the child
        and register a process-group kill via ``atexit``.  This stub keeps
        call-site code platform-neutral.
        """

        def __init__(self) -> None:
            pass

        def assign(self, pid: int) -> None:
            pass

        def close(self) -> None:
            pass

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_: object) -> None:
            pass
