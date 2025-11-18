--
-- PostgreSQL database dump
--

-- Dumped from database version 17.5
-- Dumped by pg_dump version 17.5

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agent_interactions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agent_interactions (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    project_id character varying(36) NOT NULL,
    sub_agent_name character varying(100) NOT NULL,
    interaction_type character varying(20) NOT NULL,
    mission text NOT NULL,
    start_time timestamp with time zone DEFAULT now(),
    end_time timestamp with time zone,
    duration_seconds integer,
    tokens_used integer,
    result text,
    error_message text,
    created_at timestamp with time zone DEFAULT now(),
    meta_data json,
    CONSTRAINT ck_interaction_type CHECK (((interaction_type)::text = ANY ((ARRAY['SPAWN'::character varying, 'COMPLETE'::character varying, 'ERROR'::character varying])::text[])))
);


ALTER TABLE public.agent_interactions OWNER TO postgres;

--
-- Name: agent_templates; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.agent_templates (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    product_id character varying(36),
    name character varying(100) NOT NULL,
    category character varying(50) DEFAULT 'role'::character varying NOT NULL,
    role character varying(50),
    project_type character varying(50),
    system_instructions text NOT NULL,
    user_instructions text,
    template_content text NOT NULL,
    variables json,
    behavioral_rules json,
    success_criteria json,
    tool character varying(50) NOT NULL,
    cli_tool character varying(20) NOT NULL,
    background_color character varying(7),
    model character varying(20),
    tools character varying(50),
    usage_count integer,
    last_used_at timestamp with time zone,
    avg_generation_ms double precision,
    description text,
    version character varying(20),
    is_active boolean,
    is_default boolean,
    tags json,
    meta_data json,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone,
    created_by character varying(100)
);


ALTER TABLE public.agent_templates OWNER TO postgres;

--
-- Name: COLUMN agent_templates.system_instructions; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.agent_templates.system_instructions IS 'Protected MCP coordination instructions (non-editable by users)';


--
-- Name: COLUMN agent_templates.user_instructions; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.agent_templates.user_instructions IS 'User-customizable role-specific guidance (editable)';


--
-- Name: COLUMN agent_templates.template_content; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.agent_templates.template_content IS 'DEPRECATED (v3.1): Use system_instructions + user_instructions. Kept for backward compatibility.';


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: api_keys; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.api_keys (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    user_id character varying(36) NOT NULL,
    name character varying(255) NOT NULL,
    key_hash character varying(255) NOT NULL,
    key_prefix character varying(16) NOT NULL,
    permissions jsonb NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_used timestamp with time zone,
    revoked_at timestamp with time zone,
    CONSTRAINT ck_apikey_revoked_consistency CHECK ((((is_active = true) AND (revoked_at IS NULL)) OR (is_active = false)))
);


ALTER TABLE public.api_keys OWNER TO postgres;

--
-- Name: api_metrics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.api_metrics (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    date timestamp with time zone NOT NULL,
    total_api_calls integer,
    total_mcp_calls integer
);


ALTER TABLE public.api_metrics OWNER TO postgres;

--
-- Name: configurations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.configurations (
    id character varying(36) NOT NULL,
    tenant_key character varying(36),
    project_id character varying(36),
    key character varying(255) NOT NULL,
    value json NOT NULL,
    category character varying(100),
    description text,
    is_secret boolean,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone
);


ALTER TABLE public.configurations OWNER TO postgres;

--
-- Name: context_index; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.context_index (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    project_id character varying(36) NOT NULL,
    index_type character varying(50) NOT NULL,
    document_name character varying(255) NOT NULL,
    section_name character varying(255),
    chunk_numbers json,
    summary text,
    token_count integer,
    keywords json,
    full_path text,
    content_hash character varying(32),
    version integer,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone
);


ALTER TABLE public.context_index OWNER TO postgres;

--
-- Name: discovery_config; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.discovery_config (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    project_id character varying(36) NOT NULL,
    path_key character varying(50) NOT NULL,
    path_value text NOT NULL,
    priority integer,
    enabled boolean,
    settings json,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone
);


ALTER TABLE public.discovery_config OWNER TO postgres;

--
-- Name: download_tokens; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.download_tokens (
    id integer NOT NULL,
    token character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    download_type character varying(50) NOT NULL,
    meta_data jsonb NOT NULL,
    is_used boolean NOT NULL,
    downloaded_at timestamp with time zone,
    staging_status character varying(20) NOT NULL,
    staging_error text,
    download_count integer NOT NULL,
    last_downloaded_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    CONSTRAINT ck_download_token_staging_status CHECK (((staging_status)::text = ANY ((ARRAY['pending'::character varying, 'ready'::character varying, 'failed'::character varying])::text[]))),
    CONSTRAINT ck_download_token_type CHECK (((download_type)::text = ANY ((ARRAY['slash_commands'::character varying, 'agent_templates'::character varying])::text[])))
);


ALTER TABLE public.download_tokens OWNER TO postgres;

--
-- Name: COLUMN download_tokens.token; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.download_tokens.token IS 'UUID v4 token used in download URL';


--
-- Name: COLUMN download_tokens.tenant_key; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.download_tokens.tenant_key IS 'Tenant key for multi-tenant isolation';


--
-- Name: COLUMN download_tokens.download_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.download_tokens.download_type IS 'Type of download: ''slash_commands'', ''agent_templates''';


--
-- Name: COLUMN download_tokens.meta_data; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.download_tokens.meta_data IS 'Additional metadata (filename, file_count, file_size, etc.)';


--
-- Name: COLUMN download_tokens.is_used; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.download_tokens.is_used IS 'Deprecated: legacy one-time download flag (not enforced)';


--
-- Name: COLUMN download_tokens.downloaded_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.download_tokens.downloaded_at IS 'Deprecated: legacy single-use timestamp (not enforced)';


--
-- Name: COLUMN download_tokens.staging_status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.download_tokens.staging_status IS 'Staging lifecycle status: pending|ready|failed';


--
-- Name: COLUMN download_tokens.staging_error; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.download_tokens.staging_error IS 'Staging error details when status=failed';


--
-- Name: COLUMN download_tokens.download_count; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.download_tokens.download_count IS 'Number of successful downloads for this token';


--
-- Name: COLUMN download_tokens.last_downloaded_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.download_tokens.last_downloaded_at IS 'Timestamp of most recent successful download';


--
-- Name: COLUMN download_tokens.expires_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.download_tokens.expires_at IS 'Token expiry timestamp (15 minutes after creation)';


--
-- Name: download_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.download_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.download_tokens_id_seq OWNER TO postgres;

--
-- Name: download_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.download_tokens_id_seq OWNED BY public.download_tokens.id;


--
-- Name: git_commits; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.git_commits (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    product_id character varying(36) NOT NULL,
    project_id character varying(36),
    commit_hash character varying(40) NOT NULL,
    commit_message text NOT NULL,
    author_name character varying(100) NOT NULL,
    author_email character varying(255) NOT NULL,
    branch_name character varying(100) NOT NULL,
    files_changed json,
    insertions integer,
    deletions integer,
    triggered_by character varying(50),
    commit_type character varying(50),
    push_status character varying(20),
    push_error text,
    webhook_triggered boolean,
    webhook_response json,
    committed_at timestamp with time zone NOT NULL,
    pushed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    meta_data json,
    CONSTRAINT ck_git_commit_push_status CHECK (((push_status)::text = ANY ((ARRAY['pending'::character varying, 'pushed'::character varying, 'failed'::character varying])::text[])))
);


ALTER TABLE public.git_commits OWNER TO postgres;

--
-- Name: git_configs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.git_configs (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    product_id character varying(36) NOT NULL,
    repo_url character varying(500) NOT NULL,
    branch character varying(100),
    remote_name character varying(50),
    auth_method character varying(20) NOT NULL,
    username character varying(100),
    password_encrypted text,
    ssh_key_path character varying(500),
    ssh_key_encrypted text,
    auto_commit boolean,
    auto_push boolean,
    commit_message_template text,
    webhook_url character varying(500),
    webhook_secret character varying(255),
    webhook_events json,
    ignore_patterns json,
    git_config_options json,
    is_active boolean,
    last_commit_hash character varying(40),
    last_push_at timestamp with time zone,
    last_error text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone,
    verified_at timestamp with time zone,
    meta_data json,
    CONSTRAINT ck_git_config_auth_method CHECK (((auth_method)::text = ANY ((ARRAY['https'::character varying, 'ssh'::character varying, 'token'::character varying])::text[])))
);


ALTER TABLE public.git_configs OWNER TO postgres;

--
-- Name: jobs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.jobs (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    job_type character varying(100) NOT NULL,
    status character varying(50),
    tasks json,
    scope_boundary text,
    vision_alignment text,
    created_at timestamp with time zone DEFAULT now(),
    completed_at timestamp with time zone,
    meta_data json
);


ALTER TABLE public.jobs OWNER TO postgres;

--
-- Name: large_document_index; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.large_document_index (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    project_id character varying(36) NOT NULL,
    document_path text NOT NULL,
    document_type character varying(50),
    total_size integer,
    total_tokens integer,
    chunk_count integer,
    meta_data json,
    indexed_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.large_document_index OWNER TO postgres;

--
-- Name: mcp_agent_jobs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.mcp_agent_jobs (
    id integer NOT NULL,
    tenant_key character varying(36) NOT NULL,
    project_id character varying(36),
    job_id character varying(36) NOT NULL,
    agent_type character varying(100) NOT NULL,
    mission text NOT NULL,
    status character varying(50) NOT NULL,
    failure_reason character varying(50),
    spawned_by character varying(36),
    context_chunks json,
    messages jsonb,
    acknowledged boolean,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    progress integer NOT NULL,
    block_reason text,
    current_task text,
    estimated_completion timestamp with time zone,
    tool_type character varying(20) NOT NULL,
    agent_name character varying(255),
    instance_number integer NOT NULL,
    handover_to character varying(36),
    handover_summary jsonb,
    handover_context_refs json,
    succession_reason character varying(100),
    context_used integer NOT NULL,
    context_budget integer NOT NULL,
    job_metadata jsonb NOT NULL,
    last_health_check timestamp with time zone,
    health_status character varying(20) NOT NULL,
    health_failure_count integer NOT NULL,
    last_progress_at timestamp with time zone,
    last_message_check_at timestamp with time zone,
    decommissioned_at timestamp with time zone,
    CONSTRAINT ck_mcp_agent_job_context_usage CHECK (((context_used >= 0) AND (context_used <= context_budget))),
    CONSTRAINT ck_mcp_agent_job_failure_reason CHECK (((failure_reason IS NULL) OR ((failure_reason)::text = ANY ((ARRAY['error'::character varying, 'timeout'::character varying, 'system_error'::character varying])::text[])))),
    CONSTRAINT ck_mcp_agent_job_health_failure_count CHECK ((health_failure_count >= 0)),
    CONSTRAINT ck_mcp_agent_job_health_status CHECK (((health_status)::text = ANY ((ARRAY['unknown'::character varying, 'healthy'::character varying, 'warning'::character varying, 'critical'::character varying, 'timeout'::character varying])::text[]))),
    CONSTRAINT ck_mcp_agent_job_instance_positive CHECK ((instance_number >= 1)),
    CONSTRAINT ck_mcp_agent_job_progress_range CHECK (((progress >= 0) AND (progress <= 100))),
    CONSTRAINT ck_mcp_agent_job_status CHECK (((status)::text = ANY ((ARRAY['waiting'::character varying, 'working'::character varying, 'blocked'::character varying, 'complete'::character varying, 'failed'::character varying, 'cancelled'::character varying, 'decommissioned'::character varying])::text[]))),
    CONSTRAINT ck_mcp_agent_job_succession_reason CHECK (((succession_reason IS NULL) OR ((succession_reason)::text = ANY ((ARRAY['context_limit'::character varying, 'manual'::character varying, 'phase_transition'::character varying])::text[])))),
    CONSTRAINT ck_mcp_agent_job_tool_type CHECK (((tool_type)::text = ANY ((ARRAY['claude-code'::character varying, 'codex'::character varying, 'gemini'::character varying, 'universal'::character varying])::text[])))
);


ALTER TABLE public.mcp_agent_jobs OWNER TO postgres;

--
-- Name: COLUMN mcp_agent_jobs.project_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.project_id IS 'Project ID this job belongs to (Handover 0062)';


--
-- Name: COLUMN mcp_agent_jobs.agent_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.agent_type IS 'Agent type: orchestrator, analyzer, implementer, tester, etc.';


--
-- Name: COLUMN mcp_agent_jobs.mission; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.mission IS 'Agent mission/instructions';


--
-- Name: COLUMN mcp_agent_jobs.failure_reason; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.failure_reason IS 'Reason for failure: error, timeout, system_error (Handover 0113)';


--
-- Name: COLUMN mcp_agent_jobs.spawned_by; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.spawned_by IS 'Agent ID that spawned this job';


--
-- Name: COLUMN mcp_agent_jobs.context_chunks; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.context_chunks IS 'Array of chunk_ids from mcp_context_index for context loading';


--
-- Name: COLUMN mcp_agent_jobs.messages; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.messages IS 'Array of message objects for agent communication';


--
-- Name: COLUMN mcp_agent_jobs.progress; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.progress IS 'Job completion progress (0-100%)';


--
-- Name: COLUMN mcp_agent_jobs.block_reason; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.block_reason IS 'Explanation of why job is blocked (NULL if not blocked)';


--
-- Name: COLUMN mcp_agent_jobs.current_task; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.current_task IS 'Description of current task being executed';


--
-- Name: COLUMN mcp_agent_jobs.estimated_completion; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.estimated_completion IS 'Estimated completion timestamp';


--
-- Name: COLUMN mcp_agent_jobs.tool_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.tool_type IS 'AI coding tool assigned to this agent job (claude-code, codex, gemini, universal)';


--
-- Name: COLUMN mcp_agent_jobs.agent_name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.agent_name IS 'Human-readable agent display name (e.g., Backend Agent, Database Agent)';


--
-- Name: COLUMN mcp_agent_jobs.instance_number; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.instance_number IS 'Sequential instance number for orchestrator succession (1, 2, 3, ...)';


--
-- Name: COLUMN mcp_agent_jobs.handover_to; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.handover_to IS 'UUID of successor orchestrator job (NULL if no handover)';


--
-- Name: COLUMN mcp_agent_jobs.handover_summary; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.handover_summary IS 'Compressed state transfer for successor orchestrator';


--
-- Name: COLUMN mcp_agent_jobs.handover_context_refs; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.handover_context_refs IS 'Array of context chunk IDs referenced in handover summary';


--
-- Name: COLUMN mcp_agent_jobs.succession_reason; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.succession_reason IS 'Reason for succession: ''context_limit'', ''manual'', ''phase_transition''';


--
-- Name: COLUMN mcp_agent_jobs.context_used; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.context_used IS 'Current context window usage in tokens';


--
-- Name: COLUMN mcp_agent_jobs.context_budget; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.context_budget IS 'Maximum context window budget in tokens';


--
-- Name: COLUMN mcp_agent_jobs.job_metadata; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.job_metadata IS 'JSONB metadata for thin client architecture (Handover 0088). Stores field_priorities, user_id, tool, etc.';


--
-- Name: COLUMN mcp_agent_jobs.last_health_check; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.last_health_check IS 'Timestamp of last health check scan';


--
-- Name: COLUMN mcp_agent_jobs.health_status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.health_status IS 'Health state: unknown, healthy, warning, critical, timeout';


--
-- Name: COLUMN mcp_agent_jobs.health_failure_count; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.health_failure_count IS 'Consecutive health check failures';


--
-- Name: COLUMN mcp_agent_jobs.last_progress_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.last_progress_at IS 'Timestamp of last progress update from agent (Handover 0107)';


--
-- Name: COLUMN mcp_agent_jobs.last_message_check_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.last_message_check_at IS 'Timestamp of last message queue check (Handover 0107)';


--
-- Name: COLUMN mcp_agent_jobs.decommissioned_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_agent_jobs.decommissioned_at IS 'Timestamp when agent job was decommissioned (Handover 0113)';


--
-- Name: mcp_agent_jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.mcp_agent_jobs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mcp_agent_jobs_id_seq OWNER TO postgres;

--
-- Name: mcp_agent_jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.mcp_agent_jobs_id_seq OWNED BY public.mcp_agent_jobs.id;


--
-- Name: mcp_context_index; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.mcp_context_index (
    id integer NOT NULL,
    tenant_key character varying(36) NOT NULL,
    chunk_id character varying(36) NOT NULL,
    product_id character varying(36),
    vision_document_id character varying(36),
    content text NOT NULL,
    summary text,
    keywords json,
    token_count integer,
    chunk_order integer,
    created_at timestamp with time zone DEFAULT now(),
    searchable_vector tsvector
);


ALTER TABLE public.mcp_context_index OWNER TO postgres;

--
-- Name: COLUMN mcp_context_index.vision_document_id; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_context_index.vision_document_id IS 'Link to specific vision document (NULL for legacy product-level chunks)';


--
-- Name: COLUMN mcp_context_index.summary; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_context_index.summary IS 'Optional LLM-generated summary (NULL for Phase 1 non-LLM chunking)';


--
-- Name: COLUMN mcp_context_index.keywords; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_context_index.keywords IS 'Array of keyword strings extracted via regex or LLM';


--
-- Name: COLUMN mcp_context_index.chunk_order; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_context_index.chunk_order IS 'Sequential chunk number for maintaining document order';


--
-- Name: COLUMN mcp_context_index.searchable_vector; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_context_index.searchable_vector IS 'Full-text search vector for fast keyword lookup';


--
-- Name: mcp_context_index_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.mcp_context_index_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mcp_context_index_id_seq OWNER TO postgres;

--
-- Name: mcp_context_index_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.mcp_context_index_id_seq OWNED BY public.mcp_context_index.id;


--
-- Name: mcp_context_summary; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.mcp_context_summary (
    id integer NOT NULL,
    tenant_key character varying(36) NOT NULL,
    context_id character varying(36) NOT NULL,
    product_id character varying(36),
    full_content text NOT NULL,
    condensed_mission text NOT NULL,
    full_token_count integer,
    condensed_token_count integer,
    reduction_percent double precision,
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.mcp_context_summary OWNER TO postgres;

--
-- Name: COLUMN mcp_context_summary.full_content; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_context_summary.full_content IS 'Original full context before condensation';


--
-- Name: COLUMN mcp_context_summary.condensed_mission; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_context_summary.condensed_mission IS 'Orchestrator-generated condensed mission';


--
-- Name: COLUMN mcp_context_summary.reduction_percent; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_context_summary.reduction_percent IS 'Context prioritization percentage achieved';


--
-- Name: mcp_context_summary_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.mcp_context_summary_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mcp_context_summary_id_seq OWNER TO postgres;

--
-- Name: mcp_context_summary_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.mcp_context_summary_id_seq OWNED BY public.mcp_context_summary.id;


--
-- Name: mcp_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.mcp_sessions (
    id character varying(36) NOT NULL,
    session_id character varying(36) NOT NULL,
    api_key_id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    project_id character varying(36),
    session_data jsonb NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_accessed timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone
);


ALTER TABLE public.mcp_sessions OWNER TO postgres;

--
-- Name: COLUMN mcp_sessions.session_data; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.mcp_sessions.session_data IS 'MCP protocol state: client_info, capabilities, tool_call_history';


--
-- Name: messages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.messages (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    project_id character varying(36) NOT NULL,
    to_agents json,
    message_type character varying(50),
    subject character varying(255),
    content text NOT NULL,
    priority character varying(20),
    status character varying(50),
    acknowledged_by json,
    completed_by json,
    created_at timestamp with time zone DEFAULT now(),
    acknowledged_at timestamp with time zone,
    completed_at timestamp with time zone,
    meta_data json,
    processing_started_at timestamp with time zone,
    retry_count integer,
    max_retries integer,
    backoff_seconds integer,
    circuit_breaker_status character varying(20)
);


ALTER TABLE public.messages OWNER TO postgres;

--
-- Name: optimization_metrics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.optimization_metrics (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    operation_type character varying(50) NOT NULL,
    params_size integer NOT NULL,
    result_size integer NOT NULL,
    optimized boolean NOT NULL,
    tokens_saved integer NOT NULL,
    meta_data json,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_optimization_metric_operation_type CHECK (((operation_type)::text = ANY ((ARRAY['file_read'::character varying, 'symbol_search'::character varying, 'symbol_replace'::character varying, 'pattern_search'::character varying, 'directory_list'::character varying])::text[]))),
    CONSTRAINT ck_optimization_metric_params_size CHECK ((params_size >= 0)),
    CONSTRAINT ck_optimization_metric_result_size CHECK ((result_size >= 0)),
    CONSTRAINT ck_optimization_metric_tokens_saved CHECK ((tokens_saved >= 0))
);


ALTER TABLE public.optimization_metrics OWNER TO postgres;

--
-- Name: optimization_rules; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.optimization_rules (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    operation_type character varying(50) NOT NULL,
    max_answer_chars integer NOT NULL,
    prefer_symbolic boolean NOT NULL,
    guidance text NOT NULL,
    context_filter character varying(100),
    is_active boolean NOT NULL,
    priority integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone,
    CONSTRAINT ck_optimization_rule_max_chars CHECK ((max_answer_chars > 0)),
    CONSTRAINT ck_optimization_rule_operation_type CHECK (((operation_type)::text = ANY ((ARRAY['file_read'::character varying, 'symbol_search'::character varying, 'symbol_replace'::character varying, 'pattern_search'::character varying, 'directory_list'::character varying])::text[]))),
    CONSTRAINT ck_optimization_rule_priority CHECK ((priority >= 0))
);


ALTER TABLE public.optimization_rules OWNER TO postgres;

--
-- Name: products; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.products (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    project_path character varying(500),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone,
    deleted_at timestamp with time zone,
    meta_data json,
    is_active boolean NOT NULL,
    config_data jsonb
);


ALTER TABLE public.products OWNER TO postgres;

--
-- Name: COLUMN products.project_path; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.products.project_path IS 'File system path to product folder (required for agent export)';


--
-- Name: COLUMN products.deleted_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.products.deleted_at IS 'Timestamp when product was soft deleted (NULL for active products)';


--
-- Name: COLUMN products.is_active; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.products.is_active IS 'Active product for token estimation and mission planning (one per tenant)';


--
-- Name: COLUMN products.config_data; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.products.config_data IS 'Rich project configuration: architecture, tech_stack, features, etc.';


--
-- Name: projects; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.projects (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    product_id character varying(36),
    name character varying(255) NOT NULL,
    alias character varying(6) NOT NULL,
    description text NOT NULL,
    mission text NOT NULL,
    status character varying(50),
    staging_status character varying(50),
    context_budget integer,
    context_used integer,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone,
    completed_at timestamp with time zone,
    activated_at timestamp with time zone,
    paused_at timestamp with time zone,
    deleted_at timestamp with time zone,
    meta_data json,
    orchestrator_summary text,
    closeout_prompt text,
    closeout_executed_at timestamp with time zone,
    closeout_checklist jsonb DEFAULT '[]'::jsonb NOT NULL
);


ALTER TABLE public.projects OWNER TO postgres;

--
-- Name: COLUMN projects.alias; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.projects.alias IS '6-character alphanumeric project identifier (e.g., A1B2C3)';


--
-- Name: COLUMN projects.staging_status; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.projects.staging_status IS 'Staging workflow status: null, staging, staged, cancelled, launching, active';


--
-- Name: COLUMN projects.activated_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.projects.activated_at IS 'First activation timestamp (only set once on first activation)';


--
-- Name: COLUMN projects.paused_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.projects.paused_at IS 'Timestamp when project was last paused/deactivated';


--
-- Name: COLUMN projects.deleted_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.projects.deleted_at IS 'Timestamp when project was soft deleted (NULL for active projects)';


--
-- Name: COLUMN projects.orchestrator_summary; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.projects.orchestrator_summary IS 'AI-generated final summary of project outcomes and deliverables';


--
-- Name: COLUMN projects.closeout_prompt; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.projects.closeout_prompt IS 'Prompt template used by orchestrator for closeout generation';


--
-- Name: COLUMN projects.closeout_executed_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.projects.closeout_executed_at IS 'Timestamp when closeout workflow was executed';


--
-- Name: COLUMN projects.closeout_checklist; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.projects.closeout_checklist IS 'Structured checklist of closeout tasks (JSONB array)';


--
-- Name: sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.sessions (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    project_id character varying(36) NOT NULL,
    session_number integer NOT NULL,
    title character varying(255) NOT NULL,
    objectives text,
    outcomes text,
    decisions json,
    blockers json,
    next_steps json,
    started_at timestamp with time zone DEFAULT now(),
    ended_at timestamp with time zone,
    duration_minutes integer,
    meta_data json
);


ALTER TABLE public.sessions OWNER TO postgres;

--
-- Name: settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.settings (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    category character varying(50) NOT NULL,
    settings_data jsonb NOT NULL,
    updated_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now()
);


ALTER TABLE public.settings OWNER TO postgres;

--
-- Name: setup_state; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.setup_state (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    database_initialized boolean NOT NULL,
    database_initialized_at timestamp with time zone,
    setup_version character varying(20),
    database_version character varying(20),
    python_version character varying(20),
    node_version character varying(20),
    first_admin_created boolean NOT NULL,
    first_admin_created_at timestamp with time zone,
    features_configured jsonb NOT NULL,
    tools_enabled jsonb NOT NULL,
    config_snapshot jsonb,
    validation_passed boolean NOT NULL,
    validation_failures jsonb NOT NULL,
    validation_warnings jsonb NOT NULL,
    last_validation_at timestamp with time zone,
    installer_version character varying(20),
    install_mode character varying(20),
    install_path text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone,
    meta_data jsonb,
    CONSTRAINT ck_database_initialized_at_required CHECK (((database_initialized = false) OR ((database_initialized = true) AND (database_initialized_at IS NOT NULL)))),
    CONSTRAINT ck_database_version_format CHECK (((database_version IS NULL) OR ((database_version)::text ~ '^[0-9]+(\.([0-9]+|[0-9]+\.[0-9]+))?$'::text))),
    CONSTRAINT ck_first_admin_created_at_required CHECK (((first_admin_created = false) OR ((first_admin_created = true) AND (first_admin_created_at IS NOT NULL)))),
    CONSTRAINT ck_install_mode_values CHECK (((install_mode IS NULL) OR ((install_mode)::text = ANY ((ARRAY['localhost'::character varying, 'server'::character varying, 'lan'::character varying, 'wan'::character varying])::text[])))),
    CONSTRAINT ck_setup_version_format CHECK (((setup_version IS NULL) OR ((setup_version)::text ~ '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9\.\-]+)?$'::text)))
);


ALTER TABLE public.setup_state OWNER TO postgres;

--
-- Name: COLUMN setup_state.first_admin_created; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.setup_state.first_admin_created IS 'True after first admin account created - prevents duplicate admin creation attacks';


--
-- Name: COLUMN setup_state.first_admin_created_at; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.setup_state.first_admin_created_at IS 'Timestamp when first admin account was created';


--
-- Name: COLUMN setup_state.features_configured; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.setup_state.features_configured IS 'Nested dict of configured features: {database: true, api: {enabled: true, port: 7272}}';


--
-- Name: COLUMN setup_state.tools_enabled; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.setup_state.tools_enabled IS 'Array of enabled MCP tool names';


--
-- Name: COLUMN setup_state.config_snapshot; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.setup_state.config_snapshot IS 'Snapshot of config.yaml at setup completion';


--
-- Name: COLUMN setup_state.validation_failures; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.setup_state.validation_failures IS 'Array of validation failure messages';


--
-- Name: COLUMN setup_state.validation_warnings; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.setup_state.validation_warnings IS 'Array of validation warning messages';


--
-- Name: COLUMN setup_state.install_mode; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.setup_state.install_mode IS 'Installation mode: localhost, server, lan, wan';


--
-- Name: COLUMN setup_state.install_path; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.setup_state.install_path IS 'Installation directory path';


--
-- Name: tasks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tasks (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    product_id character varying(36),
    project_id character varying(36),
    parent_task_id character varying(36),
    created_by_user_id character varying(36),
    converted_to_project_id character varying(36),
    agent_job_id character varying(36),
    title character varying(255) NOT NULL,
    description text,
    category character varying(100),
    status character varying(50),
    priority character varying(20),
    estimated_effort double precision,
    actual_effort double precision,
    created_at timestamp with time zone DEFAULT now(),
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    due_date timestamp with time zone,
    meta_data json
);


ALTER TABLE public.tasks OWNER TO postgres;

--
-- Name: template_archives; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.template_archives (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    template_id character varying(36) NOT NULL,
    product_id character varying(36),
    name character varying(100) NOT NULL,
    category character varying(50) NOT NULL,
    role character varying(50),
    system_instructions text,
    user_instructions text,
    template_content text NOT NULL,
    variables json,
    behavioral_rules json,
    success_criteria json,
    version character varying(20) NOT NULL,
    archive_reason character varying(255),
    archive_type character varying(20),
    archived_by character varying(100),
    archived_at timestamp with time zone DEFAULT now(),
    usage_count_at_archive integer,
    avg_generation_ms_at_archive double precision,
    is_restorable boolean,
    restored_at timestamp with time zone,
    restored_by character varying(100),
    meta_data json
);


ALTER TABLE public.template_archives OWNER TO postgres;

--
-- Name: template_augmentations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.template_augmentations (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    template_id character varying(36) NOT NULL,
    name character varying(100) NOT NULL,
    augmentation_type character varying(50) NOT NULL,
    target_section character varying(100),
    content text NOT NULL,
    conditions json,
    priority integer,
    is_active boolean,
    usage_count integer,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone
);


ALTER TABLE public.template_augmentations OWNER TO postgres;

--
-- Name: template_usage_stats; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.template_usage_stats (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    template_id character varying(36) NOT NULL,
    project_id character varying(36),
    used_at timestamp with time zone DEFAULT now(),
    generation_ms integer,
    variables_used json,
    augmentations_applied json,
    agent_completed boolean,
    agent_success_rate double precision,
    tokens_used integer
);


ALTER TABLE public.template_usage_stats OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    username character varying(64) NOT NULL,
    email character varying(255),
    password_hash character varying(255),
    recovery_pin_hash character varying(255),
    failed_pin_attempts integer NOT NULL,
    pin_lockout_until timestamp with time zone,
    must_change_password boolean NOT NULL,
    must_set_pin boolean NOT NULL,
    is_system_user boolean NOT NULL,
    full_name character varying(255),
    role character varying(32) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_login timestamp with time zone,
    field_priority_config jsonb,
    CONSTRAINT ck_user_pin_attempts_positive CHECK ((failed_pin_attempts >= 0)),
    CONSTRAINT ck_user_role CHECK (((role)::text = ANY ((ARRAY['admin'::character varying, 'developer'::character varying, 'viewer'::character varying])::text[])))
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: COLUMN users.recovery_pin_hash; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.recovery_pin_hash IS 'Bcrypt hash of 4-digit recovery PIN for password reset';


--
-- Name: COLUMN users.failed_pin_attempts; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.failed_pin_attempts IS 'Number of failed PIN verification attempts (rate limiting)';


--
-- Name: COLUMN users.pin_lockout_until; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.pin_lockout_until IS 'Timestamp when PIN lockout expires (15 minutes after 5 failed attempts)';


--
-- Name: COLUMN users.must_change_password; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.must_change_password IS 'Force user to change password on next login (new users, admin reset)';


--
-- Name: COLUMN users.must_set_pin; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.must_set_pin IS 'Force user to set recovery PIN on next login (new users)';


--
-- Name: COLUMN users.field_priority_config; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.users.field_priority_config IS 'User-customizable field priority for agent mission generation';


--
-- Name: vision_documents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vision_documents (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    product_id character varying(36) NOT NULL,
    document_name character varying(255) NOT NULL,
    document_type character varying(50) NOT NULL,
    vision_path character varying(500),
    vision_document text,
    storage_type character varying(20) NOT NULL,
    chunked boolean NOT NULL,
    chunk_count integer NOT NULL,
    total_tokens integer,
    file_size bigint,
    version character varying(50) NOT NULL,
    content_hash character varying(64),
    is_active boolean NOT NULL,
    display_order integer NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone,
    meta_data json,
    CONSTRAINT ck_vision_doc_chunk_count CHECK ((chunk_count >= 0)),
    CONSTRAINT ck_vision_doc_chunked_consistency CHECK ((((chunked = false) AND (chunk_count = 0)) OR ((chunked = true) AND (chunk_count > 0)))),
    CONSTRAINT ck_vision_doc_document_type CHECK (((document_type)::text = ANY ((ARRAY['vision'::character varying, 'architecture'::character varying, 'features'::character varying, 'setup'::character varying, 'api'::character varying, 'testing'::character varying, 'deployment'::character varying, 'custom'::character varying])::text[]))),
    CONSTRAINT ck_vision_doc_storage_consistency CHECK (((((storage_type)::text = 'file'::text) AND (vision_path IS NOT NULL)) OR (((storage_type)::text = 'inline'::text) AND (vision_document IS NOT NULL)) OR (((storage_type)::text = 'hybrid'::text) AND (vision_path IS NOT NULL) AND (vision_document IS NOT NULL)))),
    CONSTRAINT ck_vision_doc_storage_type CHECK (((storage_type)::text = ANY ((ARRAY['file'::character varying, 'inline'::character varying, 'hybrid'::character varying])::text[])))
);


ALTER TABLE public.vision_documents OWNER TO postgres;

--
-- Name: COLUMN vision_documents.document_name; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.vision_documents.document_name IS 'User-friendly document name (e.g., ''Product Architecture'', ''API Design'')';


--
-- Name: COLUMN vision_documents.document_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.vision_documents.document_type IS 'Document category: vision, architecture, features, setup, api, testing, deployment, custom';


--
-- Name: COLUMN vision_documents.vision_path; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.vision_documents.vision_path IS 'File path to vision document (file-based or hybrid storage)';


--
-- Name: COLUMN vision_documents.vision_document; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.vision_documents.vision_document IS 'Inline vision text (inline or hybrid storage)';


--
-- Name: COLUMN vision_documents.storage_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.vision_documents.storage_type IS 'Storage mode: ''file'', ''inline'', or ''hybrid''';


--
-- Name: COLUMN vision_documents.chunked; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.vision_documents.chunked IS 'Has document been chunked into mcp_context_index for RAG';


--
-- Name: COLUMN vision_documents.chunk_count; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.vision_documents.chunk_count IS 'Number of chunks created for this document';


--
-- Name: COLUMN vision_documents.total_tokens; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.vision_documents.total_tokens IS 'Estimated total tokens in document';


--
-- Name: COLUMN vision_documents.file_size; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.vision_documents.file_size IS 'Original file size in bytes (NULL for inline content without file)';


--
-- Name: COLUMN vision_documents.version; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.vision_documents.version IS 'Document version using semantic versioning';


--
-- Name: COLUMN vision_documents.content_hash; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.vision_documents.content_hash IS 'SHA-256 hash of document content for change detection';


--
-- Name: COLUMN vision_documents.is_active; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.vision_documents.is_active IS 'Active documents are used for context; inactive are archived';


--
-- Name: COLUMN vision_documents.display_order; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.vision_documents.display_order IS 'Display order in UI (lower numbers first)';


--
-- Name: COLUMN vision_documents.meta_data; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.vision_documents.meta_data IS 'Additional metadata: author, tags, source_url, etc.';


--
-- Name: visions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.visions (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    project_id character varying(36) NOT NULL,
    document_name character varying(255) NOT NULL,
    chunk_number integer,
    total_chunks integer,
    content text NOT NULL,
    tokens integer,
    version character varying(50),
    char_start integer,
    char_end integer,
    boundary_type character varying(20),
    keywords json,
    headers json,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone,
    meta_data json
);


ALTER TABLE public.visions OWNER TO postgres;

--
-- Name: download_tokens id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.download_tokens ALTER COLUMN id SET DEFAULT nextval('public.download_tokens_id_seq'::regclass);


--
-- Name: mcp_agent_jobs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mcp_agent_jobs ALTER COLUMN id SET DEFAULT nextval('public.mcp_agent_jobs_id_seq'::regclass);


--
-- Name: mcp_context_index id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mcp_context_index ALTER COLUMN id SET DEFAULT nextval('public.mcp_context_index_id_seq'::regclass);


--
-- Name: mcp_context_summary id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mcp_context_summary ALTER COLUMN id SET DEFAULT nextval('public.mcp_context_summary_id_seq'::regclass);


--
-- Name: agent_interactions agent_interactions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_interactions
    ADD CONSTRAINT agent_interactions_pkey PRIMARY KEY (id);


--
-- Name: agent_templates agent_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_templates
    ADD CONSTRAINT agent_templates_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: api_keys api_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_pkey PRIMARY KEY (id);


--
-- Name: api_metrics api_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.api_metrics
    ADD CONSTRAINT api_metrics_pkey PRIMARY KEY (id);


--
-- Name: configurations configurations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.configurations
    ADD CONSTRAINT configurations_pkey PRIMARY KEY (id);


--
-- Name: context_index context_index_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.context_index
    ADD CONSTRAINT context_index_pkey PRIMARY KEY (id);


--
-- Name: discovery_config discovery_config_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discovery_config
    ADD CONSTRAINT discovery_config_pkey PRIMARY KEY (id);


--
-- Name: download_tokens download_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.download_tokens
    ADD CONSTRAINT download_tokens_pkey PRIMARY KEY (id);


--
-- Name: git_commits git_commits_commit_hash_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.git_commits
    ADD CONSTRAINT git_commits_commit_hash_key UNIQUE (commit_hash);


--
-- Name: git_commits git_commits_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.git_commits
    ADD CONSTRAINT git_commits_pkey PRIMARY KEY (id);


--
-- Name: git_configs git_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.git_configs
    ADD CONSTRAINT git_configs_pkey PRIMARY KEY (id);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- Name: large_document_index large_document_index_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.large_document_index
    ADD CONSTRAINT large_document_index_pkey PRIMARY KEY (id);


--
-- Name: mcp_agent_jobs mcp_agent_jobs_job_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mcp_agent_jobs
    ADD CONSTRAINT mcp_agent_jobs_job_id_key UNIQUE (job_id);


--
-- Name: mcp_agent_jobs mcp_agent_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mcp_agent_jobs
    ADD CONSTRAINT mcp_agent_jobs_pkey PRIMARY KEY (id);


--
-- Name: mcp_context_index mcp_context_index_chunk_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mcp_context_index
    ADD CONSTRAINT mcp_context_index_chunk_id_key UNIQUE (chunk_id);


--
-- Name: mcp_context_index mcp_context_index_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mcp_context_index
    ADD CONSTRAINT mcp_context_index_pkey PRIMARY KEY (id);


--
-- Name: mcp_context_summary mcp_context_summary_context_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mcp_context_summary
    ADD CONSTRAINT mcp_context_summary_context_id_key UNIQUE (context_id);


--
-- Name: mcp_context_summary mcp_context_summary_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mcp_context_summary
    ADD CONSTRAINT mcp_context_summary_pkey PRIMARY KEY (id);


--
-- Name: mcp_sessions mcp_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mcp_sessions
    ADD CONSTRAINT mcp_sessions_pkey PRIMARY KEY (id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- Name: optimization_metrics optimization_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.optimization_metrics
    ADD CONSTRAINT optimization_metrics_pkey PRIMARY KEY (id);


--
-- Name: optimization_rules optimization_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.optimization_rules
    ADD CONSTRAINT optimization_rules_pkey PRIMARY KEY (id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);


--
-- Name: settings settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.settings
    ADD CONSTRAINT settings_pkey PRIMARY KEY (id);


--
-- Name: setup_state setup_state_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.setup_state
    ADD CONSTRAINT setup_state_pkey PRIMARY KEY (id);


--
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


--
-- Name: template_archives template_archives_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.template_archives
    ADD CONSTRAINT template_archives_pkey PRIMARY KEY (id);


--
-- Name: template_augmentations template_augmentations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.template_augmentations
    ADD CONSTRAINT template_augmentations_pkey PRIMARY KEY (id);


--
-- Name: template_usage_stats template_usage_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.template_usage_stats
    ADD CONSTRAINT template_usage_stats_pkey PRIMARY KEY (id);


--
-- Name: configurations uq_config_tenant_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.configurations
    ADD CONSTRAINT uq_config_tenant_key UNIQUE (tenant_key, key);


--
-- Name: context_index uq_context_index; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.context_index
    ADD CONSTRAINT uq_context_index UNIQUE (project_id, document_name, section_name);


--
-- Name: discovery_config uq_discovery_path; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discovery_config
    ADD CONSTRAINT uq_discovery_path UNIQUE (project_id, path_key);


--
-- Name: git_configs uq_git_config_product; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.git_configs
    ADD CONSTRAINT uq_git_config_product UNIQUE (product_id);


--
-- Name: large_document_index uq_large_doc_path; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.large_document_index
    ADD CONSTRAINT uq_large_doc_path UNIQUE (project_id, document_path);


--
-- Name: sessions uq_session_project_number; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT uq_session_project_number UNIQUE (project_id, session_number);


--
-- Name: settings uq_settings_tenant_category; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.settings
    ADD CONSTRAINT uq_settings_tenant_category UNIQUE (tenant_key, category);


--
-- Name: agent_templates uq_template_product_name_version; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_templates
    ADD CONSTRAINT uq_template_product_name_version UNIQUE (product_id, name, version);


--
-- Name: visions uq_vision_chunk; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.visions
    ADD CONSTRAINT uq_vision_chunk UNIQUE (project_id, document_name, chunk_number);


--
-- Name: vision_documents uq_vision_doc_product_name; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vision_documents
    ADD CONSTRAINT uq_vision_doc_product_name UNIQUE (product_id, document_name);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: vision_documents vision_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vision_documents
    ADD CONSTRAINT vision_documents_pkey PRIMARY KEY (id);


--
-- Name: visions visions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.visions
    ADD CONSTRAINT visions_pkey PRIMARY KEY (id);


--
-- Name: idx_agent_jobs_handover; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agent_jobs_handover ON public.mcp_agent_jobs USING btree (handover_to);


--
-- Name: idx_agent_jobs_instance; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_agent_jobs_instance ON public.mcp_agent_jobs USING btree (project_id, agent_type, instance_number);


--
-- Name: idx_api_metrics_tenant_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_api_metrics_tenant_date ON public.api_metrics USING btree (tenant_key, date);


--
-- Name: idx_apikey_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_apikey_active ON public.api_keys USING btree (is_active);


--
-- Name: idx_apikey_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_apikey_hash ON public.api_keys USING btree (key_hash);


--
-- Name: idx_apikey_permissions_gin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_apikey_permissions_gin ON public.api_keys USING gin (permissions);


--
-- Name: idx_apikey_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_apikey_tenant ON public.api_keys USING btree (tenant_key);


--
-- Name: idx_apikey_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_apikey_user ON public.api_keys USING btree (user_id);


--
-- Name: idx_archive_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_archive_date ON public.template_archives USING btree (archived_at);


--
-- Name: idx_archive_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_archive_product ON public.template_archives USING btree (product_id);


--
-- Name: idx_archive_template; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_archive_template ON public.template_archives USING btree (template_id);


--
-- Name: idx_archive_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_archive_tenant ON public.template_archives USING btree (tenant_key);


--
-- Name: idx_archive_version; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_archive_version ON public.template_archives USING btree (version);


--
-- Name: idx_augment_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_augment_active ON public.template_augmentations USING btree (is_active);


--
-- Name: idx_augment_template; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_augment_template ON public.template_augmentations USING btree (template_id);


--
-- Name: idx_augment_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_augment_tenant ON public.template_augmentations USING btree (tenant_key);


--
-- Name: idx_config_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_config_category ON public.configurations USING btree (category);


--
-- Name: idx_config_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_config_tenant ON public.configurations USING btree (tenant_key);


--
-- Name: idx_context_doc; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_context_doc ON public.context_index USING btree (document_name);


--
-- Name: idx_context_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_context_tenant ON public.context_index USING btree (tenant_key);


--
-- Name: idx_context_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_context_type ON public.context_index USING btree (index_type);


--
-- Name: idx_discovery_project; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_discovery_project ON public.discovery_config USING btree (project_id);


--
-- Name: idx_discovery_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_discovery_tenant ON public.discovery_config USING btree (tenant_key);


--
-- Name: idx_download_token_expires; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_download_token_expires ON public.download_tokens USING btree (expires_at);


--
-- Name: idx_download_token_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_download_token_tenant ON public.download_tokens USING btree (tenant_key);


--
-- Name: idx_download_token_tenant_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_download_token_tenant_type ON public.download_tokens USING btree (tenant_key, download_type);


--
-- Name: idx_download_token_token; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_download_token_token ON public.download_tokens USING btree (token);


--
-- Name: idx_git_commit_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_git_commit_date ON public.git_commits USING btree (committed_at);


--
-- Name: idx_git_commit_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_git_commit_hash ON public.git_commits USING btree (commit_hash);


--
-- Name: idx_git_commit_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_git_commit_product ON public.git_commits USING btree (product_id);


--
-- Name: idx_git_commit_project; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_git_commit_project ON public.git_commits USING btree (project_id);


--
-- Name: idx_git_commit_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_git_commit_tenant ON public.git_commits USING btree (tenant_key);


--
-- Name: idx_git_commit_trigger; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_git_commit_trigger ON public.git_commits USING btree (triggered_by);


--
-- Name: idx_git_config_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_git_config_active ON public.git_configs USING btree (is_active);


--
-- Name: idx_git_config_auth; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_git_config_auth ON public.git_configs USING btree (auth_method);


--
-- Name: idx_git_config_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_git_config_product ON public.git_configs USING btree (product_id);


--
-- Name: idx_git_config_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_git_config_tenant ON public.git_configs USING btree (tenant_key);


--
-- Name: idx_interaction_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_interaction_created ON public.agent_interactions USING btree (created_at);


--
-- Name: idx_interaction_project; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_interaction_project ON public.agent_interactions USING btree (project_id);


--
-- Name: idx_interaction_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_interaction_tenant ON public.agent_interactions USING btree (tenant_key);


--
-- Name: idx_interaction_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_interaction_type ON public.agent_interactions USING btree (interaction_type);


--
-- Name: idx_job_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_job_status ON public.jobs USING btree (status);


--
-- Name: idx_job_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_job_tenant ON public.jobs USING btree (tenant_key);


--
-- Name: idx_large_doc_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_large_doc_tenant ON public.large_document_index USING btree (tenant_key);


--
-- Name: idx_mcp_agent_jobs_job_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mcp_agent_jobs_job_id ON public.mcp_agent_jobs USING btree (job_id);


--
-- Name: idx_mcp_agent_jobs_project; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mcp_agent_jobs_project ON public.mcp_agent_jobs USING btree (project_id);


--
-- Name: idx_mcp_agent_jobs_tenant_project; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mcp_agent_jobs_tenant_project ON public.mcp_agent_jobs USING btree (tenant_key, project_id);


--
-- Name: idx_mcp_agent_jobs_tenant_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mcp_agent_jobs_tenant_status ON public.mcp_agent_jobs USING btree (tenant_key, status);


--
-- Name: idx_mcp_agent_jobs_tenant_tool; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mcp_agent_jobs_tenant_tool ON public.mcp_agent_jobs USING btree (tenant_key, tool_type);


--
-- Name: idx_mcp_agent_jobs_tenant_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mcp_agent_jobs_tenant_type ON public.mcp_agent_jobs USING btree (tenant_key, agent_type);


--
-- Name: idx_mcp_context_chunk_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mcp_context_chunk_id ON public.mcp_context_index USING btree (chunk_id);


--
-- Name: idx_mcp_context_product_vision_doc; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mcp_context_product_vision_doc ON public.mcp_context_index USING btree (product_id, vision_document_id);


--
-- Name: idx_mcp_context_searchable; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mcp_context_searchable ON public.mcp_context_index USING gin (searchable_vector);


--
-- Name: idx_mcp_context_tenant_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mcp_context_tenant_product ON public.mcp_context_index USING btree (tenant_key, product_id);


--
-- Name: idx_mcp_context_vision_doc; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mcp_context_vision_doc ON public.mcp_context_index USING btree (vision_document_id);


--
-- Name: idx_mcp_session_api_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mcp_session_api_key ON public.mcp_sessions USING btree (api_key_id);


--
-- Name: idx_mcp_session_cleanup; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mcp_session_cleanup ON public.mcp_sessions USING btree (expires_at, last_accessed);


--
-- Name: idx_mcp_session_data_gin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mcp_session_data_gin ON public.mcp_sessions USING gin (session_data);


--
-- Name: idx_mcp_session_expires; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mcp_session_expires ON public.mcp_sessions USING btree (expires_at);


--
-- Name: idx_mcp_session_last_accessed; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mcp_session_last_accessed ON public.mcp_sessions USING btree (last_accessed);


--
-- Name: idx_mcp_session_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mcp_session_tenant ON public.mcp_sessions USING btree (tenant_key);


--
-- Name: idx_mcp_summary_context_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mcp_summary_context_id ON public.mcp_context_summary USING btree (context_id);


--
-- Name: idx_mcp_summary_tenant_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_mcp_summary_tenant_product ON public.mcp_context_summary USING btree (tenant_key, product_id);


--
-- Name: idx_message_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_message_created ON public.messages USING btree (created_at);


--
-- Name: idx_message_priority; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_message_priority ON public.messages USING btree (priority);


--
-- Name: idx_message_project; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_message_project ON public.messages USING btree (project_id);


--
-- Name: idx_message_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_message_status ON public.messages USING btree (status);


--
-- Name: idx_message_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_message_tenant ON public.messages USING btree (tenant_key);


--
-- Name: idx_optimization_metric_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_optimization_metric_date ON public.optimization_metrics USING btree (created_at);


--
-- Name: idx_optimization_metric_optimized; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_optimization_metric_optimized ON public.optimization_metrics USING btree (optimized);


--
-- Name: idx_optimization_metric_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_optimization_metric_tenant ON public.optimization_metrics USING btree (tenant_key);


--
-- Name: idx_optimization_metric_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_optimization_metric_type ON public.optimization_metrics USING btree (operation_type);


--
-- Name: idx_optimization_rule_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_optimization_rule_active ON public.optimization_rules USING btree (is_active);


--
-- Name: idx_optimization_rule_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_optimization_rule_tenant ON public.optimization_rules USING btree (tenant_key);


--
-- Name: idx_optimization_rule_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_optimization_rule_type ON public.optimization_rules USING btree (operation_type);


--
-- Name: idx_product_config_data_gin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_product_config_data_gin ON public.products USING gin (config_data);


--
-- Name: idx_product_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_product_name ON public.products USING btree (name);


--
-- Name: idx_product_single_active_per_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_product_single_active_per_tenant ON public.products USING btree (tenant_key) WHERE (is_active = true);


--
-- Name: idx_product_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_product_tenant ON public.products USING btree (tenant_key);


--
-- Name: idx_products_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_products_deleted_at ON public.products USING btree (deleted_at) WHERE (deleted_at IS NOT NULL);


--
-- Name: idx_project_single_active_per_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX idx_project_single_active_per_product ON public.projects USING btree (product_id) WHERE ((status)::text = 'active'::text);


--
-- Name: idx_project_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_project_status ON public.projects USING btree (status);


--
-- Name: idx_project_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_project_tenant ON public.projects USING btree (tenant_key);


--
-- Name: idx_projects_closeout_executed; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_projects_closeout_executed ON public.projects USING btree (closeout_executed_at) WHERE (closeout_executed_at IS NOT NULL);


--
-- Name: idx_projects_deleted_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_projects_deleted_at ON public.projects USING btree (deleted_at) WHERE (deleted_at IS NOT NULL);


--
-- Name: idx_session_project; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_session_project ON public.sessions USING btree (project_id);


--
-- Name: idx_session_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_session_tenant ON public.sessions USING btree (tenant_key);


--
-- Name: idx_settings_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_settings_category ON public.settings USING btree (category);


--
-- Name: idx_settings_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_settings_tenant ON public.settings USING btree (tenant_key);


--
-- Name: idx_setup_database_incomplete; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_setup_database_incomplete ON public.setup_state USING btree (tenant_key, database_initialized) WHERE (database_initialized = false);


--
-- Name: idx_setup_database_initialized; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_setup_database_initialized ON public.setup_state USING btree (database_initialized);


--
-- Name: idx_setup_features_gin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_setup_features_gin ON public.setup_state USING gin (features_configured);


--
-- Name: idx_setup_fresh_install; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_setup_fresh_install ON public.setup_state USING btree (tenant_key, first_admin_created) WHERE (first_admin_created = false);


--
-- Name: idx_setup_mode; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_setup_mode ON public.setup_state USING btree (install_mode);


--
-- Name: idx_setup_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_setup_tenant ON public.setup_state USING btree (tenant_key);


--
-- Name: idx_setup_tools_gin; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_setup_tools_gin ON public.setup_state USING gin (tools_enabled);


--
-- Name: idx_task_agent_job; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_agent_job ON public.tasks USING btree (agent_job_id);


--
-- Name: idx_task_converted_to_project; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_converted_to_project ON public.tasks USING btree (converted_to_project_id);


--
-- Name: idx_task_created_by_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_created_by_user ON public.tasks USING btree (created_by_user_id);


--
-- Name: idx_task_priority; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_priority ON public.tasks USING btree (priority);


--
-- Name: idx_task_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_product ON public.tasks USING btree (product_id);


--
-- Name: idx_task_project; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_project ON public.tasks USING btree (project_id);


--
-- Name: idx_task_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_status ON public.tasks USING btree (status);


--
-- Name: idx_task_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_tenant ON public.tasks USING btree (tenant_key);


--
-- Name: idx_task_tenant_agent_job; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_tenant_agent_job ON public.tasks USING btree (tenant_key, agent_job_id);


--
-- Name: idx_task_tenant_created_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_task_tenant_created_user ON public.tasks USING btree (tenant_key, created_by_user_id);


--
-- Name: idx_template_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_template_active ON public.agent_templates USING btree (is_active);


--
-- Name: idx_template_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_template_category ON public.agent_templates USING btree (category);


--
-- Name: idx_template_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_template_product ON public.agent_templates USING btree (product_id);


--
-- Name: idx_template_role; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_template_role ON public.agent_templates USING btree (role);


--
-- Name: idx_template_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_template_tenant ON public.agent_templates USING btree (tenant_key);


--
-- Name: idx_template_tool; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_template_tool ON public.agent_templates USING btree (tool);


--
-- Name: idx_usage_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_usage_date ON public.template_usage_stats USING btree (used_at);


--
-- Name: idx_usage_project; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_usage_project ON public.template_usage_stats USING btree (project_id);


--
-- Name: idx_usage_template; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_usage_template ON public.template_usage_stats USING btree (template_id);


--
-- Name: idx_usage_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_usage_tenant ON public.template_usage_stats USING btree (tenant_key);


--
-- Name: idx_user_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_active ON public.users USING btree (is_active);


--
-- Name: idx_user_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_email ON public.users USING btree (email);


--
-- Name: idx_user_pin_lockout; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_pin_lockout ON public.users USING btree (pin_lockout_until);


--
-- Name: idx_user_system; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_system ON public.users USING btree (is_system_user);


--
-- Name: idx_user_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_tenant ON public.users USING btree (tenant_key);


--
-- Name: idx_user_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_username ON public.users USING btree (username);


--
-- Name: idx_vision_doc_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_vision_doc_active ON public.vision_documents USING btree (is_active);


--
-- Name: idx_vision_doc_chunked; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_vision_doc_chunked ON public.vision_documents USING btree (chunked);


--
-- Name: idx_vision_doc_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_vision_doc_product ON public.vision_documents USING btree (product_id);


--
-- Name: idx_vision_doc_product_active; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_vision_doc_product_active ON public.vision_documents USING btree (product_id, is_active, display_order);


--
-- Name: idx_vision_doc_product_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_vision_doc_product_type ON public.vision_documents USING btree (product_id, document_type);


--
-- Name: idx_vision_doc_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_vision_doc_tenant ON public.vision_documents USING btree (tenant_key);


--
-- Name: idx_vision_doc_tenant_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_vision_doc_tenant_product ON public.vision_documents USING btree (tenant_key, product_id);


--
-- Name: idx_vision_doc_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_vision_doc_type ON public.vision_documents USING btree (document_type);


--
-- Name: idx_vision_document; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_vision_document ON public.visions USING btree (document_name);


--
-- Name: idx_vision_project; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_vision_project ON public.visions USING btree (project_id);


--
-- Name: idx_vision_tenant; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_vision_tenant ON public.visions USING btree (tenant_key);


--
-- Name: ix_agent_templates_tool; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_agent_templates_tool ON public.agent_templates USING btree (tool);


--
-- Name: ix_api_keys_key_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_api_keys_key_hash ON public.api_keys USING btree (key_hash);


--
-- Name: ix_api_keys_tenant_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_api_keys_tenant_key ON public.api_keys USING btree (tenant_key);


--
-- Name: ix_api_metrics_tenant_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_api_metrics_tenant_key ON public.api_metrics USING btree (tenant_key);


--
-- Name: ix_download_tokens_tenant_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_download_tokens_tenant_key ON public.download_tokens USING btree (tenant_key);


--
-- Name: ix_download_tokens_token; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_download_tokens_token ON public.download_tokens USING btree (token);


--
-- Name: ix_mcp_agent_jobs_project_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_mcp_agent_jobs_project_id ON public.mcp_agent_jobs USING btree (project_id);


--
-- Name: ix_mcp_agent_jobs_tenant_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_mcp_agent_jobs_tenant_key ON public.mcp_agent_jobs USING btree (tenant_key);


--
-- Name: ix_mcp_context_index_tenant_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_mcp_context_index_tenant_key ON public.mcp_context_index USING btree (tenant_key);


--
-- Name: ix_mcp_context_summary_tenant_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_mcp_context_summary_tenant_key ON public.mcp_context_summary USING btree (tenant_key);


--
-- Name: ix_mcp_sessions_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_mcp_sessions_session_id ON public.mcp_sessions USING btree (session_id);


--
-- Name: ix_mcp_sessions_tenant_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_mcp_sessions_tenant_key ON public.mcp_sessions USING btree (tenant_key);


--
-- Name: ix_optimization_metrics_tenant_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_optimization_metrics_tenant_key ON public.optimization_metrics USING btree (tenant_key);


--
-- Name: ix_optimization_rules_tenant_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_optimization_rules_tenant_key ON public.optimization_rules USING btree (tenant_key);


--
-- Name: ix_products_tenant_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_products_tenant_key ON public.products USING btree (tenant_key);


--
-- Name: ix_projects_alias; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_projects_alias ON public.projects USING btree (alias);


--
-- Name: ix_settings_tenant_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_settings_tenant_key ON public.settings USING btree (tenant_key);


--
-- Name: ix_setup_state_database_initialized; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_setup_state_database_initialized ON public.setup_state USING btree (database_initialized);


--
-- Name: ix_setup_state_first_admin_created; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_setup_state_first_admin_created ON public.setup_state USING btree (first_admin_created);


--
-- Name: ix_setup_state_tenant_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_setup_state_tenant_key ON public.setup_state USING btree (tenant_key);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_tenant_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_users_tenant_key ON public.users USING btree (tenant_key);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: ix_vision_documents_tenant_key; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_vision_documents_tenant_key ON public.vision_documents USING btree (tenant_key);


--
-- Name: agent_interactions agent_interactions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.agent_interactions
    ADD CONSTRAINT agent_interactions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: api_keys api_keys_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: configurations configurations_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.configurations
    ADD CONSTRAINT configurations_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: context_index context_index_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.context_index
    ADD CONSTRAINT context_index_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: discovery_config discovery_config_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.discovery_config
    ADD CONSTRAINT discovery_config_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: git_commits git_commits_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.git_commits
    ADD CONSTRAINT git_commits_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: large_document_index large_document_index_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.large_document_index
    ADD CONSTRAINT large_document_index_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: mcp_agent_jobs mcp_agent_jobs_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mcp_agent_jobs
    ADD CONSTRAINT mcp_agent_jobs_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: mcp_context_index mcp_context_index_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mcp_context_index
    ADD CONSTRAINT mcp_context_index_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: mcp_context_index mcp_context_index_vision_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mcp_context_index
    ADD CONSTRAINT mcp_context_index_vision_document_id_fkey FOREIGN KEY (vision_document_id) REFERENCES public.vision_documents(id) ON DELETE CASCADE;


--
-- Name: mcp_context_summary mcp_context_summary_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mcp_context_summary
    ADD CONSTRAINT mcp_context_summary_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: mcp_sessions mcp_sessions_api_key_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mcp_sessions
    ADD CONSTRAINT mcp_sessions_api_key_id_fkey FOREIGN KEY (api_key_id) REFERENCES public.api_keys(id) ON DELETE CASCADE;


--
-- Name: mcp_sessions mcp_sessions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mcp_sessions
    ADD CONSTRAINT mcp_sessions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE SET NULL;


--
-- Name: messages messages_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: projects projects_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: sessions sessions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: tasks tasks_agent_job_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_agent_job_id_fkey FOREIGN KEY (agent_job_id) REFERENCES public.mcp_agent_jobs(job_id);


--
-- Name: tasks tasks_converted_to_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_converted_to_project_id_fkey FOREIGN KEY (converted_to_project_id) REFERENCES public.projects(id);


--
-- Name: tasks tasks_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id);


--
-- Name: tasks tasks_parent_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_parent_task_id_fkey FOREIGN KEY (parent_task_id) REFERENCES public.tasks(id);


--
-- Name: tasks tasks_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: tasks tasks_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: template_archives template_archives_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.template_archives
    ADD CONSTRAINT template_archives_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.agent_templates(id);


--
-- Name: template_augmentations template_augmentations_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.template_augmentations
    ADD CONSTRAINT template_augmentations_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.agent_templates(id);


--
-- Name: template_usage_stats template_usage_stats_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.template_usage_stats
    ADD CONSTRAINT template_usage_stats_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: template_usage_stats template_usage_stats_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.template_usage_stats
    ADD CONSTRAINT template_usage_stats_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.agent_templates(id);


--
-- Name: vision_documents vision_documents_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vision_documents
    ADD CONSTRAINT vision_documents_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: visions visions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.visions
    ADD CONSTRAINT visions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- PostgreSQL database dump complete
--

