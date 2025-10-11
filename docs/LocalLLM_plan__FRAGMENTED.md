# Project Plan — Local LLM Integration for Serena MCP (4 GPU Tiers)

**Author:** Patrik / Serena MCP stack
**Date:** 2025-10-06
**Goal:** Reduce premium-model spend while preserving decision quality by offloading high‑volume tasks (planning drafts, scaffolding, tests, docs, research triage) to local LLMs across four NVIDIA tiers.

---

## 0) Executive Summary (No‑BS)

* Keep **final mission approval**, **architecture/security**, and **hairy debugging** on premium.
* Move **first‑pass planning**, **CRUD/frontend scaffolding**, **tests**, **docstrings/READMEs**, and **research triage** to local.
* Standardize MCP tools and prompts so handoffs are invisible regardless of tier.
* Ship in **three phases** (P1: planner-draft + docs/tests; P2: CRUD/frontend; P3: refactor + review), with SLOs and rollback gates.

---

## 1) Scope & Success Criteria

**In scope**: On‑prem LLM serving, MCP agent routing, RAG plumbing, quantization/runtime tuning, CI smoke tests, telemetry, and rollout playbooks for 4 GPU tiers.
**Success criteria**:

* ≥ **50%** reduction in premium token cost within 30 days of P2 completion.
* **No regression** in PR acceptance rate or post‑merge defects (baseline vs 30‑day window).
* Latency P95 under **1.2×** premium for offloaded tasks.

---

## 2) Workload Split (Agents → Local vs Premium)

**Local (offload):** Planner‑Draft, Boilerplate/Builder, Test Writer, Doc Scribe, Research Triage, Basic Code Review.
**Premium:** Final Mission Review, Architecture/Security/Networking, Complex Debugger, Final PR Gate.

**Escalation triggers → premium:** any auth/crypto touch, kernel or network stack changes, data migrations altering prod rows, unexplained test flakiness, perf regressions >15%.

---

## 3) Core Architecture

* **Serving runtimes (choose per tier):**

  * **TensorRT‑LLM** for lowest latency on fixed shapes (planner).
  * **vLLM / SGLang** for multi‑tenant throughput (builder/docs/tests).
* **Quantization:** primary Q4/Q5 where needed; keep full‑precision embeddings.
* **RAG:** Qdrant/pgvector with deterministic chunking + max marginal relevance; cap prompt with **distilled context packs** (planner sees full pack; premium sees *diff*).
* **MCP tool surface (shared by all models):**

  * `context.pack({project_id, docs:[…], max_tokens})`
  * `plan.create({inputs, constraints}) → mission_draft` (LOCAL)
  * `plan.review({mission_draft}) → mission_final` (PREMIUM)
  * `kb.search({query, k, minScore})`
  * `repo.diff({since})`, `repo.apply({patch})`
  * `tests.run({subset})`, `bench.run({scenario})`

---

## 4) Tier Matrix (Hardware → Models → Roles)

| Tier | GPU                        | Architecture             | Primary Local “Planner‑Draft”                                         | Local Code/Docs Model(s)                                   | Notes                                                |
| ---- | -------------------------- | ------------------------ | --------------------------------------------------------------------- | ---------------------------------------------------------- | ---------------------------------------------------- |
| A    | **96 GB Blackwell**        | Pro 6000 Blackwell 96 GB | **Llama‑3.x 70B Instruct (128k)**, Q4/Q5 via TensorRT‑LLM or vLLM     | **Codestral‑22B** and/or **Qwen2.5‑Coder‑32B** (quantized) | Run planner + builder concurrently; headroom for KV. |
| B    | **48 GB Ada**              | RTX 6000 Ada 48 GB       | **Qwen2.5‑32B Instruct** (prefer ≥32k ctx); fallback Llama‑3 8B + RAG | **Codestral‑22B** or **Qwen2.5‑Coder‑32B Q4**              | 70B not recommended; prioritize throughput.          |
| C    | **32 GB Blackwell (5090)** | RTX 5090 32 GB           | **Qwen2.5 14B/32B Q4** as planner; Llama‑3 8B for fast drafts         | **Codestral‑22B Q4** or **Qwen2.5‑Coder‑32B Q4**           | Tight KV budget; cap ctx to 16–32k.                  |
| D    | **24 GB Ada (4040)**       | RTX 4040 24 GB           | **Llama‑3 8B** or **Qwen2.5 14B** (+aggressive RAG)                   | **Codestral‑22B Q4** or **Qwen‑Coder‑14B**                 | Optimize for latency; keep missions small.           |

> **Why these picks:** Planner needs longest stable window available on each tier; builder needs code priors + speed. 70B is ideal on 96 GB; below that, 32B/22B code models + 8–14B generalist cover 90% of offload volume.

---

## 5) Capacity Planning & SLOs

**Assumptions** (tune after benchmarking):

* **A (96 GB):** Planner‑Draft (70B) P95 ~1.2–1.6 tok/ms; 2–4 concurrent long prompts; Builder 22–32B handles 6–10 concurrent code/doc tasks.
* **B (48 GB):** Planner 32B P95 ~2–3 tok/ms; 2–3 conc.; Builder 22–32B: 5–8 conc.
* **C (32 GB):** Planner 14–32B Q4 P95 ~3–4 tok/ms; 1–2 conc.; Builder 22–32B Q4: 3–5 conc.
* **D (24 GB):** Planner 8–14B P95 ~4–5 tok/ms; 1–2 conc.; Builder 22B Q4 or 14B: 2–4 conc.

**SLOs:** P95 end‑to‑end for offloaded tasks ≤ **1.2×** premium baseline for scaffolding/docs/tests; Planner‑Draft ≤ **1.5×**.

---

## 6) Prompt/Context Strategy

* **Planner‑Draft Prompt** (LOCAL): consumes **context pack** (vision, tech stack, constraints) up to tier ctx cap; outputs **typed JSON**: mission, agent graph, dependencies, risks.
* **Plan‑Review Prompt** (PREMIUM): sees only `mission_draft + diffs + open risks` → returns signed‐off `mission_final`.
* **Builder Prompt**: deterministic templates per language/framework; expects pointers to repo paths + acceptance tests.
* **Research Triage Prompt**: summarize KB hits with citations + confidence; label items to escalate.

---

## 7) Runtimes & Quantization

* **A (96 GB):** Llama‑70B via **TensorRT‑LLM** (production) or vLLM (dev). Code models via **vLLM/SGLang**. Quant Q4/Q5 as needed; keep ctx at 128k for planner.
* **B/C/D:** Prefer **vLLM** for scheduler/throughput; Codestral/Qwen‑Coder in Q4; cap ctx to prevent KV OOM.
* **KV cache**: configure separate GPU memory pools per model; set hard ctx caps per tier.

---

## 8) MCP Agent Routing

```yaml
routing:
  - when: task in ["mission_create_draft"]
    tier: any
    model: local.planner
  - when: task in ["mission_review","arch_decision","security_review","complex_debug"]
    model: premium.claude
  - when: task in ["scaffold","tests","docs","basic_review"]
    model: local.builder
  - escalate_if: [touches_auth, touches_crypto, migration_modifies_prod_rows, p95_latency>1.5x, test_flakiness>5%]
    to: premium.claude
```

---

## 9) Deployment (per tier) — Compose Skeletons

> Adjust `image:` tags to your registry; these are reference patterns.

### Tier A (96 GB) — Planner 70B + Builder 22/32B

```yaml
version: "3.9"
services:
  planner70b:
    image: local/llm-trtllm-llama70b:latest
    deploy: {resources: {reservations: {devices: [{capabilities: [gpu]}]}}}
    environment:
      - MODEL=llama-70b-instruct
      - CONTEXT=128000
      - QUANT=Q4
    ports: ["8001:8001"]

  builder22b:
    image: local/llm-vllm-codestral22b:latest
    environment:
      - MODEL=codestral-22b-instruct
      - CONTEXT=32000
      - QUANT=Q4
    ports: ["8002:8002"]

  mcp-gateway:
    image: local/mcp-router:latest
    environment:
      - ROUTING_CONFIG=/cfg/routing.yaml
    volumes:
      - ./cfg:/cfg
    ports: ["8080:8080"]
```

### Tier B (48 GB) — Planner 32B + Builder 22/32B

```yaml
services:
  planner32b:
    image: local/llm-vllm-qwen32b:latest
    environment:
      - MODEL=qwen2.5-32b-instruct
      - CONTEXT=32000
      - QUANT=Q4
    ports: ["8001:8001"]
  builder22b: { ...same as above... }
  mcp-gateway: { ...same... }
```

### Tier C (32 GB, 5090) — Planner 14–32B Q4 + Builder 22/32B Q4

```yaml
services:
  planner14b:
    image: local/llm-vllm-llama8b-or-qwen14b:latest
    environment:
      - MODEL=qwen2.5-14b-instruct
      - CONTEXT=24000
      - QUANT=Q4
    ports: ["8001:8001"]
  builder22b: { ... }
  mcp-gateway: { ... }
```

### Tier D (24 GB, 4040) — Planner 8–14B + Builder 22B Q4 (or 14B)

```yaml
services:
  planner8b:
    image: local/llm-vllm-llama8b:latest
    environment:
      - MODEL=llama-3-8b-instruct
      - CONTEXT=16000
      - QUANT=Q4
    ports: ["8001:8001"]
  builder22b:
    image: local/llm-vllm-codestral22b:latest
    environment:
      - MODEL=codestral-22b-instruct
      - CONTEXT=16000
      - QUANT=Q4
    ports: ["8002:8002"]
  mcp-gateway: { ... }
```

---

## 10) Rollout Plan (Milestones & Gates)

**Phase 1 — Planner‑Draft + Docs/Tests (2 weeks)**

* Implement `context.pack`, `plan.create`, `plan.review`.
* Stand up serving for selected tier; run latency/throughput baselines.
* Ship Doc Scribe + Test Writer agents; enable **premium review gate**.
* **Gate:** premium spend ↓ ≥20% with neutral quality metrics.

**Phase 2 — CRUD/Frontend Scaffolding (2–3 weeks)**

* Enable Builder agent for controllers, migrations, React components.
* Add `qa.review` (style/obvious bugs) locally; premium for arch/security.
* **Gate:** premium spend ↓ ≥40%; PR acceptance rate unchanged.

**Phase 3 — Refactor + Basic Review (2 weeks)**

* Allow local refactors under LOC/complexity thresholds.
* Add automatic **escalation triggers** and rollback.
* **Gate:** no increase in post‑merge defects over 30 days.

---

## 11) Testing & Benchmarks

* **Golden set**: curated tasks per agent class (mission drafts, CRUD, tests, docs, refactors).
* **Metrics**: latency P95, tokens saved, PR acceptance, defect rate, rework %, hallucination rate (manual spot checks), coverage deltas.
* **Load tests**: 1, 3, 5, 8 concurrent flows per tier; verify KV OOM boundaries.

---

## 12) Risks & Mitigations

* **Context truncation** (lower tiers) → aggressive RAG + distilled packs; enforce ctx caps.
* **Security regressions** → mandatory premium reviews on sensitive diffs.
* **Model drift** → pin container digests; monthly eval re‑baselining.
* **Throughput cliffs** → isolate planner from builder; separate GPU memory pools.

---

## 13) Ops Runbook (per deployment)

* Health: `/metrics` (tokens/s, queue depth, P95), `/readyz`, `/livez` endpoints.
* Scaling: separate autoscaling knobs for planner vs builder (even on single GPU, queue disciplines differ).
* Logs: structured JSON w/ `mission_id`, `agent`, `model`, `ctx_len`, `escalated`.
* Rollback: compose profile switch back to premium‑only path; freeze local endpoints.

---

## 14) Procurement & Images

* Build/publish images with fixed tags; maintain **A/B** images per tier (stable vs experimental).
* Keep a slim **dev** variant (smaller ctx caps) for laptops; prod images locked.

---

## 15) Next Steps (Actionable)

1. Pick **Tier A** first (you have 96 GB).
2. Implement `context.pack` + `plan.create` + `plan.review`.
3. Stand up **planner (70B)** + **builder (22/32B)** with quant plans.
4. Wire routing policies + escalation triggers.
5. Run P1 golden tests; compare against premium‑only baseline; ship if gates met.

---

## Appendix A — Prompt Templates (short)

**Planner‑Draft (LOCAL):** *Inputs*: context_pack, constraints. *Output*: JSON `{mission, agent_graph, dependencies, risks, open_questions}` (≤ 2,000 tokens).
**Plan‑Review (PREMIUM):** *Inputs*: mission_draft + diffs + risks. *Output*: JSON `{mission_final, decisions, escalations}`.
**Builder (LOCAL):** *Inputs*: mission_final sections + repo paths. *Output*: changeset + tests + docs w/ rationale.

---

## Appendix B — Dev Log (initial)

* 2025‑10‑06: Created 4‑tier local LLM integration plan; defined routing, models, deployment skeletons, and rollout gates.

---

## Appendix C — Peer Review (GitHub Copilot)

**Date:** 2025-10-06
**Reviewer:** GitHub Copilot

### 1. Overall Assessment

This is an exceptionally well-crafted and comprehensive project plan. I am in strong agreement with the core strategy, architecture, and phased rollout. The tiered hardware approach is realistic, the workload split is logical, and the risk management is thorough. The plan demonstrates a deep understanding of the technical and practical challenges involved.

My feedback below is intended to build upon this strong foundation, offering minor refinements rather than significant changes.

### 2. Suggestions & Refinements

*   **Model Evaluation Cadence:** The model choices are excellent for the current landscape. I suggest formalizing the "monthly eval re-baselining" mentioned in the risks section into a recurring task. This process should include scouting for new state-of-the-art open models and updating the "golden set" of benchmarks to prevent metric drift and ensure the MCP is always leveraging the most efficient models available for each tier.

*   **Developer Experience (DX) and Local Tooling:** The "slim dev variant" is a crucial component. I recommend expanding on this by defining a standardized `giljo-cli` or similar tool. This tool would allow developers to:
    *   Easily switch between local-only and remote-premium endpoints.
    *   Run local validation tests against the routing logic (`routing.yaml`).
    *   Stream logs from local model servers with consistent formatting.
    *   This would improve the inner development loop and make it easier to debug issues before they reach CI.

*   **Advanced RAG Strategies:** The current RAG plan is solid. To further enhance performance on lower-resource Tiers (C and D), consider exploring:
    *   **Re-ranking:** Use a small, fast model to re-rank the initial retrieval results from pgvector/Qdrant before injecting them into the final context. This can significantly improve signal-to-noise ratio.
    *   **Hypothetical Document Embeddings (HyDE):** For complex queries, generate a hypothetical answer first and then use its embedding to find more relevant documents. This can be particularly effective for the `Planner-Draft` agent.

*   **Security of Local Endpoints:** The plan correctly escalates sensitive tasks. However, the local model serving endpoints themselves introduce a new attack surface. I recommend explicitly adding a task to secure the `mcp-gateway` and the model servers. This should include:
    *   Enforcing authentication on all local API endpoints (e.g., via a shared secret or mTLS).
    *   Implementing strict network policies in the Docker environment to ensure services can only communicate with the gateway, not externally.

*   **Explicit Cost-Benefit Note:** The plan's goal of a 50% reduction in premium spend is clear. It would be beneficial to add a brief note under the "Executive Summary" or "Scope" acknowledging the trade-off: the upfront and ongoing operational costs (hardware, power, engineering maintenance) are being accepted in exchange for long-term reduction in variable token costs and increased operational sovereignty.

### 3. Conclusion

This plan is ready for execution. My suggestions are aimed at enhancing its robustness, developer experience, and long-term adaptability. I fully endorse moving forward with Phase 1 as outlined.
