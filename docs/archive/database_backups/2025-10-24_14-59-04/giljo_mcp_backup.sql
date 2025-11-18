--
-- PostgreSQL database dump
--

-- Dumped from database version 17.5
-- Dumped by pg_dump version 17.5

-- Started on 2025-10-24 14:59:04

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
-- TOC entry 2 (class 3079 OID 130007)
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- TOC entry 5335 (class 0 OID 0)
-- Dependencies: 2
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 245 (class 1259 OID 130561)
-- Name: agent_interactions; Type: TABLE; Schema: public; Owner: giljo_user
--

CREATE TABLE public.agent_interactions (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    project_id character varying(36) NOT NULL,
    parent_agent_id character varying(36),
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


ALTER TABLE public.agent_interactions OWNER TO giljo_user;

--
-- TOC entry 219 (class 1259 OID 130103)
-- Name: agent_templates; Type: TABLE; Schema: public; Owner: giljo_user
--

CREATE TABLE public.agent_templates (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    product_id character varying(36),
    name character varying(100) NOT NULL,
    category character varying(50) NOT NULL,
    role character varying(50),
    project_type character varying(50),
    template_content text NOT NULL,
    variables json,
    behavioral_rules json,
    success_criteria json,
    preferred_tool character varying(50),
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


ALTER TABLE public.agent_templates OWNER TO giljo_user;

--
-- TOC entry 234 (class 1259 OID 130319)
-- Name: agents; Type: TABLE; Schema: public; Owner: giljo_user
--

CREATE TABLE public.agents (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    project_id character varying(36) NOT NULL,
    name character varying(100) NOT NULL,
    role character varying(50) NOT NULL,
    status character varying(50),
    mission text,
    context_used integer,
    last_active timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now(),
    decommissioned_at timestamp with time zone,
    meta_data json
);


ALTER TABLE public.agents OWNER TO giljo_user;

--
-- TOC entry 229 (class 1259 OID 130257)
-- Name: api_keys; Type: TABLE; Schema: public; Owner: giljo_user
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


ALTER TABLE public.api_keys OWNER TO giljo_user;

--
-- TOC entry 237 (class 1259 OID 130373)
-- Name: configurations; Type: TABLE; Schema: public; Owner: giljo_user
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


ALTER TABLE public.configurations OWNER TO giljo_user;

--
-- TOC entry 239 (class 1259 OID 130407)
-- Name: context_index; Type: TABLE; Schema: public; Owner: giljo_user
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


ALTER TABLE public.context_index OWNER TO giljo_user;

--
-- TOC entry 238 (class 1259 OID 130390)
-- Name: discovery_config; Type: TABLE; Schema: public; Owner: giljo_user
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


ALTER TABLE public.discovery_config OWNER TO giljo_user;

--
-- TOC entry 247 (class 1259 OID 130613)
-- Name: git_commits; Type: TABLE; Schema: public; Owner: giljo_user
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
    agent_id character varying(36),
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


ALTER TABLE public.git_commits OWNER TO giljo_user;

--
-- TOC entry 220 (class 1259 OID 130118)
-- Name: git_configs; Type: TABLE; Schema: public; Owner: giljo_user
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


ALTER TABLE public.git_configs OWNER TO giljo_user;

--
-- TOC entry 244 (class 1259 OID 130545)
-- Name: jobs; Type: TABLE; Schema: public; Owner: giljo_user
--

CREATE TABLE public.jobs (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    agent_id character varying(36) NOT NULL,
    job_type character varying(100) NOT NULL,
    status character varying(50),
    tasks json,
    scope_boundary text,
    vision_alignment text,
    created_at timestamp with time zone DEFAULT now(),
    completed_at timestamp with time zone,
    meta_data json
);


ALTER TABLE public.jobs OWNER TO giljo_user;

--
-- TOC entry 240 (class 1259 OID 130425)
-- Name: large_document_index; Type: TABLE; Schema: public; Owner: giljo_user
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


ALTER TABLE public.large_document_index OWNER TO giljo_user;

--
-- TOC entry 225 (class 1259 OID 130191)
-- Name: mcp_agent_jobs; Type: TABLE; Schema: public; Owner: giljo_user
--

CREATE TABLE public.mcp_agent_jobs (
    id integer NOT NULL,
    tenant_key character varying(36) NOT NULL,
    job_id character varying(36) NOT NULL,
    agent_type character varying(100) NOT NULL,
    mission text NOT NULL,
    status character varying(50) NOT NULL,
    spawned_by character varying(36),
    context_chunks json,
    messages jsonb,
    acknowledged boolean,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    CONSTRAINT ck_mcp_agent_job_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'active'::character varying, 'completed'::character varying, 'failed'::character varying])::text[])))
);


ALTER TABLE public.mcp_agent_jobs OWNER TO giljo_user;

--
-- TOC entry 5336 (class 0 OID 0)
-- Dependencies: 225
-- Name: COLUMN mcp_agent_jobs.agent_type; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.mcp_agent_jobs.agent_type IS 'Agent type: orchestrator, analyzer, implementer, tester, etc.';


--
-- TOC entry 5337 (class 0 OID 0)
-- Dependencies: 225
-- Name: COLUMN mcp_agent_jobs.mission; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.mcp_agent_jobs.mission IS 'Agent mission/instructions';


--
-- TOC entry 5338 (class 0 OID 0)
-- Dependencies: 225
-- Name: COLUMN mcp_agent_jobs.spawned_by; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.mcp_agent_jobs.spawned_by IS 'Agent ID that spawned this job';


--
-- TOC entry 5339 (class 0 OID 0)
-- Dependencies: 225
-- Name: COLUMN mcp_agent_jobs.context_chunks; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.mcp_agent_jobs.context_chunks IS 'Array of chunk_ids from mcp_context_index for context loading';


--
-- TOC entry 5340 (class 0 OID 0)
-- Dependencies: 225
-- Name: COLUMN mcp_agent_jobs.messages; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.mcp_agent_jobs.messages IS 'Array of message objects for agent communication';


--
-- TOC entry 224 (class 1259 OID 130190)
-- Name: mcp_agent_jobs_id_seq; Type: SEQUENCE; Schema: public; Owner: giljo_user
--

CREATE SEQUENCE public.mcp_agent_jobs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mcp_agent_jobs_id_seq OWNER TO giljo_user;

--
-- TOC entry 5341 (class 0 OID 0)
-- Dependencies: 224
-- Name: mcp_agent_jobs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: giljo_user
--

ALTER SEQUENCE public.mcp_agent_jobs_id_seq OWNED BY public.mcp_agent_jobs.id;


--
-- TOC entry 231 (class 1259 OID 130279)
-- Name: mcp_context_index; Type: TABLE; Schema: public; Owner: giljo_user
--

CREATE TABLE public.mcp_context_index (
    id integer NOT NULL,
    tenant_key character varying(36) NOT NULL,
    chunk_id character varying(36) NOT NULL,
    product_id character varying(36),
    content text NOT NULL,
    summary text,
    keywords json,
    token_count integer,
    chunk_order integer,
    created_at timestamp with time zone DEFAULT now(),
    searchable_vector tsvector
);


ALTER TABLE public.mcp_context_index OWNER TO giljo_user;

--
-- TOC entry 5342 (class 0 OID 0)
-- Dependencies: 231
-- Name: COLUMN mcp_context_index.summary; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.mcp_context_index.summary IS 'Optional LLM-generated summary (NULL for Phase 1 non-LLM chunking)';


--
-- TOC entry 5343 (class 0 OID 0)
-- Dependencies: 231
-- Name: COLUMN mcp_context_index.keywords; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.mcp_context_index.keywords IS 'Array of keyword strings extracted via regex or LLM';


--
-- TOC entry 5344 (class 0 OID 0)
-- Dependencies: 231
-- Name: COLUMN mcp_context_index.chunk_order; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.mcp_context_index.chunk_order IS 'Sequential chunk number for maintaining document order';


--
-- TOC entry 5345 (class 0 OID 0)
-- Dependencies: 231
-- Name: COLUMN mcp_context_index.searchable_vector; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.mcp_context_index.searchable_vector IS 'Full-text search vector for fast keyword lookup';


--
-- TOC entry 230 (class 1259 OID 130278)
-- Name: mcp_context_index_id_seq; Type: SEQUENCE; Schema: public; Owner: giljo_user
--

CREATE SEQUENCE public.mcp_context_index_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mcp_context_index_id_seq OWNER TO giljo_user;

--
-- TOC entry 5346 (class 0 OID 0)
-- Dependencies: 230
-- Name: mcp_context_index_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: giljo_user
--

ALTER SEQUENCE public.mcp_context_index_id_seq OWNED BY public.mcp_context_index.id;


--
-- TOC entry 233 (class 1259 OID 130300)
-- Name: mcp_context_summary; Type: TABLE; Schema: public; Owner: giljo_user
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


ALTER TABLE public.mcp_context_summary OWNER TO giljo_user;

--
-- TOC entry 5347 (class 0 OID 0)
-- Dependencies: 233
-- Name: COLUMN mcp_context_summary.full_content; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.mcp_context_summary.full_content IS 'Original full context before condensation';


--
-- TOC entry 5348 (class 0 OID 0)
-- Dependencies: 233
-- Name: COLUMN mcp_context_summary.condensed_mission; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.mcp_context_summary.condensed_mission IS 'Orchestrator-generated condensed mission';


--
-- TOC entry 5349 (class 0 OID 0)
-- Dependencies: 233
-- Name: COLUMN mcp_context_summary.reduction_percent; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.mcp_context_summary.reduction_percent IS 'Context prioritization percentage achieved';


--
-- TOC entry 232 (class 1259 OID 130299)
-- Name: mcp_context_summary_id_seq; Type: SEQUENCE; Schema: public; Owner: giljo_user
--

CREATE SEQUENCE public.mcp_context_summary_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mcp_context_summary_id_seq OWNER TO giljo_user;

--
-- TOC entry 5350 (class 0 OID 0)
-- Dependencies: 232
-- Name: mcp_context_summary_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: giljo_user
--

ALTER SEQUENCE public.mcp_context_summary_id_seq OWNED BY public.mcp_context_summary.id;


--
-- TOC entry 241 (class 1259 OID 130441)
-- Name: mcp_sessions; Type: TABLE; Schema: public; Owner: giljo_user
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


ALTER TABLE public.mcp_sessions OWNER TO giljo_user;

--
-- TOC entry 5351 (class 0 OID 0)
-- Dependencies: 241
-- Name: COLUMN mcp_sessions.session_data; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.mcp_sessions.session_data IS 'MCP protocol state: client_info, capabilities, tool_call_history';


--
-- TOC entry 242 (class 1259 OID 130468)
-- Name: messages; Type: TABLE; Schema: public; Owner: giljo_user
--

CREATE TABLE public.messages (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    project_id character varying(36) NOT NULL,
    from_agent_id character varying(36),
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


ALTER TABLE public.messages OWNER TO giljo_user;

--
-- TOC entry 248 (class 1259 OID 130640)
-- Name: optimization_metrics; Type: TABLE; Schema: public; Owner: giljo_user
--

CREATE TABLE public.optimization_metrics (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    agent_id character varying(36) NOT NULL,
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


ALTER TABLE public.optimization_metrics OWNER TO giljo_user;

--
-- TOC entry 223 (class 1259 OID 130175)
-- Name: optimization_rules; Type: TABLE; Schema: public; Owner: giljo_user
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


ALTER TABLE public.optimization_rules OWNER TO giljo_user;

--
-- TOC entry 218 (class 1259 OID 130090)
-- Name: products; Type: TABLE; Schema: public; Owner: giljo_user
--

CREATE TABLE public.products (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    vision_path character varying(500),
    vision_document text,
    vision_type character varying(20),
    chunked boolean,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone,
    meta_data json,
    config_data jsonb,
    CONSTRAINT ck_product_vision_type CHECK (((vision_type)::text = ANY ((ARRAY['file'::character varying, 'inline'::character varying, 'none'::character varying])::text[])))
);


ALTER TABLE public.products OWNER TO giljo_user;

--
-- TOC entry 5352 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN products.vision_path; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.products.vision_path IS 'File path to vision document (file-based workflow)';


--
-- TOC entry 5353 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN products.vision_document; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.products.vision_document IS 'Inline vision text (alternative to vision_path for agentic workflow)';


--
-- TOC entry 5354 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN products.vision_type; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.products.vision_type IS 'Vision source: ''file'', ''inline'', or ''none''';


--
-- TOC entry 5355 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN products.chunked; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.products.chunked IS 'Has vision been chunked into mcp_context_index for agentic RAG';


--
-- TOC entry 5356 (class 0 OID 0)
-- Dependencies: 218
-- Name: COLUMN products.config_data; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.products.config_data IS 'Rich project configuration: architecture, tech_stack, features, etc.';


--
-- TOC entry 226 (class 1259 OID 130207)
-- Name: projects; Type: TABLE; Schema: public; Owner: giljo_user
--

CREATE TABLE public.projects (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    product_id character varying(36),
    name character varying(255) NOT NULL,
    alias character varying(6) NOT NULL,
    mission text NOT NULL,
    status character varying(50),
    context_budget integer,
    context_used integer,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone,
    completed_at timestamp with time zone,
    meta_data json
);


ALTER TABLE public.projects OWNER TO giljo_user;

--
-- TOC entry 5357 (class 0 OID 0)
-- Dependencies: 226
-- Name: COLUMN projects.alias; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.projects.alias IS '6-character alphanumeric project identifier (e.g., A1B2C3)';


--
-- TOC entry 235 (class 1259 OID 130338)
-- Name: sessions; Type: TABLE; Schema: public; Owner: giljo_user
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


ALTER TABLE public.sessions OWNER TO giljo_user;

--
-- TOC entry 221 (class 1259 OID 130133)
-- Name: setup_state; Type: TABLE; Schema: public; Owner: giljo_user
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


ALTER TABLE public.setup_state OWNER TO giljo_user;

--
-- TOC entry 5358 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN setup_state.first_admin_created; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.setup_state.first_admin_created IS 'True after first admin account created - prevents duplicate admin creation attacks';


--
-- TOC entry 5359 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN setup_state.first_admin_created_at; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.setup_state.first_admin_created_at IS 'Timestamp when first admin account was created';


--
-- TOC entry 5360 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN setup_state.features_configured; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.setup_state.features_configured IS 'Nested dict of configured features: {database: true, api: {enabled: true, port: 7272}}';


--
-- TOC entry 5361 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN setup_state.tools_enabled; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.setup_state.tools_enabled IS 'Array of enabled MCP tool names';


--
-- TOC entry 5362 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN setup_state.config_snapshot; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.setup_state.config_snapshot IS 'Snapshot of config.yaml at setup completion';


--
-- TOC entry 5363 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN setup_state.validation_failures; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.setup_state.validation_failures IS 'Array of validation failure messages';


--
-- TOC entry 5364 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN setup_state.validation_warnings; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.setup_state.validation_warnings IS 'Array of validation warning messages';


--
-- TOC entry 5365 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN setup_state.install_mode; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.setup_state.install_mode IS 'Installation mode: localhost, server, lan, wan';


--
-- TOC entry 5366 (class 0 OID 0)
-- Dependencies: 221
-- Name: COLUMN setup_state.install_path; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.setup_state.install_path IS 'Installation directory path';


--
-- TOC entry 243 (class 1259 OID 130491)
-- Name: tasks; Type: TABLE; Schema: public; Owner: giljo_user
--

CREATE TABLE public.tasks (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    product_id character varying(36),
    project_id character varying(36) NOT NULL,
    assigned_agent_id character varying(36),
    parent_task_id character varying(36),
    created_by_user_id character varying(36),
    assigned_to_user_id character varying(36),
    converted_to_project_id character varying(36),
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


ALTER TABLE public.tasks OWNER TO giljo_user;

--
-- TOC entry 227 (class 1259 OID 130223)
-- Name: template_archives; Type: TABLE; Schema: public; Owner: giljo_user
--

CREATE TABLE public.template_archives (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    template_id character varying(36) NOT NULL,
    product_id character varying(36),
    name character varying(100) NOT NULL,
    category character varying(50) NOT NULL,
    role character varying(50),
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


ALTER TABLE public.template_archives OWNER TO giljo_user;

--
-- TOC entry 228 (class 1259 OID 130241)
-- Name: template_augmentations; Type: TABLE; Schema: public; Owner: giljo_user
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


ALTER TABLE public.template_augmentations OWNER TO giljo_user;

--
-- TOC entry 246 (class 1259 OID 130586)
-- Name: template_usage_stats; Type: TABLE; Schema: public; Owner: giljo_user
--

CREATE TABLE public.template_usage_stats (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    template_id character varying(36) NOT NULL,
    agent_id character varying(36),
    project_id character varying(36),
    used_at timestamp with time zone DEFAULT now(),
    generation_ms integer,
    variables_used json,
    augmentations_applied json,
    agent_completed boolean,
    agent_success_rate double precision,
    tokens_used integer
);


ALTER TABLE public.template_usage_stats OWNER TO giljo_user;

--
-- TOC entry 222 (class 1259 OID 130156)
-- Name: users; Type: TABLE; Schema: public; Owner: giljo_user
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
    CONSTRAINT ck_user_pin_attempts_positive CHECK ((failed_pin_attempts >= 0)),
    CONSTRAINT ck_user_role CHECK (((role)::text = ANY ((ARRAY['admin'::character varying, 'developer'::character varying, 'viewer'::character varying])::text[])))
);


ALTER TABLE public.users OWNER TO giljo_user;

--
-- TOC entry 5367 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN users.recovery_pin_hash; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.users.recovery_pin_hash IS 'Bcrypt hash of 4-digit recovery PIN for password reset';


--
-- TOC entry 5368 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN users.failed_pin_attempts; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.users.failed_pin_attempts IS 'Number of failed PIN verification attempts (rate limiting)';


--
-- TOC entry 5369 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN users.pin_lockout_until; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.users.pin_lockout_until IS 'Timestamp when PIN lockout expires (15 minutes after 5 failed attempts)';


--
-- TOC entry 5370 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN users.must_change_password; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.users.must_change_password IS 'Force user to change password on next login (new users, admin reset)';


--
-- TOC entry 5371 (class 0 OID 0)
-- Dependencies: 222
-- Name: COLUMN users.must_set_pin; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.users.must_set_pin IS 'Force user to set recovery PIN on next login (new users)';


--
-- TOC entry 236 (class 1259 OID 130355)
-- Name: visions; Type: TABLE; Schema: public; Owner: giljo_user
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


ALTER TABLE public.visions OWNER TO giljo_user;

--
-- TOC entry 4861 (class 2604 OID 130194)
-- Name: mcp_agent_jobs id; Type: DEFAULT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.mcp_agent_jobs ALTER COLUMN id SET DEFAULT nextval('public.mcp_agent_jobs_id_seq'::regclass);


--
-- TOC entry 4867 (class 2604 OID 130282)
-- Name: mcp_context_index id; Type: DEFAULT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.mcp_context_index ALTER COLUMN id SET DEFAULT nextval('public.mcp_context_index_id_seq'::regclass);


--
-- TOC entry 4869 (class 2604 OID 130303)
-- Name: mcp_context_summary id; Type: DEFAULT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.mcp_context_summary ALTER COLUMN id SET DEFAULT nextval('public.mcp_context_summary_id_seq'::regclass);


--
-- TOC entry 5325 (class 0 OID 130561)
-- Dependencies: 245
-- Data for Name: agent_interactions; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.agent_interactions (id, tenant_key, project_id, parent_agent_id, sub_agent_name, interaction_type, mission, start_time, end_time, duration_seconds, tokens_used, result, error_message, created_at, meta_data) FROM stdin;
\.


--
-- TOC entry 5299 (class 0 OID 130103)
-- Dependencies: 219
-- Data for Name: agent_templates; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.agent_templates (id, tenant_key, product_id, name, category, role, project_type, template_content, variables, behavioral_rules, success_criteria, preferred_tool, usage_count, last_used_at, avg_generation_ms, description, version, is_active, is_default, tags, meta_data, created_at, updated_at, created_by) FROM stdin;
\.


--
-- TOC entry 5314 (class 0 OID 130319)
-- Dependencies: 234
-- Data for Name: agents; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.agents (id, tenant_key, project_id, name, role, status, mission, context_used, last_active, created_at, decommissioned_at, meta_data) FROM stdin;
\.


--
-- TOC entry 5309 (class 0 OID 130257)
-- Dependencies: 229
-- Data for Name: api_keys; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.api_keys (id, tenant_key, user_id, name, key_hash, key_prefix, permissions, is_active, created_at, last_used, revoked_at) FROM stdin;
f8db8760-6558-428e-97f1-92b35cc152cf	tk_JOxU7dkkhHxRzPG3whDvMtkshYTTE1vi	f8a27d80-3903-40fe-bfcb-e09c6a8c4441	Claude Code prompt key	$2b$12$DJSKl.O0ZFohFzi482JSae6TCH4Mou69XJH.ucqePgTC3nDKQWo0e	gk_xKs76WQ9e...	["*"]	f	2025-10-23 17:47:52.845964-04	\N	2025-10-23 18:00:53.324599-04
c2e4bc5e-bd35-407a-98e8-7c403ddf8453	tk_JOxU7dkkhHxRzPG3whDvMtkshYTTE1vi	f8a27d80-3903-40fe-bfcb-e09c6a8c4441	Claude Code prompt key	$2b$12$48U/qos9UBek09i7HstHJe4uEQZ3BSc92wHNI81XDYQtneElTCuwW	gk_5FOHdFxys...	["*"]	f	2025-10-23 18:00:59.620938-04	\N	2025-10-23 18:03:21.47241-04
804f7048-c4a2-4520-a8c3-766097c7e442	tk_JOxU7dkkhHxRzPG3whDvMtkshYTTE1vi	f8a27d80-3903-40fe-bfcb-e09c6a8c4441	Claude Code prompt key	$2b$12$Q3pF8PEWxHq3Zs8BRH/9FuiII4UHJZC5PN9sGdlYauesmOj0DVVt.	gk_jfuVOY0Zp...	["*"]	f	2025-10-23 18:03:32.858717-04	\N	2025-10-23 18:06:28.138733-04
440ae77c-65aa-4313-96c6-b8f1c7c59be5	tk_JOxU7dkkhHxRzPG3whDvMtkshYTTE1vi	f8a27d80-3903-40fe-bfcb-e09c6a8c4441	Claude Code prompt key	$2b$12$MQtsYP.VABX90OaRa119E.JMzHdGiGDCbnAjhQ58MIqMBXYyavcae	gk_Tx7r1os5d...	["*"]	f	2025-10-23 18:06:34.16221-04	\N	2025-10-23 18:18:22.223667-04
b1b77e64-d655-49f3-bab5-5d57def299aa	tk_JOxU7dkkhHxRzPG3whDvMtkshYTTE1vi	f8a27d80-3903-40fe-bfcb-e09c6a8c4441	Claude Code prompt key	$2b$12$1K7vkw5wcNd9ux5GpBJ/9.rs.vWdEq73Sqo5trXHIp5wJQtwmdDvS	gk_hr9StpWSP...	["*"]	f	2025-10-23 18:23:14.410552-04	\N	2025-10-23 18:33:00.021245-04
3cfc63b0-dd3e-460d-b9c9-ab8de3a2d7fd	tk_JOxU7dkkhHxRzPG3whDvMtkshYTTE1vi	f8a27d80-3903-40fe-bfcb-e09c6a8c4441	Claude Code prompt key	$2b$12$tQGxUeaTybP6R60yBkD9OeM1QJPWtCC0CTVp1pKQG7NZB6tuzgEce	gk_PuhQkU7jS...	["*"]	f	2025-10-23 21:08:23.811259-04	\N	2025-10-23 21:09:08.179983-04
fcdc7ad4-5936-4815-89b9-b045d17c9b48	tk_JOxU7dkkhHxRzPG3whDvMtkshYTTE1vi	f8a27d80-3903-40fe-bfcb-e09c6a8c4441	Claude Code prompt key	$2b$12$2Pz9gws5uKpaZZXC5klRp.tQvgsvA9EtTwibe0HZmk6.kBLzMBhN2	gk_Ze0EFjl0V...	["*"]	f	2025-10-23 18:33:07.140023-04	2025-10-23 18:38:10.464937-04	2025-10-23 21:09:12.132049-04
a254db62-4d30-4f21-95f7-d331e759437a	tk_JOxU7dkkhHxRzPG3whDvMtkshYTTE1vi	f8a27d80-3903-40fe-bfcb-e09c6a8c4441	Claude Code prompt key	$2b$12$kQTtEO644odSKpge.RjSsuyUZJsI8ZEWmM2MbrPt0soBVryW6DZCi	gk_uWmLgPjVn...	["*"]	t	2025-10-23 21:14:32.280216-04	\N	\N
\.


--
-- TOC entry 5317 (class 0 OID 130373)
-- Dependencies: 237
-- Data for Name: configurations; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.configurations (id, tenant_key, project_id, key, value, category, description, is_secret, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5319 (class 0 OID 130407)
-- Dependencies: 239
-- Data for Name: context_index; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.context_index (id, tenant_key, project_id, index_type, document_name, section_name, chunk_numbers, summary, token_count, keywords, full_path, content_hash, version, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5318 (class 0 OID 130390)
-- Dependencies: 238
-- Data for Name: discovery_config; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.discovery_config (id, tenant_key, project_id, path_key, path_value, priority, enabled, settings, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5327 (class 0 OID 130613)
-- Dependencies: 247
-- Data for Name: git_commits; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.git_commits (id, tenant_key, product_id, project_id, commit_hash, commit_message, author_name, author_email, branch_name, files_changed, insertions, deletions, triggered_by, agent_id, commit_type, push_status, push_error, webhook_triggered, webhook_response, committed_at, pushed_at, created_at, meta_data) FROM stdin;
\.


--
-- TOC entry 5300 (class 0 OID 130118)
-- Dependencies: 220
-- Data for Name: git_configs; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.git_configs (id, tenant_key, product_id, repo_url, branch, remote_name, auth_method, username, password_encrypted, ssh_key_path, ssh_key_encrypted, auto_commit, auto_push, commit_message_template, webhook_url, webhook_secret, webhook_events, ignore_patterns, git_config_options, is_active, last_commit_hash, last_push_at, last_error, created_at, updated_at, verified_at, meta_data) FROM stdin;
\.


--
-- TOC entry 5324 (class 0 OID 130545)
-- Dependencies: 244
-- Data for Name: jobs; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.jobs (id, tenant_key, agent_id, job_type, status, tasks, scope_boundary, vision_alignment, created_at, completed_at, meta_data) FROM stdin;
\.


--
-- TOC entry 5320 (class 0 OID 130425)
-- Dependencies: 240
-- Data for Name: large_document_index; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.large_document_index (id, tenant_key, project_id, document_path, document_type, total_size, total_tokens, chunk_count, meta_data, indexed_at) FROM stdin;
\.


--
-- TOC entry 5305 (class 0 OID 130191)
-- Dependencies: 225
-- Data for Name: mcp_agent_jobs; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.mcp_agent_jobs (id, tenant_key, job_id, agent_type, mission, status, spawned_by, context_chunks, messages, acknowledged, started_at, completed_at, created_at) FROM stdin;
\.


--
-- TOC entry 5311 (class 0 OID 130279)
-- Dependencies: 231
-- Data for Name: mcp_context_index; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.mcp_context_index (id, tenant_key, chunk_id, product_id, content, summary, keywords, token_count, chunk_order, created_at, searchable_vector) FROM stdin;
\.


--
-- TOC entry 5313 (class 0 OID 130300)
-- Dependencies: 233
-- Data for Name: mcp_context_summary; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.mcp_context_summary (id, tenant_key, context_id, product_id, full_content, condensed_mission, full_token_count, condensed_token_count, reduction_percent, created_at) FROM stdin;
\.


--
-- TOC entry 5321 (class 0 OID 130441)
-- Dependencies: 241
-- Data for Name: mcp_sessions; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.mcp_sessions (id, session_id, api_key_id, tenant_key, project_id, session_data, created_at, last_accessed, expires_at) FROM stdin;
dfb70fae-246f-497a-9075-884b93ea7a86	121d78c1-c6ac-4299-899b-31943266cab5	fcdc7ad4-5936-4815-89b9-b045d17c9b48	tk_JOxU7dkkhHxRzPG3whDvMtkshYTTE1vi	\N	{"client_info": {}, "initialized": false, "capabilities": {}, "tool_call_history": []}	2025-10-23 18:38:09.783055-04	2025-10-23 18:38:10.467937-04	2025-10-24 18:38:10.467937-04
\.


--
-- TOC entry 5322 (class 0 OID 130468)
-- Dependencies: 242
-- Data for Name: messages; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.messages (id, tenant_key, project_id, from_agent_id, to_agents, message_type, subject, content, priority, status, acknowledged_by, completed_by, created_at, acknowledged_at, completed_at, meta_data, processing_started_at, retry_count, max_retries, backoff_seconds, circuit_breaker_status) FROM stdin;
\.


--
-- TOC entry 5328 (class 0 OID 130640)
-- Dependencies: 248
-- Data for Name: optimization_metrics; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.optimization_metrics (id, tenant_key, agent_id, operation_type, params_size, result_size, optimized, tokens_saved, meta_data, created_at) FROM stdin;
\.


--
-- TOC entry 5303 (class 0 OID 130175)
-- Dependencies: 223
-- Data for Name: optimization_rules; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.optimization_rules (id, tenant_key, operation_type, max_answer_chars, prefer_symbolic, guidance, context_filter, is_active, priority, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5298 (class 0 OID 130090)
-- Dependencies: 218
-- Data for Name: products; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.products (id, tenant_key, name, description, vision_path, vision_document, vision_type, chunked, created_at, updated_at, meta_data, config_data) FROM stdin;
734a2db0-68de-4098-8468-8bdf3aca13ca	tk_cyyOVf1HsbOCA8eFLEHoYUwiIIYhXjnd	TinyContacts	TinyContacts — Simple, test-friendly contacts web app\r\n\r\nA minimal, clean contacts app you can build in 3–4 small projects to exercise your MCP tool’s “project → sub-agents” workflow. It’s intentionally boring (on purpose): CRUD for contacts with photo upload, phone, email, and important dates. Nothing fancy, easy to verify, and perfect for sub-agent hand-offs.\r\n\r\n1) Product overview\r\n\r\nGoal: Let a user add and manage contacts with:\r\n\r\nContact photo (upload/replace)\r\n\r\nName\r\n\r\nEmail\r\n\r\nPhone number\r\n\r\nImportant dates (e.g., birthday, anniversary, custom label + date)\r\n\r\nKeep it simple:\r\n\r\nSingle user (no auth) to reduce scope (you can bolt on auth later).\r\n\r\nOne-page UI with a modal form. Client-side validation.\r\n\r\nBasic search/filter by name or email.\r\n\r\nNon-goals for v1:\r\n\r\nNo multi-user accounts / auth\r\n\r\nNo social integrations, no vCard import/export (optional later)\r\n\r\nNo complicated date rules or reminders (optional later)	products\\734a2db0-68de-4098-8468-8bdf3aca13ca\\vision\\TinyContactsProduct.md	\N	none	f	2025-10-23 22:38:08.613221-04	\N	{"vision_chunks": 1, "vision_filename": "TinyContactsProduct.md", "vision_size": 4818, "chunks_metadata": [{"chunk_number": 1, "char_start": 0, "char_end": 4758, "boundary_type": "complete", "keywords": ["Project", "Agent", "API", "UI", "MCP"], "headers": []}]}	{}
\.


--
-- TOC entry 5306 (class 0 OID 130207)
-- Dependencies: 226
-- Data for Name: projects; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.projects (id, tenant_key, product_id, name, alias, mission, status, context_budget, context_used, created_at, updated_at, completed_at, meta_data) FROM stdin;
0f36ef6f-b4ed-46c7-a168-68fd139f33a8	tk_JOxU7dkkhHxRzPG3whDvMtkshYTTE1vi	\N	Bootstrap & Groundwork	YJK2AW	Purpose: Create skeleton repos, run “hello world”, wire backend & frontend dev servers.\n\nScope & Tasks:\n\nInit repo structure.\n\nFastAPI up with /health returning {status: "ok"}.\n\nVite/React app with a blank page + fetch /health.\n\n.gitignore, README with run instructions.\n\nDeliverables:\n\nRunning uvicorn backend.app:app (or similar) and npm run dev.\n\nREADME: setup & run commands (Windows-friendly).\n\nAcceptance:\n\nGET /health → 200 OK.\n\nFrontend loads and shows backend health result.	active	150000	0	2025-10-23 22:53:01.503137-04	\N	\N	{}
\.


--
-- TOC entry 5315 (class 0 OID 130338)
-- Dependencies: 235
-- Data for Name: sessions; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.sessions (id, tenant_key, project_id, session_number, title, objectives, outcomes, decisions, blockers, next_steps, started_at, ended_at, duration_minutes, meta_data) FROM stdin;
\.


--
-- TOC entry 5301 (class 0 OID 130133)
-- Dependencies: 221
-- Data for Name: setup_state; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.setup_state (id, tenant_key, database_initialized, database_initialized_at, setup_version, database_version, python_version, node_version, first_admin_created, first_admin_created_at, features_configured, tools_enabled, config_snapshot, validation_passed, validation_failures, validation_warnings, last_validation_at, installer_version, install_mode, install_path, created_at, updated_at, meta_data) FROM stdin;
01800b83-1002-4438-8748-fed2b1099f46	tk_tz8AiQdLw51JiNHjGv05L3xrFvGG9UJK	t	2025-10-22 00:29:51.325317-04	3.0.0	\N	\N	\N	f	\N	{}	[]	\N	t	[]	[]	\N	\N	\N	\N	2025-10-22 00:29:51.325317-04	2025-10-22 00:29:51.325317-04	{}
8c4fc64a-a1a1-4434-92ea-9506068c7ac2	tk_JOxU7dkkhHxRzPG3whDvMtkshYTTE1vi	t	2025-10-22 00:31:24.355309-04	\N	\N	\N	\N	t	2025-10-22 00:31:24.355309-04	{}	[]	\N	t	[]	[]	\N	\N	\N	\N	2025-10-22 00:31:24.352241-04	\N	{}
\.


--
-- TOC entry 5323 (class 0 OID 130491)
-- Dependencies: 243
-- Data for Name: tasks; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.tasks (id, tenant_key, product_id, project_id, assigned_agent_id, parent_task_id, created_by_user_id, assigned_to_user_id, converted_to_project_id, title, description, category, status, priority, estimated_effort, actual_effort, created_at, started_at, completed_at, due_date, meta_data) FROM stdin;
\.


--
-- TOC entry 5307 (class 0 OID 130223)
-- Dependencies: 227
-- Data for Name: template_archives; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.template_archives (id, tenant_key, template_id, product_id, name, category, role, template_content, variables, behavioral_rules, success_criteria, version, archive_reason, archive_type, archived_by, archived_at, usage_count_at_archive, avg_generation_ms_at_archive, is_restorable, restored_at, restored_by, meta_data) FROM stdin;
\.


--
-- TOC entry 5308 (class 0 OID 130241)
-- Dependencies: 228
-- Data for Name: template_augmentations; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.template_augmentations (id, tenant_key, template_id, name, augmentation_type, target_section, content, conditions, priority, is_active, usage_count, created_at, updated_at) FROM stdin;
\.


--
-- TOC entry 5326 (class 0 OID 130586)
-- Dependencies: 246
-- Data for Name: template_usage_stats; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.template_usage_stats (id, tenant_key, template_id, agent_id, project_id, used_at, generation_ms, variables_used, augmentations_applied, agent_completed, agent_success_rate, tokens_used) FROM stdin;
\.


--
-- TOC entry 5302 (class 0 OID 130156)
-- Dependencies: 222
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.users (id, tenant_key, username, email, password_hash, recovery_pin_hash, failed_pin_attempts, pin_lockout_until, must_change_password, must_set_pin, is_system_user, full_name, role, is_active, created_at, last_login) FROM stdin;
f8a27d80-3903-40fe-bfcb-e09c6a8c4441	tk_JOxU7dkkhHxRzPG3whDvMtkshYTTE1vi	patrik	giljo72@gmail.com	$2b$12$L8hYBSuit1Wz5FEWvO/IfOQbpGJosGE/XbkYkUdAI.NBUDBd9zAz.	\N	0	\N	f	f	f	Patrik Pettersson	admin	t	2025-10-22 00:31:24.337556-04	2025-10-23 18:32:46.837525-04
\.


--
-- TOC entry 5316 (class 0 OID 130355)
-- Dependencies: 236
-- Data for Name: visions; Type: TABLE DATA; Schema: public; Owner: giljo_user
--

COPY public.visions (id, tenant_key, project_id, document_name, chunk_number, total_chunks, content, tokens, version, char_start, char_end, boundary_type, keywords, headers, created_at, updated_at, meta_data) FROM stdin;
\.


--
-- TOC entry 5372 (class 0 OID 0)
-- Dependencies: 224
-- Name: mcp_agent_jobs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: giljo_user
--

SELECT pg_catalog.setval('public.mcp_agent_jobs_id_seq', 1, false);


--
-- TOC entry 5373 (class 0 OID 0)
-- Dependencies: 230
-- Name: mcp_context_index_id_seq; Type: SEQUENCE SET; Schema: public; Owner: giljo_user
--

SELECT pg_catalog.setval('public.mcp_context_index_id_seq', 1, false);


--
-- TOC entry 5374 (class 0 OID 0)
-- Dependencies: 232
-- Name: mcp_context_summary_id_seq; Type: SEQUENCE SET; Schema: public; Owner: giljo_user
--

SELECT pg_catalog.setval('public.mcp_context_summary_id_seq', 1, false);


--
-- TOC entry 5090 (class 2606 OID 130570)
-- Name: agent_interactions agent_interactions_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.agent_interactions
    ADD CONSTRAINT agent_interactions_pkey PRIMARY KEY (id);


--
-- TOC entry 4916 (class 2606 OID 130110)
-- Name: agent_templates agent_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.agent_templates
    ADD CONSTRAINT agent_templates_pkey PRIMARY KEY (id);


--
-- TOC entry 5011 (class 2606 OID 130327)
-- Name: agents agents_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_pkey PRIMARY KEY (id);


--
-- TOC entry 4987 (class 2606 OID 130265)
-- Name: api_keys api_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_pkey PRIMARY KEY (id);


--
-- TOC entry 5031 (class 2606 OID 130380)
-- Name: configurations configurations_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.configurations
    ADD CONSTRAINT configurations_pkey PRIMARY KEY (id);


--
-- TOC entry 5043 (class 2606 OID 130414)
-- Name: context_index context_index_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.context_index
    ADD CONSTRAINT context_index_pkey PRIMARY KEY (id);


--
-- TOC entry 5037 (class 2606 OID 130397)
-- Name: discovery_config discovery_config_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.discovery_config
    ADD CONSTRAINT discovery_config_pkey PRIMARY KEY (id);


--
-- TOC entry 5103 (class 2606 OID 130623)
-- Name: git_commits git_commits_commit_hash_key; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.git_commits
    ADD CONSTRAINT git_commits_commit_hash_key UNIQUE (commit_hash);


--
-- TOC entry 5105 (class 2606 OID 130621)
-- Name: git_commits git_commits_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.git_commits
    ADD CONSTRAINT git_commits_pkey PRIMARY KEY (id);


--
-- TOC entry 4925 (class 2606 OID 130126)
-- Name: git_configs git_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.git_configs
    ADD CONSTRAINT git_configs_pkey PRIMARY KEY (id);


--
-- TOC entry 5088 (class 2606 OID 130552)
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- TOC entry 5051 (class 2606 OID 130432)
-- Name: large_document_index large_document_index_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.large_document_index
    ADD CONSTRAINT large_document_index_pkey PRIMARY KEY (id);


--
-- TOC entry 4966 (class 2606 OID 130202)
-- Name: mcp_agent_jobs mcp_agent_jobs_job_id_key; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.mcp_agent_jobs
    ADD CONSTRAINT mcp_agent_jobs_job_id_key UNIQUE (job_id);


--
-- TOC entry 4968 (class 2606 OID 130200)
-- Name: mcp_agent_jobs mcp_agent_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.mcp_agent_jobs
    ADD CONSTRAINT mcp_agent_jobs_pkey PRIMARY KEY (id);


--
-- TOC entry 5000 (class 2606 OID 130289)
-- Name: mcp_context_index mcp_context_index_chunk_id_key; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.mcp_context_index
    ADD CONSTRAINT mcp_context_index_chunk_id_key UNIQUE (chunk_id);


--
-- TOC entry 5002 (class 2606 OID 130287)
-- Name: mcp_context_index mcp_context_index_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.mcp_context_index
    ADD CONSTRAINT mcp_context_index_pkey PRIMARY KEY (id);


--
-- TOC entry 5007 (class 2606 OID 130310)
-- Name: mcp_context_summary mcp_context_summary_context_id_key; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.mcp_context_summary
    ADD CONSTRAINT mcp_context_summary_context_id_key UNIQUE (context_id);


--
-- TOC entry 5009 (class 2606 OID 130308)
-- Name: mcp_context_summary mcp_context_summary_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.mcp_context_summary
    ADD CONSTRAINT mcp_context_summary_pkey PRIMARY KEY (id);


--
-- TOC entry 5063 (class 2606 OID 130449)
-- Name: mcp_sessions mcp_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.mcp_sessions
    ADD CONSTRAINT mcp_sessions_pkey PRIMARY KEY (id);


--
-- TOC entry 5070 (class 2606 OID 130475)
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- TOC entry 5119 (class 2606 OID 130651)
-- Name: optimization_metrics optimization_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.optimization_metrics
    ADD CONSTRAINT optimization_metrics_pkey PRIMARY KEY (id);


--
-- TOC entry 4960 (class 2606 OID 130185)
-- Name: optimization_rules optimization_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.optimization_rules
    ADD CONSTRAINT optimization_rules_pkey PRIMARY KEY (id);


--
-- TOC entry 4914 (class 2606 OID 130098)
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- TOC entry 4973 (class 2606 OID 130214)
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- TOC entry 5020 (class 2606 OID 130345)
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);


--
-- TOC entry 4943 (class 2606 OID 130145)
-- Name: setup_state setup_state_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.setup_state
    ADD CONSTRAINT setup_state_pkey PRIMARY KEY (id);


--
-- TOC entry 5083 (class 2606 OID 130498)
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


--
-- TOC entry 4980 (class 2606 OID 130230)
-- Name: template_archives template_archives_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.template_archives
    ADD CONSTRAINT template_archives_pkey PRIMARY KEY (id);


--
-- TOC entry 4985 (class 2606 OID 130248)
-- Name: template_augmentations template_augmentations_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.template_augmentations
    ADD CONSTRAINT template_augmentations_pkey PRIMARY KEY (id);


--
-- TOC entry 5101 (class 2606 OID 130593)
-- Name: template_usage_stats template_usage_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.template_usage_stats
    ADD CONSTRAINT template_usage_stats_pkey PRIMARY KEY (id);


--
-- TOC entry 5016 (class 2606 OID 130329)
-- Name: agents uq_agent_project_name; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT uq_agent_project_name UNIQUE (project_id, name);


--
-- TOC entry 5035 (class 2606 OID 130382)
-- Name: configurations uq_config_tenant_key; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.configurations
    ADD CONSTRAINT uq_config_tenant_key UNIQUE (tenant_key, key);


--
-- TOC entry 5048 (class 2606 OID 130416)
-- Name: context_index uq_context_index; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.context_index
    ADD CONSTRAINT uq_context_index UNIQUE (project_id, document_name, section_name);


--
-- TOC entry 5041 (class 2606 OID 130399)
-- Name: discovery_config uq_discovery_path; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.discovery_config
    ADD CONSTRAINT uq_discovery_path UNIQUE (project_id, path_key);


--
-- TOC entry 4931 (class 2606 OID 130128)
-- Name: git_configs uq_git_config_product; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.git_configs
    ADD CONSTRAINT uq_git_config_product UNIQUE (product_id);


--
-- TOC entry 5053 (class 2606 OID 130434)
-- Name: large_document_index uq_large_doc_path; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.large_document_index
    ADD CONSTRAINT uq_large_doc_path UNIQUE (project_id, document_path);


--
-- TOC entry 5022 (class 2606 OID 130347)
-- Name: sessions uq_session_project_number; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT uq_session_project_number UNIQUE (project_id, session_number);


--
-- TOC entry 4923 (class 2606 OID 130112)
-- Name: agent_templates uq_template_product_name_version; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.agent_templates
    ADD CONSTRAINT uq_template_product_name_version UNIQUE (product_id, name, version);


--
-- TOC entry 5027 (class 2606 OID 130364)
-- Name: visions uq_vision_chunk; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.visions
    ADD CONSTRAINT uq_vision_chunk UNIQUE (project_id, document_name, chunk_number);


--
-- TOC entry 4954 (class 2606 OID 130165)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- TOC entry 5029 (class 2606 OID 130362)
-- Name: visions visions_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.visions
    ADD CONSTRAINT visions_pkey PRIMARY KEY (id);


--
-- TOC entry 5012 (class 1259 OID 130337)
-- Name: idx_agent_project; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_agent_project ON public.agents USING btree (project_id);


--
-- TOC entry 5013 (class 1259 OID 130336)
-- Name: idx_agent_status; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_agent_status ON public.agents USING btree (status);


--
-- TOC entry 5014 (class 1259 OID 130335)
-- Name: idx_agent_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_agent_tenant ON public.agents USING btree (tenant_key);


--
-- TOC entry 4988 (class 1259 OID 130274)
-- Name: idx_apikey_active; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_apikey_active ON public.api_keys USING btree (is_active);


--
-- TOC entry 4989 (class 1259 OID 130272)
-- Name: idx_apikey_hash; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_apikey_hash ON public.api_keys USING btree (key_hash);


--
-- TOC entry 4990 (class 1259 OID 130275)
-- Name: idx_apikey_permissions_gin; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_apikey_permissions_gin ON public.api_keys USING gin (permissions);


--
-- TOC entry 4991 (class 1259 OID 130277)
-- Name: idx_apikey_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_apikey_tenant ON public.api_keys USING btree (tenant_key);


--
-- TOC entry 4992 (class 1259 OID 130271)
-- Name: idx_apikey_user; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_apikey_user ON public.api_keys USING btree (user_id);


--
-- TOC entry 4974 (class 1259 OID 130238)
-- Name: idx_archive_date; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_archive_date ON public.template_archives USING btree (archived_at);


--
-- TOC entry 4975 (class 1259 OID 130236)
-- Name: idx_archive_product; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_archive_product ON public.template_archives USING btree (product_id);


--
-- TOC entry 4976 (class 1259 OID 130240)
-- Name: idx_archive_template; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_archive_template ON public.template_archives USING btree (template_id);


--
-- TOC entry 4977 (class 1259 OID 130239)
-- Name: idx_archive_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_archive_tenant ON public.template_archives USING btree (tenant_key);


--
-- TOC entry 4978 (class 1259 OID 130237)
-- Name: idx_archive_version; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_archive_version ON public.template_archives USING btree (version);


--
-- TOC entry 4981 (class 1259 OID 130254)
-- Name: idx_augment_active; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_augment_active ON public.template_augmentations USING btree (is_active);


--
-- TOC entry 4982 (class 1259 OID 130255)
-- Name: idx_augment_template; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_augment_template ON public.template_augmentations USING btree (template_id);


--
-- TOC entry 4983 (class 1259 OID 130256)
-- Name: idx_augment_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_augment_tenant ON public.template_augmentations USING btree (tenant_key);


--
-- TOC entry 5032 (class 1259 OID 130388)
-- Name: idx_config_category; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_config_category ON public.configurations USING btree (category);


--
-- TOC entry 5033 (class 1259 OID 130389)
-- Name: idx_config_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_config_tenant ON public.configurations USING btree (tenant_key);


--
-- TOC entry 5044 (class 1259 OID 130424)
-- Name: idx_context_doc; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_context_doc ON public.context_index USING btree (document_name);


--
-- TOC entry 5045 (class 1259 OID 130422)
-- Name: idx_context_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_context_tenant ON public.context_index USING btree (tenant_key);


--
-- TOC entry 5046 (class 1259 OID 130423)
-- Name: idx_context_type; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_context_type ON public.context_index USING btree (index_type);


--
-- TOC entry 5038 (class 1259 OID 130406)
-- Name: idx_discovery_project; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_discovery_project ON public.discovery_config USING btree (project_id);


--
-- TOC entry 5039 (class 1259 OID 130405)
-- Name: idx_discovery_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_discovery_tenant ON public.discovery_config USING btree (tenant_key);


--
-- TOC entry 5106 (class 1259 OID 130639)
-- Name: idx_git_commit_date; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_git_commit_date ON public.git_commits USING btree (committed_at);


--
-- TOC entry 5107 (class 1259 OID 130638)
-- Name: idx_git_commit_hash; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_git_commit_hash ON public.git_commits USING btree (commit_hash);


--
-- TOC entry 5108 (class 1259 OID 130636)
-- Name: idx_git_commit_product; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_git_commit_product ON public.git_commits USING btree (product_id);


--
-- TOC entry 5109 (class 1259 OID 130637)
-- Name: idx_git_commit_project; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_git_commit_project ON public.git_commits USING btree (project_id);


--
-- TOC entry 5110 (class 1259 OID 130634)
-- Name: idx_git_commit_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_git_commit_tenant ON public.git_commits USING btree (tenant_key);


--
-- TOC entry 5111 (class 1259 OID 130635)
-- Name: idx_git_commit_trigger; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_git_commit_trigger ON public.git_commits USING btree (triggered_by);


--
-- TOC entry 4926 (class 1259 OID 130130)
-- Name: idx_git_config_active; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_git_config_active ON public.git_configs USING btree (is_active);


--
-- TOC entry 4927 (class 1259 OID 130132)
-- Name: idx_git_config_auth; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_git_config_auth ON public.git_configs USING btree (auth_method);


--
-- TOC entry 4928 (class 1259 OID 130131)
-- Name: idx_git_config_product; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_git_config_product ON public.git_configs USING btree (product_id);


--
-- TOC entry 4929 (class 1259 OID 130129)
-- Name: idx_git_config_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_git_config_tenant ON public.git_configs USING btree (tenant_key);


--
-- TOC entry 5091 (class 1259 OID 130585)
-- Name: idx_interaction_created; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_interaction_created ON public.agent_interactions USING btree (created_at);


--
-- TOC entry 5092 (class 1259 OID 130583)
-- Name: idx_interaction_parent; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_interaction_parent ON public.agent_interactions USING btree (parent_agent_id);


--
-- TOC entry 5093 (class 1259 OID 130582)
-- Name: idx_interaction_project; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_interaction_project ON public.agent_interactions USING btree (project_id);


--
-- TOC entry 5094 (class 1259 OID 130581)
-- Name: idx_interaction_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_interaction_tenant ON public.agent_interactions USING btree (tenant_key);


--
-- TOC entry 5095 (class 1259 OID 130584)
-- Name: idx_interaction_type; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_interaction_type ON public.agent_interactions USING btree (interaction_type);


--
-- TOC entry 5084 (class 1259 OID 130559)
-- Name: idx_job_agent; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_job_agent ON public.jobs USING btree (agent_id);


--
-- TOC entry 5085 (class 1259 OID 130558)
-- Name: idx_job_status; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_job_status ON public.jobs USING btree (status);


--
-- TOC entry 5086 (class 1259 OID 130560)
-- Name: idx_job_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_job_tenant ON public.jobs USING btree (tenant_key);


--
-- TOC entry 5049 (class 1259 OID 130440)
-- Name: idx_large_doc_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_large_doc_tenant ON public.large_document_index USING btree (tenant_key);


--
-- TOC entry 4961 (class 1259 OID 130206)
-- Name: idx_mcp_agent_jobs_job_id; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_mcp_agent_jobs_job_id ON public.mcp_agent_jobs USING btree (job_id);


--
-- TOC entry 4962 (class 1259 OID 130204)
-- Name: idx_mcp_agent_jobs_tenant_status; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_mcp_agent_jobs_tenant_status ON public.mcp_agent_jobs USING btree (tenant_key, status);


--
-- TOC entry 4963 (class 1259 OID 130205)
-- Name: idx_mcp_agent_jobs_tenant_type; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_mcp_agent_jobs_tenant_type ON public.mcp_agent_jobs USING btree (tenant_key, agent_type);


--
-- TOC entry 4995 (class 1259 OID 130297)
-- Name: idx_mcp_context_chunk_id; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_mcp_context_chunk_id ON public.mcp_context_index USING btree (chunk_id);


--
-- TOC entry 4996 (class 1259 OID 130295)
-- Name: idx_mcp_context_searchable; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_mcp_context_searchable ON public.mcp_context_index USING gin (searchable_vector);


--
-- TOC entry 4997 (class 1259 OID 130296)
-- Name: idx_mcp_context_tenant_product; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_mcp_context_tenant_product ON public.mcp_context_index USING btree (tenant_key, product_id);


--
-- TOC entry 5054 (class 1259 OID 130464)
-- Name: idx_mcp_session_api_key; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_mcp_session_api_key ON public.mcp_sessions USING btree (api_key_id);


--
-- TOC entry 5055 (class 1259 OID 130463)
-- Name: idx_mcp_session_cleanup; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_mcp_session_cleanup ON public.mcp_sessions USING btree (expires_at, last_accessed);


--
-- TOC entry 5056 (class 1259 OID 130465)
-- Name: idx_mcp_session_data_gin; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_mcp_session_data_gin ON public.mcp_sessions USING gin (session_data);


--
-- TOC entry 5057 (class 1259 OID 130462)
-- Name: idx_mcp_session_expires; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_mcp_session_expires ON public.mcp_sessions USING btree (expires_at);


--
-- TOC entry 5058 (class 1259 OID 130460)
-- Name: idx_mcp_session_last_accessed; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_mcp_session_last_accessed ON public.mcp_sessions USING btree (last_accessed);


--
-- TOC entry 5059 (class 1259 OID 130467)
-- Name: idx_mcp_session_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_mcp_session_tenant ON public.mcp_sessions USING btree (tenant_key);


--
-- TOC entry 5003 (class 1259 OID 130317)
-- Name: idx_mcp_summary_context_id; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_mcp_summary_context_id ON public.mcp_context_summary USING btree (context_id);


--
-- TOC entry 5004 (class 1259 OID 130318)
-- Name: idx_mcp_summary_tenant_product; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_mcp_summary_tenant_product ON public.mcp_context_summary USING btree (tenant_key, product_id);


--
-- TOC entry 5064 (class 1259 OID 130488)
-- Name: idx_message_created; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_message_created ON public.messages USING btree (created_at);


--
-- TOC entry 5065 (class 1259 OID 130486)
-- Name: idx_message_priority; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_message_priority ON public.messages USING btree (priority);


--
-- TOC entry 5066 (class 1259 OID 130489)
-- Name: idx_message_project; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_message_project ON public.messages USING btree (project_id);


--
-- TOC entry 5067 (class 1259 OID 130490)
-- Name: idx_message_status; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_message_status ON public.messages USING btree (status);


--
-- TOC entry 5068 (class 1259 OID 130487)
-- Name: idx_message_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_message_tenant ON public.messages USING btree (tenant_key);


--
-- TOC entry 5112 (class 1259 OID 130657)
-- Name: idx_optimization_metric_agent; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_optimization_metric_agent ON public.optimization_metrics USING btree (agent_id);


--
-- TOC entry 5113 (class 1259 OID 130660)
-- Name: idx_optimization_metric_date; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_optimization_metric_date ON public.optimization_metrics USING btree (created_at);


--
-- TOC entry 5114 (class 1259 OID 130661)
-- Name: idx_optimization_metric_optimized; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_optimization_metric_optimized ON public.optimization_metrics USING btree (optimized);


--
-- TOC entry 5115 (class 1259 OID 130662)
-- Name: idx_optimization_metric_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_optimization_metric_tenant ON public.optimization_metrics USING btree (tenant_key);


--
-- TOC entry 5116 (class 1259 OID 130658)
-- Name: idx_optimization_metric_type; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_optimization_metric_type ON public.optimization_metrics USING btree (operation_type);


--
-- TOC entry 4955 (class 1259 OID 130189)
-- Name: idx_optimization_rule_active; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_optimization_rule_active ON public.optimization_rules USING btree (is_active);


--
-- TOC entry 4956 (class 1259 OID 130186)
-- Name: idx_optimization_rule_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_optimization_rule_tenant ON public.optimization_rules USING btree (tenant_key);


--
-- TOC entry 4957 (class 1259 OID 130187)
-- Name: idx_optimization_rule_type; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_optimization_rule_type ON public.optimization_rules USING btree (operation_type);


--
-- TOC entry 4909 (class 1259 OID 130100)
-- Name: idx_product_config_data_gin; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_product_config_data_gin ON public.products USING gin (config_data);


--
-- TOC entry 4910 (class 1259 OID 130101)
-- Name: idx_product_name; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_product_name ON public.products USING btree (name);


--
-- TOC entry 4911 (class 1259 OID 130099)
-- Name: idx_product_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_product_tenant ON public.products USING btree (tenant_key);


--
-- TOC entry 4969 (class 1259 OID 130221)
-- Name: idx_project_status; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_project_status ON public.projects USING btree (status);


--
-- TOC entry 4970 (class 1259 OID 130220)
-- Name: idx_project_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_project_tenant ON public.projects USING btree (tenant_key);


--
-- TOC entry 5017 (class 1259 OID 130354)
-- Name: idx_session_project; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_session_project ON public.sessions USING btree (project_id);


--
-- TOC entry 5018 (class 1259 OID 130353)
-- Name: idx_session_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_session_tenant ON public.sessions USING btree (tenant_key);


--
-- TOC entry 4932 (class 1259 OID 130146)
-- Name: idx_setup_database_incomplete; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_setup_database_incomplete ON public.setup_state USING btree (tenant_key, database_initialized) WHERE (database_initialized = false);


--
-- TOC entry 4933 (class 1259 OID 130148)
-- Name: idx_setup_database_initialized; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_setup_database_initialized ON public.setup_state USING btree (database_initialized);


--
-- TOC entry 4934 (class 1259 OID 130150)
-- Name: idx_setup_features_gin; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_setup_features_gin ON public.setup_state USING gin (features_configured);


--
-- TOC entry 4935 (class 1259 OID 130152)
-- Name: idx_setup_fresh_install; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_setup_fresh_install ON public.setup_state USING btree (tenant_key, first_admin_created) WHERE (first_admin_created = false);


--
-- TOC entry 4936 (class 1259 OID 130149)
-- Name: idx_setup_mode; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_setup_mode ON public.setup_state USING btree (install_mode);


--
-- TOC entry 4937 (class 1259 OID 130147)
-- Name: idx_setup_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_setup_tenant ON public.setup_state USING btree (tenant_key);


--
-- TOC entry 4938 (class 1259 OID 130151)
-- Name: idx_setup_tools_gin; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_setup_tools_gin ON public.setup_state USING gin (tools_enabled);


--
-- TOC entry 5071 (class 1259 OID 130543)
-- Name: idx_task_assigned; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_assigned ON public.tasks USING btree (assigned_agent_id);


--
-- TOC entry 5072 (class 1259 OID 130539)
-- Name: idx_task_assigned_to_user; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_assigned_to_user ON public.tasks USING btree (assigned_to_user_id);


--
-- TOC entry 5073 (class 1259 OID 130542)
-- Name: idx_task_converted_to_project; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_converted_to_project ON public.tasks USING btree (converted_to_project_id);


--
-- TOC entry 5074 (class 1259 OID 130538)
-- Name: idx_task_created_by_user; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_created_by_user ON public.tasks USING btree (created_by_user_id);


--
-- TOC entry 5075 (class 1259 OID 130537)
-- Name: idx_task_priority; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_priority ON public.tasks USING btree (priority);


--
-- TOC entry 5076 (class 1259 OID 130541)
-- Name: idx_task_product; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_product ON public.tasks USING btree (product_id);


--
-- TOC entry 5077 (class 1259 OID 130544)
-- Name: idx_task_project; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_project ON public.tasks USING btree (project_id);


--
-- TOC entry 5078 (class 1259 OID 130536)
-- Name: idx_task_status; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_status ON public.tasks USING btree (status);


--
-- TOC entry 5079 (class 1259 OID 130534)
-- Name: idx_task_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_tenant ON public.tasks USING btree (tenant_key);


--
-- TOC entry 5080 (class 1259 OID 130535)
-- Name: idx_task_tenant_assigned_user; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_tenant_assigned_user ON public.tasks USING btree (tenant_key, assigned_to_user_id);


--
-- TOC entry 5081 (class 1259 OID 130540)
-- Name: idx_task_tenant_created_user; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_tenant_created_user ON public.tasks USING btree (tenant_key, created_by_user_id);


--
-- TOC entry 4917 (class 1259 OID 130117)
-- Name: idx_template_active; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_template_active ON public.agent_templates USING btree (is_active);


--
-- TOC entry 4918 (class 1259 OID 130115)
-- Name: idx_template_category; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_template_category ON public.agent_templates USING btree (category);


--
-- TOC entry 4919 (class 1259 OID 130113)
-- Name: idx_template_product; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_template_product ON public.agent_templates USING btree (product_id);


--
-- TOC entry 4920 (class 1259 OID 130116)
-- Name: idx_template_role; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_template_role ON public.agent_templates USING btree (role);


--
-- TOC entry 4921 (class 1259 OID 130114)
-- Name: idx_template_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_template_tenant ON public.agent_templates USING btree (tenant_key);


--
-- TOC entry 5096 (class 1259 OID 130609)
-- Name: idx_usage_date; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_usage_date ON public.template_usage_stats USING btree (used_at);


--
-- TOC entry 5097 (class 1259 OID 130612)
-- Name: idx_usage_project; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_usage_project ON public.template_usage_stats USING btree (project_id);


--
-- TOC entry 5098 (class 1259 OID 130611)
-- Name: idx_usage_template; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_usage_template ON public.template_usage_stats USING btree (template_id);


--
-- TOC entry 5099 (class 1259 OID 130610)
-- Name: idx_usage_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_usage_tenant ON public.template_usage_stats USING btree (tenant_key);


--
-- TOC entry 4944 (class 1259 OID 130173)
-- Name: idx_user_active; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_user_active ON public.users USING btree (is_active);


--
-- TOC entry 4945 (class 1259 OID 130172)
-- Name: idx_user_email; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_user_email ON public.users USING btree (email);


--
-- TOC entry 4946 (class 1259 OID 130167)
-- Name: idx_user_pin_lockout; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_user_pin_lockout ON public.users USING btree (pin_lockout_until);


--
-- TOC entry 4947 (class 1259 OID 130174)
-- Name: idx_user_system; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_user_system ON public.users USING btree (is_system_user);


--
-- TOC entry 4948 (class 1259 OID 130166)
-- Name: idx_user_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_user_tenant ON public.users USING btree (tenant_key);


--
-- TOC entry 4949 (class 1259 OID 130168)
-- Name: idx_user_username; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_user_username ON public.users USING btree (username);


--
-- TOC entry 5023 (class 1259 OID 130371)
-- Name: idx_vision_document; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_vision_document ON public.visions USING btree (document_name);


--
-- TOC entry 5024 (class 1259 OID 130370)
-- Name: idx_vision_project; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_vision_project ON public.visions USING btree (project_id);


--
-- TOC entry 5025 (class 1259 OID 130372)
-- Name: idx_vision_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_vision_tenant ON public.visions USING btree (tenant_key);


--
-- TOC entry 4993 (class 1259 OID 130273)
-- Name: ix_api_keys_key_hash; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE UNIQUE INDEX ix_api_keys_key_hash ON public.api_keys USING btree (key_hash);


--
-- TOC entry 4994 (class 1259 OID 130276)
-- Name: ix_api_keys_tenant_key; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX ix_api_keys_tenant_key ON public.api_keys USING btree (tenant_key);


--
-- TOC entry 4964 (class 1259 OID 130203)
-- Name: ix_mcp_agent_jobs_tenant_key; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX ix_mcp_agent_jobs_tenant_key ON public.mcp_agent_jobs USING btree (tenant_key);


--
-- TOC entry 4998 (class 1259 OID 130298)
-- Name: ix_mcp_context_index_tenant_key; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX ix_mcp_context_index_tenant_key ON public.mcp_context_index USING btree (tenant_key);


--
-- TOC entry 5005 (class 1259 OID 130316)
-- Name: ix_mcp_context_summary_tenant_key; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX ix_mcp_context_summary_tenant_key ON public.mcp_context_summary USING btree (tenant_key);


--
-- TOC entry 5060 (class 1259 OID 130461)
-- Name: ix_mcp_sessions_session_id; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE UNIQUE INDEX ix_mcp_sessions_session_id ON public.mcp_sessions USING btree (session_id);


--
-- TOC entry 5061 (class 1259 OID 130466)
-- Name: ix_mcp_sessions_tenant_key; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX ix_mcp_sessions_tenant_key ON public.mcp_sessions USING btree (tenant_key);


--
-- TOC entry 5117 (class 1259 OID 130659)
-- Name: ix_optimization_metrics_tenant_key; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX ix_optimization_metrics_tenant_key ON public.optimization_metrics USING btree (tenant_key);


--
-- TOC entry 4958 (class 1259 OID 130188)
-- Name: ix_optimization_rules_tenant_key; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX ix_optimization_rules_tenant_key ON public.optimization_rules USING btree (tenant_key);


--
-- TOC entry 4912 (class 1259 OID 130102)
-- Name: ix_products_tenant_key; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX ix_products_tenant_key ON public.products USING btree (tenant_key);


--
-- TOC entry 4971 (class 1259 OID 130222)
-- Name: ix_projects_alias; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE UNIQUE INDEX ix_projects_alias ON public.projects USING btree (alias);


--
-- TOC entry 4939 (class 1259 OID 130153)
-- Name: ix_setup_state_database_initialized; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX ix_setup_state_database_initialized ON public.setup_state USING btree (database_initialized);


--
-- TOC entry 4940 (class 1259 OID 130154)
-- Name: ix_setup_state_first_admin_created; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX ix_setup_state_first_admin_created ON public.setup_state USING btree (first_admin_created);


--
-- TOC entry 4941 (class 1259 OID 130155)
-- Name: ix_setup_state_tenant_key; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE UNIQUE INDEX ix_setup_state_tenant_key ON public.setup_state USING btree (tenant_key);


--
-- TOC entry 4950 (class 1259 OID 130171)
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- TOC entry 4951 (class 1259 OID 130169)
-- Name: ix_users_tenant_key; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX ix_users_tenant_key ON public.users USING btree (tenant_key);


--
-- TOC entry 4952 (class 1259 OID 130170)
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- TOC entry 5145 (class 2606 OID 130576)
-- Name: agent_interactions agent_interactions_parent_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.agent_interactions
    ADD CONSTRAINT agent_interactions_parent_agent_id_fkey FOREIGN KEY (parent_agent_id) REFERENCES public.agents(id);


--
-- TOC entry 5146 (class 2606 OID 130571)
-- Name: agent_interactions agent_interactions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.agent_interactions
    ADD CONSTRAINT agent_interactions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- TOC entry 5126 (class 2606 OID 130330)
-- Name: agents agents_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- TOC entry 5123 (class 2606 OID 130266)
-- Name: api_keys api_keys_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 5129 (class 2606 OID 130383)
-- Name: configurations configurations_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.configurations
    ADD CONSTRAINT configurations_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- TOC entry 5131 (class 2606 OID 130417)
-- Name: context_index context_index_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.context_index
    ADD CONSTRAINT context_index_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- TOC entry 5130 (class 2606 OID 130400)
-- Name: discovery_config discovery_config_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.discovery_config
    ADD CONSTRAINT discovery_config_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- TOC entry 5150 (class 2606 OID 130629)
-- Name: git_commits git_commits_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.git_commits
    ADD CONSTRAINT git_commits_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id);


--
-- TOC entry 5151 (class 2606 OID 130624)
-- Name: git_commits git_commits_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.git_commits
    ADD CONSTRAINT git_commits_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- TOC entry 5144 (class 2606 OID 130553)
-- Name: jobs jobs_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id);


--
-- TOC entry 5132 (class 2606 OID 130435)
-- Name: large_document_index large_document_index_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.large_document_index
    ADD CONSTRAINT large_document_index_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- TOC entry 5124 (class 2606 OID 130290)
-- Name: mcp_context_index mcp_context_index_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.mcp_context_index
    ADD CONSTRAINT mcp_context_index_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- TOC entry 5125 (class 2606 OID 130311)
-- Name: mcp_context_summary mcp_context_summary_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.mcp_context_summary
    ADD CONSTRAINT mcp_context_summary_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- TOC entry 5133 (class 2606 OID 130450)
-- Name: mcp_sessions mcp_sessions_api_key_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.mcp_sessions
    ADD CONSTRAINT mcp_sessions_api_key_id_fkey FOREIGN KEY (api_key_id) REFERENCES public.api_keys(id) ON DELETE CASCADE;


--
-- TOC entry 5134 (class 2606 OID 130455)
-- Name: mcp_sessions mcp_sessions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.mcp_sessions
    ADD CONSTRAINT mcp_sessions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id) ON DELETE SET NULL;


--
-- TOC entry 5135 (class 2606 OID 130481)
-- Name: messages messages_from_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_from_agent_id_fkey FOREIGN KEY (from_agent_id) REFERENCES public.agents(id);


--
-- TOC entry 5136 (class 2606 OID 130476)
-- Name: messages messages_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- TOC entry 5152 (class 2606 OID 130652)
-- Name: optimization_metrics optimization_metrics_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.optimization_metrics
    ADD CONSTRAINT optimization_metrics_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id);


--
-- TOC entry 5120 (class 2606 OID 130215)
-- Name: projects projects_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- TOC entry 5127 (class 2606 OID 130348)
-- Name: sessions sessions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- TOC entry 5137 (class 2606 OID 130509)
-- Name: tasks tasks_assigned_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_assigned_agent_id_fkey FOREIGN KEY (assigned_agent_id) REFERENCES public.agents(id);


--
-- TOC entry 5138 (class 2606 OID 130524)
-- Name: tasks tasks_assigned_to_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_assigned_to_user_id_fkey FOREIGN KEY (assigned_to_user_id) REFERENCES public.users(id);


--
-- TOC entry 5139 (class 2606 OID 130529)
-- Name: tasks tasks_converted_to_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_converted_to_project_id_fkey FOREIGN KEY (converted_to_project_id) REFERENCES public.projects(id);


--
-- TOC entry 5140 (class 2606 OID 130519)
-- Name: tasks tasks_created_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id);


--
-- TOC entry 5141 (class 2606 OID 130514)
-- Name: tasks tasks_parent_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_parent_task_id_fkey FOREIGN KEY (parent_task_id) REFERENCES public.tasks(id);


--
-- TOC entry 5142 (class 2606 OID 130499)
-- Name: tasks tasks_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- TOC entry 5143 (class 2606 OID 130504)
-- Name: tasks tasks_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- TOC entry 5121 (class 2606 OID 130231)
-- Name: template_archives template_archives_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.template_archives
    ADD CONSTRAINT template_archives_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.agent_templates(id);


--
-- TOC entry 5122 (class 2606 OID 130249)
-- Name: template_augmentations template_augmentations_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.template_augmentations
    ADD CONSTRAINT template_augmentations_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.agent_templates(id);


--
-- TOC entry 5147 (class 2606 OID 130599)
-- Name: template_usage_stats template_usage_stats_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.template_usage_stats
    ADD CONSTRAINT template_usage_stats_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id);


--
-- TOC entry 5148 (class 2606 OID 130604)
-- Name: template_usage_stats template_usage_stats_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.template_usage_stats
    ADD CONSTRAINT template_usage_stats_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- TOC entry 5149 (class 2606 OID 130594)
-- Name: template_usage_stats template_usage_stats_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.template_usage_stats
    ADD CONSTRAINT template_usage_stats_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.agent_templates(id);


--
-- TOC entry 5128 (class 2606 OID 130365)
-- Name: visions visions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.visions
    ADD CONSTRAINT visions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- TOC entry 5334 (class 0 OID 0)
-- Dependencies: 6
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: pg_database_owner
--

GRANT ALL ON SCHEMA public TO giljo_owner;
GRANT ALL ON SCHEMA public TO giljo_user;


--
-- TOC entry 2203 (class 826 OID 130089)
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: giljo_owner
--

ALTER DEFAULT PRIVILEGES FOR ROLE giljo_owner IN SCHEMA public GRANT SELECT,USAGE ON SEQUENCES TO giljo_user;


--
-- TOC entry 2202 (class 826 OID 130088)
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: giljo_owner
--

ALTER DEFAULT PRIVILEGES FOR ROLE giljo_owner IN SCHEMA public GRANT SELECT,INSERT,DELETE,UPDATE ON TABLES TO giljo_user;


-- Completed on 2025-10-24 14:59:05

--
-- PostgreSQL database dump complete
--

