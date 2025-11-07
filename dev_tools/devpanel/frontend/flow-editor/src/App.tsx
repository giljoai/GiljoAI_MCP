import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type Edge,
  type EdgeChange,
  type NodeChange,
} from "reactflow";
import clsx from "clsx";
import { ChangeEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { FlowDocument, FlowNode, FlowNodeData, FlowSummary, SaveState } from "./types";

const API_BASE = (import.meta.env.VITE_DEVPANEL_API as string) ?? "http://127.0.0.1:8283";
const AUTOSAVE_DELAY = Number(import.meta.env.VITE_AUTOSAVE_MS ?? 1500);

type Selection = { type: "node" | "edge"; id: string } | null;
type FlowContext = {
  source?: string;
  generated_at?: string;
  updated_at?: string;
  metadata?: Record<string, unknown>;
};

const STATUS_OPTIONS = ["draft", "validated", "in-progress", "blocked", "deprecated"];

const normalizeNodes = (nodes: FlowNode[] | undefined): FlowNode[] =>
  (nodes ?? []).map((node, idx) => ({
    id: node.id ?? `node-${idx}`,
    type: node.type ?? "default",
    position: node.position ?? { x: 80, y: idx * 140 },
    data: {
      label: node.data?.label ?? `Step ${idx + 1}`,
      description: node.data?.description ?? "",
      status: node.data?.status ?? "draft",
      code_reference: node.data?.code_reference ?? "",
      notes: node.data?.notes ?? [],
    },
    style: node.style,
  }));

const normalizeEdges = (edges: Edge[] | undefined): Edge[] =>
  (edges ?? []).map((edge, idx) => ({
    id: edge.id ?? `edge-${idx}`,
    source: edge.source,
    target: edge.target,
    type: edge.type ?? "default",
    label: edge.label,
    data: edge.data,
  }));

function App() {
  const [flows, setFlows] = useState<FlowSummary[]>([]);
  const [activeFlowId, setActiveFlowId] = useState<string>("");
  const [nodes, setNodes] = useState<FlowNode[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [flowMeta, setFlowMeta] = useState<{ title: string; description: string }>({ title: "", description: "" });
  const [flowContext, setFlowContext] = useState<FlowContext>({});
  const [selection, setSelection] = useState<Selection>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [listError, setListError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [dirty, setDirty] = useState<boolean>(false);
  const suppressAutosave = useRef<boolean>(false);
  const saveTimer = useRef<ReturnType<typeof window.setTimeout> | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const selectedNode = useMemo(
    () => (selection?.type === "node" ? nodes.find((node) => node.id === selection.id) ?? null : null),
    [selection, nodes],
  );
  const selectedEdge = useMemo(
    () => (selection?.type === "edge" ? edges.find((edge) => edge.id === selection.id) ?? null : null),
    [selection, edges],
  );

  useEffect(() => {
    const fetchFlows = async () => {
      setListError(null);
      try {
        const resp = await fetch(`${API_BASE}/flow-editor/flows`);
        if (!resp.ok) {
          throw new Error(`Flow index unavailable (${resp.status})`);
        }
        const data = await resp.json();
        const entries: FlowSummary[] = data.flows ?? [];
        setFlows(entries);
        if (entries.length && !activeFlowId) {
          setActiveFlowId(entries[0].id);
        }
      } catch (err) {
        setListError(err instanceof Error ? err.message : "Unable to load flow list");
      }
    };
    fetchFlows();
  }, []);

  const hydrateFlow = useCallback((doc: FlowDocument) => {
    suppressAutosave.current = true;
    setNodes(normalizeNodes(doc.nodes));
    setEdges(normalizeEdges(doc.edges));
    setFlowMeta({
      title: doc.title ?? doc.id ?? "Untitled flow",
      description: doc.description ?? "",
    });
    setFlowContext({
      source: doc.source,
      generated_at: doc.generated_at,
      updated_at: doc.updated_at ?? doc.generated_at,
      metadata: doc.metadata,
    });
    setDirty(false);
    setSaveError(null);
    setSaveState("idle");
    setSelection(null);
    suppressAutosave.current = false;
  }, []);

  const loadFlow = useCallback(
    async (flowId: string) => {
      if (!flowId) {
        return;
      }
      setLoading(true);
      try {
        const resp = await fetch(`${API_BASE}/flow-editor/flows/${flowId}`);
        if (!resp.ok) {
          throw new Error(`Unable to load flow ${flowId} (${resp.status})`);
        }
        const doc = (await resp.json()) as FlowDocument;
        hydrateFlow(doc);
      } catch (err) {
        setListError(err instanceof Error ? err.message : "Unable to load flow details");
      } finally {
        setLoading(false);
      }
    },
    [hydrateFlow],
  );

  useEffect(() => {
    if (activeFlowId) {
      loadFlow(activeFlowId);
    }
  }, [activeFlowId, loadFlow]);

  useEffect(
    () => () => {
      if (saveTimer.current) {
        window.clearTimeout(saveTimer.current);
      }
    },
    [],
  );

  const saveCurrentFlow = useCallback(async () => {
    if (!activeFlowId) {
      return;
    }
    setSaveState("saving");
    setSaveError(null);
    try {
      const payload: FlowDocument = {
        id: activeFlowId,
        title: flowMeta.title || activeFlowId,
        description: flowMeta.description,
        source: flowContext.source,
        generated_at: flowContext.generated_at,
        metadata: flowContext.metadata,
        nodes,
        edges,
      };
      const resp = await fetch(`${API_BASE}/flow-editor/flows/${activeFlowId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        const detail = await resp.json().catch(() => ({}));
        throw new Error(detail.detail ?? `Save failed (${resp.status})`);
      }
      const body = await resp.json();
      setDirty(false);
      setSaveState("idle");
      setFlowContext((ctx) => ({ ...ctx, updated_at: body.flow?.updated_at ?? new Date().toISOString() }));
    } catch (err) {
      setSaveState("error");
      setSaveError(err instanceof Error ? err.message : "Autosave failed");
    }
  }, [activeFlowId, edges, flowContext.generated_at, flowContext.metadata, flowContext.source, flowMeta.description, flowMeta.title, nodes]);

  const queueAutosave = useCallback(() => {
    if (suppressAutosave.current || !activeFlowId) {
      return;
    }
    setDirty(true);
    if (saveTimer.current) {
      window.clearTimeout(saveTimer.current);
    }
    saveTimer.current = window.setTimeout(() => {
      void saveCurrentFlow();
    }, AUTOSAVE_DELAY);
  }, [activeFlowId, saveCurrentFlow]);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
      setNodes((nds) => applyNodeChanges(changes, nds));
      queueAutosave();
    },
    [queueAutosave],
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
      setEdges((eds) => applyEdgeChanges(changes, eds));
      queueAutosave();
    },
    [queueAutosave],
  );

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge({ ...connection, type: "smoothstep", animated: true }, eds));
      queueAutosave();
    },
    [queueAutosave],
  );

  const updateNodeData = useCallback(
    (nodeId: string, patch: Partial<FlowNodeData>) => {
      setNodes((nds) =>
        nds.map((node) => (node.id === nodeId ? { ...node, data: { ...node.data, ...patch } } : node)),
      );
      queueAutosave();
    },
    [queueAutosave],
  );

  const updateEdge = useCallback(
    (edgeId: string, patch: Partial<Edge>) => {
      setEdges((eds) => eds.map((edge) => (edge.id === edgeId ? { ...edge, ...patch } : edge)));
      queueAutosave();
    },
    [queueAutosave],
  );

  const handleAddNode = useCallback(() => {
    const nextIndex = nodes.length + 1;
    const id = `node-${Date.now()}`;
    setNodes((nds) => [
      ...nds,
      {
        id,
        type: "default",
        position: { x: 120 + nds.length * 16, y: nds.length * 120 },
        data: {
          label: `Step ${nextIndex}`,
          description: "",
          status: "draft",
          code_reference: "",
          notes: [],
        },
      },
    ]);
    setSelection({ type: "node", id });
    queueAutosave();
  }, [nodes.length, queueAutosave]);

  const handleDeleteSelection = useCallback(() => {
    if (!selection) {
      return;
    }
    if (selection.type === "node") {
      setNodes((nds) => nds.filter((node) => node.id != selection.id));
      setEdges((eds) => eds.filter((edge) => edge.source !== selection.id && edge.target !== selection.id));
    } else {
      setEdges((eds) => eds.filter((edge) => edge.id !== selection.id));
    }
    setSelection(null);
    queueAutosave();
  }, [queueAutosave, selection]);

  const handleExport = useCallback(() => {
    if (!activeFlowId) {
      return;
    }
    const payload: FlowDocument = {
      id: activeFlowId,
      title: flowMeta.title || activeFlowId,
      description: flowMeta.description,
      source: flowContext.source,
      generated_at: flowContext.generated_at,
      updated_at: flowContext.updated_at,
      metadata: flowContext.metadata,
      nodes,
      edges,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${activeFlowId}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }, [activeFlowId, edges, flowContext.generated_at, flowContext.metadata, flowContext.source, flowContext.updated_at, flowMeta.description, flowMeta.title, nodes]);

  const handleImport = useCallback(
    async (evt: ChangeEvent<HTMLInputElement>) => {
      const file = evt.target.files?.[0];
      if (!file) {
        return;
      }
      try {
        const raw = await file.text();
        const parsed = JSON.parse(raw) as FlowDocument;
        hydrateFlow(parsed);
        setDirty(true);
        queueAutosave();
      } catch (err) {
        setSaveError(err instanceof Error ? err.message : "Unable to import flow JSON");
        setSaveState("error");
      } finally {
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
      }
    },
    [hydrateFlow, queueAutosave],
  );

  const handleFlowMetaChange = useCallback(
    (field: "title" | "description", value: string) => {
      setFlowMeta((meta) => ({ ...meta, [field]: value }));
      queueAutosave();
    },
    [queueAutosave],
  );

  return (
    <div className="flow-editor-shell">
      <aside className="sidebar">
        <header>
          <p className="eyebrow">Flow Library</p>
          <h1>Flow Editor</h1>
          <p className="muted">
            Edit parsed flows from handovers, drag new paths, and annotate the nodes with references back to the code.
          </p>
        </header>
        {listError ? (
          <div className="error-card">
            <p>{listError}</p>
            <p className="small">Start the DevPanel backend and ensure ENABLE_DEVPANEL=true.</p>
          </div>
        ) : (
          <ul className="flow-list">
            {flows.map((flow) => (
              <li key={flow.id}>
                <button
                  className={clsx("flow-link", { active: flow.id === activeFlowId })}
                  onClick={() => setActiveFlowId(flow.id)}
                >
                  <span>{flow.title}</span>
                  <small>{flow.updated_at ? new Date(flow.updated_at).toLocaleString() : "—"}</small>
                </button>
              </li>
            ))}
          </ul>
        )}
        <div className="palette">
          <div className="palette-row">
            <span>Canvas</span>
            <div className="pill">{dirty ? "Unsaved changes" : "All changes saved"}</div>
          </div>
          <button onClick={handleAddNode}>Add Step</button>
          <button disabled={!selection} onClick={handleDeleteSelection}>
            Delete Selected
          </button>
          <button onClick={() => void saveCurrentFlow()}>Save Now</button>
          <button onClick={() => loadFlow(activeFlowId)} disabled={!activeFlowId || loading}>
            Reload from Seed
          </button>
          <button onClick={handleExport} disabled={!activeFlowId}>
            Export JSON
          </button>
          <button onClick={() => fileInputRef.current?.click()} disabled={!activeFlowId}>
            Import JSON
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/json"
            className="hidden-input"
            onChange={handleImport}
          />
        </div>
      </aside>

      <main className="canvas-area">
        <div className="toolbar">
          <div>
            <p className="eyebrow">Active Flow</p>
            <div className="title-edit">
              <input
                type="text"
                value={flowMeta.title}
                placeholder="Flow title"
                onChange={(evt) => handleFlowMetaChange("title", evt.target.value)}
              />
            </div>
          </div>
          <div className="status-group">
            <div className={clsx("status-pill", saveState)}>
              {saveState === "saving" && "Saving…"}
              {saveState === "idle" && (dirty ? "Queued for autosave" : "Saved")}
              {saveState === "error" && "Autosave failed"}
            </div>
            {flowContext.updated_at && (
              <span className="timestamp">Updated {new Date(flowContext.updated_at).toLocaleTimeString()}</span>
            )}
          </div>
        </div>
        <textarea
          className="flow-description"
          placeholder="Describe what this flow covers…"
          value={flowMeta.description}
          onChange={(evt) => handleFlowMetaChange("description", evt.target.value)}
        />
        <section className="canvas-wrapper">
          <ReactFlow
            style={{ width: "100%", height: "100%" }}
            nodes={nodes}
            edges={edges}
            fitView
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onSelectionChange={({ nodes: selectedNodes, edges: selectedEdges }) => {
              if (selectedNodes.length) {
                setSelection({ type: "node", id: selectedNodes[0].id });
              } else if (selectedEdges.length) {
                setSelection({ type: "edge", id: selectedEdges[0].id });
              } else {
                setSelection(null);
              }
            }}
          >
            <MiniMap pannable zoomable />
            <Controls position="top-right" />
            <Background gap={18} />
          </ReactFlow>
        </section>
        {flowContext.source && (
          <div className="source-note">
            Seeded from <code>{flowContext.source}</code>
          </div>
        )}
        {saveError && <div className="error-card">{saveError}</div>}
      </main>

      <aside className="inspector">
        <section className="inspector-section">
          <p className="eyebrow">Inspector</p>
          {!selection && <p className="muted">Select a node or edge to edit metadata.</p>}
          {selectedNode && (
            <div className="inspector-card">
              <h3>{selectedNode.data?.label ?? selectedNode.id}</h3>
              <label>
                Label
                <input
                  type="text"
                  value={selectedNode.data?.label ?? ""}
                  onChange={(evt) => updateNodeData(selectedNode.id, { label: evt.target.value })}
                />
              </label>
              <label>
                Status
                <select
                  value={selectedNode.data?.status ?? "draft"}
                  onChange={(evt) => updateNodeData(selectedNode.id, { status: evt.target.value })}
                >
                  {STATUS_OPTIONS.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Code Reference
                <input
                  type="text"
                  value={selectedNode.data?.code_reference ?? ""}
                  placeholder="file.py#L42"
                  onChange={(evt) => updateNodeData(selectedNode.id, { code_reference: evt.target.value })}
                />
              </label>
              <label>
                Description
                <textarea
                  value={selectedNode.data?.description ?? ""}
                  onChange={(evt) => updateNodeData(selectedNode.id, { description: evt.target.value })}
                />
              </label>
              {selectedNode.data?.notes && selectedNode.data.notes.length > 0 && (
                <div className="notes">
                  <p className="eyebrow">Imported Notes</p>
                  <ul>
                    {selectedNode.data.notes.map((note, idx) => (
                      <li key={`${selectedNode.id}-note-${idx}`}>{note}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
          {selectedEdge && (
            <div className="inspector-card">
              <h3>Connection {selectedEdge.id}</h3>
              <label>
                Label
                <input
                  type="text"
                  value={selectedEdge.label ?? ""}
                  onChange={(evt) => updateEdge(selectedEdge.id, { label: evt.target.value })}
                />
              </label>
              <label>
                Notes
                <textarea
                  value={(selectedEdge.data as { description?: string } | undefined)?.description ?? ""}
                  onChange={(evt) =>
                    updateEdge(selectedEdge.id, {
                      data: { ...(selectedEdge.data || {}), description: evt.target.value },
                    })
                  }
                />
              </label>
            </div>
          )}
        </section>

        <section className="inspector-section">
          <p className="eyebrow">Status Palette</p>
          <div className="status-grid">
            {STATUS_OPTIONS.map((status) => (
              <button
                key={status}
                className="status-chip"
                onClick={() => selectedNode && updateNodeData(selectedNode.id, { status })}
                disabled={!selectedNode}
              >
                {status}
              </button>
            ))}
          </div>
        </section>
      </aside>
    </div>
  );
}

export default App;
