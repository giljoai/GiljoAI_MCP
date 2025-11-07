import type { Edge, Node } from "reactflow";

export interface FlowNodeData {
  label: string;
  description?: string;
  status?: string;
  code_reference?: string;
  notes?: string[];
}

export type FlowNode = Node<FlowNodeData>;

export interface FlowDocument {
  id: string;
  title?: string;
  description?: string;
  source?: string;
  generated_at?: string;
  updated_at?: string;
  nodes: FlowNode[];
  edges: Edge[];
  layout?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface FlowSummary {
  id: string;
  title: string;
  filename: string;
  updated_at?: string;
}

export type SaveState = "idle" | "saving" | "error";
