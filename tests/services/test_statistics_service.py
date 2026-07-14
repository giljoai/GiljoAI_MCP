# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Tests for StatisticsService (BE-5022b).

Verifies that the service layer correctly wraps the statistics repositories
and enforces tenant isolation on all analytics queries.

These tests seed a known mix of rows into the real test database and assert the
exact non-zero counts the service returns. The previous version asserted only
key-shape and zero-counts on an empty tenant, so a broken aggregation/WHERE
clause (e.g. a dropped tenant_key filter or a miscounted status) would have
passed silently. A second tenant is seeded to prove cross-tenant isolation.
"""

import random
from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio

from giljo_mcp.database import tenant_session_context
from giljo_mcp.models import AgentExecution, AgentJob, Message, Product, Project, Task
from giljo_mcp.services.statistics_service import StatisticsService


@pytest_asyncio.fixture
async def stats_service(db_manager, db_session):
    """Create StatisticsService instance with test session."""
    return StatisticsService(
        db_manager=db_manager,
        test_session=db_session,
    )


def _project(tenant_key, status, **extra):
    # product_id intentionally left NULL: an "only one active project per product"
    # partial unique index (idx_project_single_active_per_product) would otherwise
    # reject multiple active projects sharing a product. NULLs are distinct, so the
    # seeded mix of active projects is allowed without coupling each to its own product.
    return Project(
        tenant_key=tenant_key,
        name="Stats Project",
        description="seeded for statistics tests",
        mission="seeded mission",
        status=status,
        series_number=random.randint(1, 9000),
        **extra,
    )


@pytest_asyncio.fixture
async def seeded_stats(db_session, test_tenant_key):
    """Seed tenant A with a known row mix; tenant B with 2 projects (isolation).

    Tenant A totals: 7 projects (4 active incl. 1 staged, 2 completed, 1 cancelled),
    5 messages (2 pending / 1 ack / 1 completed / 1 failed), 3 agent executions
    (working / waiting / complete), 2 tasks (1 completed / 1 pending).
    """
    tenant_a = test_tenant_key
    tenant_b = f"tk_b_{uuid4().hex[:12]}"  # distinct tenant; tenant_key is VARCHAR(36)

    with tenant_session_context(db_session, tenant_a):
        product_a = Product(tenant_key=tenant_a, name="Product A", description="d", is_active=True)
        db_session.add(product_a)
        await db_session.flush()

        projects = [
            *[_project(tenant_a, "active") for _ in range(3)],
            _project(tenant_a, "active", staging_status="staging_complete"),
            *[_project(tenant_a, "completed") for _ in range(2)],
            _project(tenant_a, "cancelled"),
        ]
        db_session.add_all(projects)
        await db_session.flush()

        msg_project = projects[0]
        for status in ("pending", "pending", "acknowledged", "completed", "failed"):
            db_session.add(Message(tenant_key=tenant_a, project_id=msg_project.id, content="hi", status=status))

        job = AgentJob(
            job_id=str(uuid4()),
            tenant_key=tenant_a,
            project_id=msg_project.id,
            mission="seeded",
            job_type="implementer",
            status="active",
            created_at=datetime.now(UTC),
        )
        db_session.add(job)
        await db_session.flush()
        for status in ("working", "waiting", "complete"):
            db_session.add(
                AgentExecution(
                    job_id=job.job_id,
                    agent_id=str(uuid4()),
                    tenant_key=tenant_a,
                    agent_display_name="implementer",
                    agent_name=f"implementer-{status}",
                    status=status,
                    completed_at=datetime.now(UTC) if status == "complete" else None,
                )
            )

        db_session.add_all(
            [
                Task(tenant_key=tenant_a, product_id=product_a.id, title="t1", status="completed"),
                Task(tenant_key=tenant_a, product_id=product_a.id, title="t2", status="pending"),
            ]
        )
        await db_session.flush()

    with tenant_session_context(db_session, tenant_b):
        product_b = Product(tenant_key=tenant_b, name="Product B", description="d", is_active=True)
        db_session.add(product_b)
        await db_session.flush()
        db_session.add_all([_project(tenant_b, "active") for _ in range(2)])
        await db_session.flush()

    return {"tenant_a": tenant_a, "tenant_b": tenant_b}


@pytest.mark.asyncio
async def test_get_system_stats_returns_expected_keys(stats_service, test_tenant_key):
    """System stats should return all expected metric keys."""
    result = await stats_service.get_system_stats(test_tenant_key)
    expected_keys = {
        "total_projects",
        "active_projects",
        "completed_projects",
        "total_agents",
        "active_agents",
        "total_messages",
        "pending_messages",
        "total_tasks",
        "completed_tasks",
        "total_agents_spawned",
        "total_jobs_completed",
        "projects_staged",
        "projects_cancelled",
    }
    assert set(result.keys()) == expected_keys


@pytest.mark.asyncio
async def test_get_system_stats_counts_seeded_data(stats_service, seeded_stats):
    """System stats must report the exact seeded counts (catches broken aggregation)."""
    result = await stats_service.get_system_stats(seeded_stats["tenant_a"])

    assert result["total_projects"] == 7
    assert result["active_projects"] == 4  # 3 plain + 1 staged-but-active
    assert result["completed_projects"] == 2
    assert result["projects_cancelled"] == 1
    assert result["projects_staged"] == 1
    assert result["total_messages"] == 5
    assert result["pending_messages"] == 2
    assert result["total_agents"] == 3
    assert result["active_agents"] == 2  # working + waiting
    assert result["total_jobs_completed"] == 1  # complete
    assert result["total_tasks"] == 2
    assert result["completed_tasks"] == 1


@pytest.mark.asyncio
async def test_get_system_stats_isolates_tenants(stats_service, seeded_stats):
    """A second tenant sees only its own rows — proves the tenant_key filter."""
    tenant_a = await stats_service.get_system_stats(seeded_stats["tenant_a"])
    tenant_b = await stats_service.get_system_stats(seeded_stats["tenant_b"])

    assert tenant_a["total_projects"] == 7
    assert tenant_b["total_projects"] == 2  # only tenant B's own projects
    assert tenant_b["total_messages"] == 0
    assert tenant_b["total_agents"] == 0


@pytest.mark.asyncio
async def test_get_system_stats_unknown_tenant_returns_zeros(stats_service):
    """An unseeded tenant returns zeros (empty-path smoke)."""
    result = await stats_service.get_system_stats("nonexistent_tenant_key")
    assert result["total_projects"] == 0
    assert result["total_agents"] == 0
    assert result["total_messages"] == 0


@pytest.mark.asyncio
async def test_get_dashboard_stats_returns_expected_keys(stats_service, test_tenant_key):
    """Dashboard stats should return all expected top-level keys."""
    result = await stats_service.get_dashboard_stats(test_tenant_key)
    expected_keys = {
        "project_status_dist",
        "taxonomy_dist",
        "agent_role_dist",
        "recent_projects",
        "recent_memories",
        "task_status_dist",
        "execution_mode_dist",
        "products",
        "total_commits",  # BE-6078
    }
    assert set(result.keys()) == expected_keys


@pytest.mark.asyncio
async def test_get_total_commits_counts_all_git_commits(stats_service, db_session, test_tenant_key):
    """BE-6078: total_commits sums jsonb_array_length(git_commits) across ALL
    product_memory_entries — not the capped 10-item preview. Tenant-scoped and
    honors the per-product dashboard filter; a foreign tenant's commits and
    other-product commits must not leak into a product-filtered count."""
    from giljo_mcp.models.product_memory_entry import ProductMemoryEntry

    tenant_a = test_tenant_key
    tenant_b = f"tk_b_{uuid4().hex[:12]}"

    def _commit(n: int) -> dict:
        return {"sha": f"{n:040x}", "message": f"commit {n}"}

    def _entry(tenant_key, product_id, seq, commit_count):
        return ProductMemoryEntry(
            tenant_key=tenant_key,
            product_id=product_id,
            sequence=seq,
            entry_type="project_completion",
            source="write_360_memory_v1",
            timestamp=datetime.now(UTC),
            git_commits=[_commit(i) for i in range(commit_count)],
        )

    with tenant_session_context(db_session, tenant_a):
        product_a1 = Product(tenant_key=tenant_a, name="PA1", description="d", is_active=True)
        product_a2 = Product(tenant_key=tenant_a, name="PA2", description="d", is_active=False)
        db_session.add_all([product_a1, product_a2])
        await db_session.flush()
        db_session.add_all(
            [
                _entry(tenant_a, product_a1.id, 1, 3),  # 3 commits
                _entry(tenant_a, product_a1.id, 2, 4),  # 4 commits
                _entry(tenant_a, product_a1.id, 3, 0),  # empty array contributes 0
                _entry(tenant_a, product_a2.id, 1, 5),  # other product: 5 commits
            ]
        )
        await db_session.flush()

    with tenant_session_context(db_session, tenant_b):
        product_b = Product(tenant_key=tenant_b, name="PB", description="d", is_active=True)
        db_session.add(product_b)
        await db_session.flush()
        db_session.add(_entry(tenant_b, product_b.id, 1, 99))  # foreign tenant: must not leak
        await db_session.flush()

    # Tenant-wide (all products for tenant A): 3 + 4 + 0 + 5 = 12.
    all_products = await stats_service.get_dashboard_stats(tenant_a)
    assert all_products["total_commits"] == 12

    # Product-filtered to product_a1: 3 + 4 + 0 = 7 (excludes product_a2 and tenant B).
    filtered = await stats_service.get_dashboard_stats(tenant_a, product_id=str(product_a1.id))
    assert filtered["total_commits"] == 7

    # Foreign tenant sees only its own commits (99), proving isolation.
    foreign = await stats_service.get_dashboard_stats(tenant_b)
    assert foreign["total_commits"] == 99


@pytest.mark.asyncio
async def test_agent_role_distribution_ticker_and_folding(db_session, test_tenant_key):
    """Agent Roles pill: the ticker counts every agent an orchestrator spawned,
    the bar categorizes them by base role.

    Regression for the Dashboard reading "0 spawned": the prior query counted
    ONLY executions whose agent_name exactly matched a configured template, so
    specialized subagent names (implementer-backend / implementer-frontend) and
    template-less jobs were silently dropped. This asserts:
      - implementer-backend + implementer-frontend fold into "implementer";
      - a template-linked (FK) execution counts under its template;
      - the orchestrator/conductor itself is excluded (it is not spawned BY an
        orchestrator);
      - a spawned name that maps to no template still counts (its own segment);
      - the ticker (sum of segment counts) equals the total workers spawned.
    """
    from giljo_mcp.models.templates import AgentTemplate
    from giljo_mcp.repositories.job_statistics_repository import JobStatisticsRepository

    tenant = test_tenant_key
    with tenant_session_context(db_session, tenant):
        impl = AgentTemplate(tenant_key=tenant, name="implementer", background_color="#aabbcc")
        tester = AgentTemplate(tenant_key=tenant, name="tester", background_color="#ddeeff")
        reviewer = AgentTemplate(tenant_key=tenant, name="reviewer", background_color="#123456")
        db_session.add_all([impl, tester, reviewer])
        await db_session.flush()

        project = _project(tenant, "active")
        db_session.add(project)
        await db_session.flush()

        def _job(job_type, template_id=None):
            job = AgentJob(
                job_id=str(uuid4()),
                tenant_key=tenant,
                project_id=project.id,
                mission="m",
                job_type=job_type,
                status="active",
                template_id=template_id,
                created_at=datetime.now(UTC),
            )
            db_session.add(job)
            return job

        def _exec(job, display_name, agent_name):
            db_session.add(
                AgentExecution(
                    job_id=job.job_id,
                    agent_id=str(uuid4()),
                    tenant_key=tenant,
                    agent_display_name=display_name,
                    agent_name=agent_name,
                    status="working",
                    started_at=datetime.now(UTC),
                )
            )

        # Orchestrator — excluded from the ticker (it is the assigner).
        _exec(_job("orchestrator"), "orchestrator", "orchestrator")
        # Two implementer variants (name-path, no template_id) — fold to implementer.
        _exec(_job("Backend-Templates-Removal"), "Backend-Templates-Removal", "implementer-backend")
        _exec(_job("Frontend-Templates-Removal"), "Frontend-Templates-Removal", "implementer-frontend")
        # One more backend implementer → implementer total = 3.
        _exec(_job("Backend-2"), "Backend-2", "implementer-backend")
        # Exact template-name match.
        _exec(_job("tester"), "tester", "tester")
        # FK path: job carries a template_id (reviewer) regardless of agent_name.
        _exec(_job("Code Checker", template_id=reviewer.id), "Code Checker", "code-checker")
        # A spawned agent that maps to no template — still counts under its own label.
        _exec(_job("data-wrangler"), "data-wrangler", "data-wrangler")
        await db_session.flush()

    repo = JobStatisticsRepository(None)
    with tenant_session_context(db_session, tenant):
        dist = await repo.get_agent_role_distribution(db_session, tenant)
    by_label = {seg["label"]: seg["count"] for seg in dist}

    assert by_label["Implementer"] == 3  # backend + backend + frontend, folded
    assert by_label["Tester"] == 1
    assert by_label["Reviewer"] == 1  # via FK template_id, not agent_name
    assert by_label["Data Wrangler"] == 1  # unmatched name still counts
    assert "Orchestrator" not in by_label  # the assigner is not a spawned agent

    ticker = sum(seg["count"] for seg in dist)
    assert ticker == 6  # 3 impl + 1 tester + 1 reviewer + 1 wrangler; orchestrator excluded


@pytest.mark.asyncio
async def test_get_system_stats_uses_single_session(stats_service, monkeypatch):
    """BE-6063a A1: all 13 counts must share ONE session, not open one each.

    Pins the round-trip collapse (landed in f023044ce) so the BE-6063 off-loop /
    tenant-guard follow-ups (links b/c) cannot regress ``get_system_stats`` back
    to a session-per-count fan-out on the single sync worker. Spies on
    ``_get_session`` and asserts exactly one ``async with`` is entered for the
    full set of counts.
    """
    real_get_session = stats_service._get_session
    calls = 0

    def _counting_get_session(tenant_key=None):
        nonlocal calls
        calls += 1
        return real_get_session(tenant_key)

    monkeypatch.setattr(stats_service, "_get_session", _counting_get_session)

    result = await stats_service.get_system_stats("any_tenant_key")

    assert calls == 1, f"expected one shared session for all counts, got {calls}"
    assert "total_projects" in result
