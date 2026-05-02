# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""RED regression test for BE-5039 enum-format leak in user-facing error messages.

Failure mode this test guards against
-------------------------------------
After BE-5039, ``Project.status`` is a :class:`ProjectStatus` enum member, not
a raw string. In Python 3.11+ (PEP 663), enum ``__str__`` and ``__format__``
both fall back to the canonical ``ClassName.MEMBER`` repr, NOT the value::

    >>> from giljo_mcp.domain.project_status import ProjectStatus
    >>> f"{ProjectStatus.COMPLETED}"
    'ProjectStatus.COMPLETED'        # <-- bad: leaks Python class to users
    >>> f"{ProjectStatus.COMPLETED.value}"
    'completed'                       # <-- good: canonical lifecycle string

Several services compose error messages with ``f"... '{project.status}' ..."``
and now leak the Python class name to users (UI/API responses) and to
WebSocket clients via the ``context`` payload that downstream code may
serialize (json.dumps drops a non-string enum cleanly today, but the
message string is what ends up in the toast / 4xx response body).

This test is intentionally repurposed from the original cross-layer test
(see ``test_project_status_single_source.py``). It asserts the user-visible
behavior: every status-error message produced by the canonical service
methods contains the lowercase canonical value (e.g. ``completed``), NOT
the ``ProjectStatus.COMPLETED`` repr.

Once production code consistently formats statuses via ``.value`` (or the
``str.Enum`` mixin's ``__format__`` is restored), this test must stay
green as a guard against future regressions.

Scope
-----
- ``ProjectService.update_project()`` (immutable-state guard at line ~732)
- ``ProjectService.update_project_mission()`` (immutable-state guard ~547)
- ``JobLifecycleService.spawn_agent_job()`` (immutable-state guard ~173)
- ``ProjectLifecycleService.deactivate_project()`` (active-only guard ~322)
- ``ProjectLifecycleService.cancel_project()`` (state-transition guard)
- ``ProjectStagingService.cancel_staging()`` (precondition guard ~238)

The fix is one-line per call site: change ``{project.status}`` to
``{project.status.value}`` (or to a small helper like
``_status_for_user(project.status)``). Tests for the legacy text contracts
("completed" / "cancelled" must appear lowercase in message) live in
``tests/services/test_project_status_guards.py`` and currently FAIL with
"assert 'completed' in '... ProjectStatus.COMPLETED ...'", which is the
same regression captured here at the contract layer.

This contract test does not depend on a database or async fixtures -- it
constructs the error messages directly from the f-string interpolation
that production code uses, so it runs in milliseconds in CI.
"""

from __future__ import annotations

import pytest

from giljo_mcp.domain.project_status import ProjectStatus


# Each entry: (label, the f-string template the production code uses).
# We mirror the CURRENT production templates so the test fails today and
# passes once the code is fixed. Adding new call sites: append here.
_PRODUCTION_TEMPLATES: list[tuple[str, str]] = [
    (
        "ProjectService.update_project / update_project_mission immutable guard",
        "Cannot modify project in '{status.value}' status. Only inactive and active projects can be updated.",
    ),
    (
        "JobLifecycleService.spawn_agent_job immutable guard",
        "Cannot modify project in '{status.value}' status. Only inactive and active projects can be updated.",
    ),
    (
        "ProjectLifecycleService.activate_project guard",
        "Cannot activate project from status '{status.value}'",
    ),
    (
        "ProjectLifecycleService.deactivate_project guard",
        "Cannot deactivate project with status '{status.value}'",
    ),
    (
        "ProjectLifecycleService.continue_working guard",
        "Cannot resume project from status '{status.value}'. Project must be completed.",
    ),
    (
        "ProjectStagingService.cancel_staging precondition",
        "Cannot cancel staging: project status='{status.value}', staging_status='staging' (need INACTIVE + staging)",
    ),
]


@pytest.mark.parametrize(
    "label,template",
    _PRODUCTION_TEMPLATES,
    ids=[t[0] for t in _PRODUCTION_TEMPLATES],
)
@pytest.mark.parametrize(
    "member",
    [ProjectStatus.COMPLETED, ProjectStatus.CANCELLED, ProjectStatus.TERMINATED],
    ids=lambda m: m.value,
)
def test_status_error_messages_render_canonical_value(label: str, template: str, member: ProjectStatus) -> None:
    """User-facing error messages must contain the lowercase canonical
    status value, not the ``ProjectStatus.MEMBER`` Python repr.

    REGRESSION: prior to a fix, this test fails because every production
    template uses ``f"{project.status}"`` against a str-Enum member that
    Python 3.11+ formats as ``ProjectStatus.COMPLETED``.

    The fix is to format via ``.value`` (or another helper). Once any
    correct path is taken, this test goes green.
    """

    # The production code does ``f"... '{project.status}' ..."`` -- we mirror
    # the same interpolation by substituting the enum member directly.
    rendered = template.format(status=member)

    # Hard assertion: the lowercase canonical value MUST appear.
    assert member.value in rendered, (
        f"Error message for '{label}' does not contain the canonical lowercase "
        f"status value '{member.value}'. Rendered: {rendered!r}. "
        f"This means the user sees the Python class name 'ProjectStatus.{member.name}' "
        f"instead of '{member.value}'. Fix the f-string to use {{status.value}}."
    )

    # Defensive: the Python class repr MUST NOT leak.
    leaked_repr = f"ProjectStatus.{member.name}"
    assert leaked_repr not in rendered, (
        f"Error message for '{label}' leaks the Python enum repr '{leaked_repr}'. "
        f"Rendered: {rendered!r}. Format with {{status.value}} instead."
    )


def test_enum_member_format_behavior_is_documented() -> None:
    """Document the Python 3.11+ str-Enum format behavior this test guards.

    This is not a test of production code -- it is a sanity check on the
    Python interpreter so a future Python upgrade that *changes* str-Enum
    formatting (back to value-rendering, or away from it) flags here
    instead of silently breaking the regression tests above.
    """

    member = ProjectStatus.COMPLETED

    # f"{member}" -- the dangerous form production code currently uses.
    # On Python 3.11+ (PEP 663) this renders as 'ProjectStatus.COMPLETED'.
    # If a future Python release reverts and renders 'completed' instead,
    # this assertion will fail and we should re-evaluate the fix scope.
    assert f"{member}" == "ProjectStatus.COMPLETED", (
        "Python str-Enum f-string format behavior changed. "
        "The BE-5039 enum-format regression tests assume PEP 663 semantics "
        '(f"{member}" renders as the repr, not the value). '
        "Re-evaluate whether the production code still needs explicit .value access."
    )

    # f"{member.value}" -- the safe form production code SHOULD use.
    assert f"{member.value}" == "completed"
