/**
 * Message System Types
 * Type definitions for message visualization and broadcast system
 */

export interface Message {
  id: string
  from: string // Sender (agent job_id, 'user', 'system', 'orchestrator')
  from_agent?: string // Alias for backend compatibility
  to_agents: string[] // Recipient list
  to_agent?: string // Single recipient (backend compatibility)
  content: string
  type: MessageType // 'direct' | 'broadcast' | 'system' | 'info' | 'error' | 'success'
  message_type?: MessageType // Alias for backend compatibility
  priority: MessagePriority
  status: MessageStatus
  created_at: string // ISO timestamp
  recipient_count?: number // For broadcasts
}

export type MessageType = 'direct' | 'broadcast' | 'system' | 'info' | 'error' | 'success'
export type MessagePriority = 'normal' | 'high' | 'urgent'
export type MessageStatus = 'pending' | 'delivered' | 'acknowledged' | 'completed' | 'failed'

export interface BroadcastRequest {
  project_id: string
  content: string
  priority: MessagePriority
  from_agent?: string
}

export interface BroadcastResponse {
  success: boolean
  message_id: string
  recipient_count: number
  recipients: string[]
  timestamp: string
}

export interface BroadcastTemplate {
  id: string
  name: string
  content: string
  priority: MessagePriority
}

export interface MessageFilter {
  agent_name?: string
  message_type?: MessageType
  status?: MessageStatus
  search?: string
}
