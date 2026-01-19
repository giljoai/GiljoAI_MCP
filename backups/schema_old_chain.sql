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
-- Name: public; Type: SCHEMA; Schema: -; Owner: postgres
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO postgres;

--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: postgres
--

COMMENT ON SCHEMA public IS '';


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
    start_time timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    end_time timestamp with time zone,
    duration_seconds integer,
    tokens_used integer,
    result text,
    error_message text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    meta_data json,
    CONSTRAINT ck_interaction_type CHECK (((interaction_type)::text = ANY (ARRAY[('SPAWN'::character varying)::text, ('COMPLETE'::character varying)::text, ('ERROR'::character varying)::text])))
);


ALTER TABLE public.agent_interactions OWNER TO giljo_user;

--
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
    last_active timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    decommissioned_at timestamp with time zone,
    meta_data json
);


ALTER TABLE public.agents OWNER TO giljo_user;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: giljo_user
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO giljo_user;

--
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
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone
);


ALTER TABLE public.configurations OWNER TO giljo_user;

--
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
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamp with time zone,
    meta_data json
);


ALTER TABLE public.jobs OWNER TO giljo_user;

--
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
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at timestamp with time zone,
    completed_at timestamp with time zone,
    meta_data json
);


ALTER TABLE public.messages OWNER TO giljo_user;

--
-- Name: products; Type: TABLE; Schema: public; Owner: giljo_user
--

CREATE TABLE public.products (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    vision_path character varying(500),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone,
    meta_data json,
    config_data jsonb,
    is_active boolean DEFAULT false NOT NULL
);


ALTER TABLE public.products OWNER TO giljo_user;

--
-- Name: projects; Type: TABLE; Schema: public; Owner: giljo_user
--

CREATE TABLE public.projects (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    name character varying(255) NOT NULL,
    mission text NOT NULL,
    status character varying(50),
    context_budget integer,
    context_used integer,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone,
    completed_at timestamp with time zone,
    meta_data json,
    product_id character varying(36),
    alias character varying(6) NOT NULL
);


ALTER TABLE public.projects OWNER TO giljo_user;

--
-- Name: COLUMN projects.alias; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.projects.alias IS '6-character alphanumeric project identifier (e.g., A1B2C3)';


--
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
    started_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    ended_at timestamp with time zone,
    duration_minutes integer,
    meta_data json
);


ALTER TABLE public.sessions OWNER TO giljo_user;

--
-- Name: setup_state; Type: TABLE; Schema: public; Owner: giljo_user
--

CREATE TABLE public.setup_state (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    completed boolean NOT NULL,
    completed_at timestamp with time zone,
    setup_version character varying(20),
    database_version character varying(20),
    python_version character varying(20),
    node_version character varying(20),
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
    default_password_active boolean DEFAULT true NOT NULL,
    password_changed_at timestamp with time zone,
    CONSTRAINT ck_completed_at_required CHECK (((completed = false) OR ((completed = true) AND (completed_at IS NOT NULL)))),
    CONSTRAINT ck_database_version_format CHECK (((database_version IS NULL) OR ((database_version)::text ~ '^[0-9]+(\.([0-9]+|[0-9]+\.[0-9]+))?$'::text))),
    CONSTRAINT ck_install_mode_values CHECK (((install_mode IS NULL) OR ((install_mode)::text = ANY (ARRAY[('localhost'::character varying)::text, ('server'::character varying)::text, ('lan'::character varying)::text, ('wan'::character varying)::text])))),
    CONSTRAINT ck_setup_version_format CHECK (((setup_version IS NULL) OR ((setup_version)::text ~ '^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9\.\-]+)?$'::text)))
);


ALTER TABLE public.setup_state OWNER TO giljo_user;

--
-- Name: COLUMN setup_state.features_configured; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.setup_state.features_configured IS 'Nested dict of configured features: {database: true, api: {enabled: true, port: 7272}}';


--
-- Name: COLUMN setup_state.tools_enabled; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.setup_state.tools_enabled IS 'Array of enabled MCP tool names';


--
-- Name: COLUMN setup_state.config_snapshot; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.setup_state.config_snapshot IS 'Snapshot of config.yaml at setup completion';


--
-- Name: COLUMN setup_state.validation_failures; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.setup_state.validation_failures IS 'Array of validation failure messages';


--
-- Name: COLUMN setup_state.validation_warnings; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.setup_state.validation_warnings IS 'Array of validation warning messages';


--
-- Name: COLUMN setup_state.install_mode; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.setup_state.install_mode IS 'Installation mode: localhost, server, lan, wan';


--
-- Name: COLUMN setup_state.install_path; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.setup_state.install_path IS 'Installation directory path';


--
-- Name: COLUMN setup_state.default_password_active; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.setup_state.default_password_active IS 'True if default admin/admin password is still active';


--
-- Name: COLUMN setup_state.password_changed_at; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.setup_state.password_changed_at IS 'Timestamp when default password was changed';


--
-- Name: tasks; Type: TABLE; Schema: public; Owner: giljo_user
--

CREATE TABLE public.tasks (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    project_id character varying(36) NOT NULL,
    assigned_agent_id character varying(36),
    parent_task_id character varying(36),
    title character varying(255) NOT NULL,
    description text,
    category character varying(100),
    status character varying(50),
    priority character varying(20),
    estimated_effort double precision,
    actual_effort double precision,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    due_date timestamp with time zone,
    meta_data json,
    product_id character varying(36),
    created_by_user_id character varying(36),
    assigned_to_user_id character varying(36),
    converted_to_project_id character varying(36)
);


ALTER TABLE public.tasks OWNER TO giljo_user;

--
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
-- Name: users; Type: TABLE; Schema: public; Owner: giljo_user
--

CREATE TABLE public.users (
    id character varying(36) NOT NULL,
    tenant_key character varying(36) NOT NULL,
    username character varying(64) NOT NULL,
    email character varying(255),
    password_hash character varying(255),
    full_name character varying(255),
    role character varying(32) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_login timestamp with time zone,
    is_system_user boolean DEFAULT false NOT NULL,
    field_priority_config jsonb,
    CONSTRAINT ck_user_role CHECK (((role)::text = ANY (ARRAY[('admin'::character varying)::text, ('developer'::character varying)::text, ('viewer'::character varying)::text])))
);


ALTER TABLE public.users OWNER TO giljo_user;

--
-- Name: COLUMN users.is_system_user; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.users.is_system_user IS 'True for auto-created system users (localhost) that bypass password auth';


--
-- Name: COLUMN users.field_priority_config; Type: COMMENT; Schema: public; Owner: giljo_user
--

COMMENT ON COLUMN public.users.field_priority_config IS 'User-customizable field priority for agent mission generation';


--
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
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone,
    meta_data json
);


ALTER TABLE public.visions OWNER TO giljo_user;

--
-- Name: agent_interactions agent_interactions_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.agent_interactions
    ADD CONSTRAINT agent_interactions_pkey PRIMARY KEY (id);


--
-- Name: agent_templates agent_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.agent_templates
    ADD CONSTRAINT agent_templates_pkey PRIMARY KEY (id);


--
-- Name: agents agents_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: api_keys api_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_pkey PRIMARY KEY (id);


--
-- Name: configurations configurations_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.configurations
    ADD CONSTRAINT configurations_pkey PRIMARY KEY (id);


--
-- Name: jobs jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: projects projects_tenant_key_key; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_tenant_key_key UNIQUE (tenant_key);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);


--
-- Name: setup_state setup_state_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.setup_state
    ADD CONSTRAINT setup_state_pkey PRIMARY KEY (id);


--
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


--
-- Name: template_archives template_archives_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.template_archives
    ADD CONSTRAINT template_archives_pkey PRIMARY KEY (id);


--
-- Name: template_augmentations template_augmentations_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.template_augmentations
    ADD CONSTRAINT template_augmentations_pkey PRIMARY KEY (id);


--
-- Name: template_usage_stats template_usage_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.template_usage_stats
    ADD CONSTRAINT template_usage_stats_pkey PRIMARY KEY (id);


--
-- Name: agents uq_agent_project_name; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT uq_agent_project_name UNIQUE (project_id, name);


--
-- Name: configurations uq_config_tenant_key; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.configurations
    ADD CONSTRAINT uq_config_tenant_key UNIQUE (tenant_key, key);


--
-- Name: sessions uq_session_project_number; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT uq_session_project_number UNIQUE (project_id, session_number);


--
-- Name: agent_templates uq_template_product_name_version; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.agent_templates
    ADD CONSTRAINT uq_template_product_name_version UNIQUE (product_id, name, version);


--
-- Name: visions uq_vision_chunk; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.visions
    ADD CONSTRAINT uq_vision_chunk UNIQUE (project_id, document_name, chunk_number);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: visions visions_pkey; Type: CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.visions
    ADD CONSTRAINT visions_pkey PRIMARY KEY (id);


--
-- Name: idx_agent_project; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_agent_project ON public.agents USING btree (project_id);


--
-- Name: idx_agent_status; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_agent_status ON public.agents USING btree (status);


--
-- Name: idx_agent_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_agent_tenant ON public.agents USING btree (tenant_key);


--
-- Name: idx_apikey_active; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_apikey_active ON public.api_keys USING btree (is_active);


--
-- Name: idx_apikey_hash; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_apikey_hash ON public.api_keys USING btree (key_hash);


--
-- Name: idx_apikey_permissions_gin; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_apikey_permissions_gin ON public.api_keys USING gin (permissions);


--
-- Name: idx_apikey_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_apikey_tenant ON public.api_keys USING btree (tenant_key);


--
-- Name: idx_apikey_user; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_apikey_user ON public.api_keys USING btree (user_id);


--
-- Name: idx_archive_date; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_archive_date ON public.template_archives USING btree (archived_at);


--
-- Name: idx_archive_product; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_archive_product ON public.template_archives USING btree (product_id);


--
-- Name: idx_archive_template; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_archive_template ON public.template_archives USING btree (template_id);


--
-- Name: idx_archive_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_archive_tenant ON public.template_archives USING btree (tenant_key);


--
-- Name: idx_archive_version; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_archive_version ON public.template_archives USING btree (version);


--
-- Name: idx_augment_active; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_augment_active ON public.template_augmentations USING btree (is_active);


--
-- Name: idx_augment_template; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_augment_template ON public.template_augmentations USING btree (template_id);


--
-- Name: idx_augment_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_augment_tenant ON public.template_augmentations USING btree (tenant_key);


--
-- Name: idx_config_category; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_config_category ON public.configurations USING btree (category);


--
-- Name: idx_config_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_config_tenant ON public.configurations USING btree (tenant_key);


--
-- Name: idx_interaction_created; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_interaction_created ON public.agent_interactions USING btree (created_at);


--
-- Name: idx_interaction_parent; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_interaction_parent ON public.agent_interactions USING btree (parent_agent_id);


--
-- Name: idx_interaction_project; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_interaction_project ON public.agent_interactions USING btree (project_id);


--
-- Name: idx_interaction_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_interaction_tenant ON public.agent_interactions USING btree (tenant_key);


--
-- Name: idx_interaction_type; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_interaction_type ON public.agent_interactions USING btree (interaction_type);


--
-- Name: idx_job_agent; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_job_agent ON public.jobs USING btree (agent_id);


--
-- Name: idx_job_status; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_job_status ON public.jobs USING btree (status);


--
-- Name: idx_job_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_job_tenant ON public.jobs USING btree (tenant_key);


--
-- Name: idx_message_created; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_message_created ON public.messages USING btree (created_at);


--
-- Name: idx_message_priority; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_message_priority ON public.messages USING btree (priority);


--
-- Name: idx_message_project; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_message_project ON public.messages USING btree (project_id);


--
-- Name: idx_message_status; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_message_status ON public.messages USING btree (status);


--
-- Name: idx_message_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_message_tenant ON public.messages USING btree (tenant_key);


--
-- Name: idx_product_config_data_gin; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_product_config_data_gin ON public.products USING gin (config_data);


--
-- Name: idx_product_name; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_product_name ON public.products USING btree (name);


--
-- Name: idx_product_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_product_tenant ON public.products USING btree (tenant_key);


--
-- Name: idx_project_alias_unique; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE UNIQUE INDEX idx_project_alias_unique ON public.projects USING btree (alias);


--
-- Name: idx_project_status; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_project_status ON public.projects USING btree (status);


--
-- Name: idx_project_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_project_tenant ON public.projects USING btree (tenant_key);


--
-- Name: idx_session_project; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_session_project ON public.sessions USING btree (project_id);


--
-- Name: idx_session_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_session_tenant ON public.sessions USING btree (tenant_key);


--
-- Name: idx_setup_completed; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_setup_completed ON public.setup_state USING btree (completed);


--
-- Name: idx_setup_features_gin; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_setup_features_gin ON public.setup_state USING gin (features_configured);


--
-- Name: idx_setup_incomplete; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_setup_incomplete ON public.setup_state USING btree (tenant_key, completed) WHERE (completed = false);


--
-- Name: idx_setup_mode; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_setup_mode ON public.setup_state USING btree (install_mode);


--
-- Name: idx_setup_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_setup_tenant ON public.setup_state USING btree (tenant_key);


--
-- Name: idx_setup_tools_gin; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_setup_tools_gin ON public.setup_state USING gin (tools_enabled);


--
-- Name: idx_task_assigned; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_assigned ON public.tasks USING btree (assigned_agent_id);


--
-- Name: idx_task_assigned_to_user; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_assigned_to_user ON public.tasks USING btree (assigned_to_user_id);


--
-- Name: idx_task_converted_to_project; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_converted_to_project ON public.tasks USING btree (converted_to_project_id);


--
-- Name: idx_task_created_by_user; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_created_by_user ON public.tasks USING btree (created_by_user_id);


--
-- Name: idx_task_priority; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_priority ON public.tasks USING btree (priority);


--
-- Name: idx_task_product; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_product ON public.tasks USING btree (product_id);


--
-- Name: idx_task_project; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_project ON public.tasks USING btree (project_id);


--
-- Name: idx_task_status; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_status ON public.tasks USING btree (status);


--
-- Name: idx_task_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_tenant ON public.tasks USING btree (tenant_key);


--
-- Name: idx_task_tenant_assigned_user; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_tenant_assigned_user ON public.tasks USING btree (tenant_key, assigned_to_user_id);


--
-- Name: idx_task_tenant_created_user; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_task_tenant_created_user ON public.tasks USING btree (tenant_key, created_by_user_id);


--
-- Name: idx_template_active; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_template_active ON public.agent_templates USING btree (is_active);


--
-- Name: idx_template_category; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_template_category ON public.agent_templates USING btree (category);


--
-- Name: idx_template_product; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_template_product ON public.agent_templates USING btree (product_id);


--
-- Name: idx_template_role; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_template_role ON public.agent_templates USING btree (role);


--
-- Name: idx_template_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_template_tenant ON public.agent_templates USING btree (tenant_key);


--
-- Name: idx_usage_date; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_usage_date ON public.template_usage_stats USING btree (used_at);


--
-- Name: idx_usage_project; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_usage_project ON public.template_usage_stats USING btree (project_id);


--
-- Name: idx_usage_template; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_usage_template ON public.template_usage_stats USING btree (template_id);


--
-- Name: idx_usage_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_usage_tenant ON public.template_usage_stats USING btree (tenant_key);


--
-- Name: idx_user_active; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_user_active ON public.users USING btree (is_active);


--
-- Name: idx_user_email; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_user_email ON public.users USING btree (email);


--
-- Name: idx_user_field_priority_config_gin; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_user_field_priority_config_gin ON public.users USING gin (field_priority_config);


--
-- Name: idx_user_system; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_user_system ON public.users USING btree (is_system_user);


--
-- Name: idx_user_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_user_tenant ON public.users USING btree (tenant_key);


--
-- Name: idx_user_username; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_user_username ON public.users USING btree (username);


--
-- Name: idx_vision_document; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_vision_document ON public.visions USING btree (document_name);


--
-- Name: idx_vision_project; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_vision_project ON public.visions USING btree (project_id);


--
-- Name: idx_vision_tenant; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX idx_vision_tenant ON public.visions USING btree (tenant_key);


--
-- Name: ix_api_keys_key_hash; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE UNIQUE INDEX ix_api_keys_key_hash ON public.api_keys USING btree (key_hash);


--
-- Name: ix_api_keys_tenant_key; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX ix_api_keys_tenant_key ON public.api_keys USING btree (tenant_key);


--
-- Name: ix_products_tenant_key; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX ix_products_tenant_key ON public.products USING btree (tenant_key);


--
-- Name: ix_setup_state_completed; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX ix_setup_state_completed ON public.setup_state USING btree (completed);


--
-- Name: ix_setup_state_tenant_key; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE UNIQUE INDEX ix_setup_state_tenant_key ON public.setup_state USING btree (tenant_key);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_tenant_key; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE INDEX ix_users_tenant_key ON public.users USING btree (tenant_key);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: giljo_user
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: agent_interactions agent_interactions_parent_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.agent_interactions
    ADD CONSTRAINT agent_interactions_parent_agent_id_fkey FOREIGN KEY (parent_agent_id) REFERENCES public.agents(id);


--
-- Name: agent_interactions agent_interactions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.agent_interactions
    ADD CONSTRAINT agent_interactions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: agents agents_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.agents
    ADD CONSTRAINT agents_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: api_keys api_keys_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.api_keys
    ADD CONSTRAINT api_keys_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: configurations configurations_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.configurations
    ADD CONSTRAINT configurations_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: tasks fk_task_assigned_to_user; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT fk_task_assigned_to_user FOREIGN KEY (assigned_to_user_id) REFERENCES public.users(id);


--
-- Name: tasks fk_task_created_by_user; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT fk_task_created_by_user FOREIGN KEY (created_by_user_id) REFERENCES public.users(id);


--
-- Name: jobs jobs_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.jobs
    ADD CONSTRAINT jobs_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id);


--
-- Name: messages messages_from_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_from_agent_id_fkey FOREIGN KEY (from_agent_id) REFERENCES public.agents(id);


--
-- Name: messages messages_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: projects projects_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.projects
    ADD CONSTRAINT projects_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: sessions sessions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.sessions
    ADD CONSTRAINT sessions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: tasks tasks_assigned_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_assigned_agent_id_fkey FOREIGN KEY (assigned_agent_id) REFERENCES public.agents(id);


--
-- Name: tasks tasks_converted_to_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_converted_to_project_id_fkey FOREIGN KEY (converted_to_project_id) REFERENCES public.projects(id);


--
-- Name: tasks tasks_parent_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_parent_task_id_fkey FOREIGN KEY (parent_task_id) REFERENCES public.tasks(id);


--
-- Name: tasks tasks_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: tasks tasks_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.tasks
    ADD CONSTRAINT tasks_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: template_archives template_archives_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.template_archives
    ADD CONSTRAINT template_archives_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.agent_templates(id);


--
-- Name: template_augmentations template_augmentations_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.template_augmentations
    ADD CONSTRAINT template_augmentations_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.agent_templates(id);


--
-- Name: template_usage_stats template_usage_stats_agent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.template_usage_stats
    ADD CONSTRAINT template_usage_stats_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES public.agents(id);


--
-- Name: template_usage_stats template_usage_stats_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.template_usage_stats
    ADD CONSTRAINT template_usage_stats_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: template_usage_stats template_usage_stats_template_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.template_usage_stats
    ADD CONSTRAINT template_usage_stats_template_id_fkey FOREIGN KEY (template_id) REFERENCES public.agent_templates(id);


--
-- Name: visions visions_project_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: giljo_user
--

ALTER TABLE ONLY public.visions
    ADD CONSTRAINT visions_project_id_fkey FOREIGN KEY (project_id) REFERENCES public.projects(id);


--
-- Name: SCHEMA public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE USAGE ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO giljo_owner;
GRANT ALL ON SCHEMA public TO giljo_user;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: giljo_owner
--

ALTER DEFAULT PRIVILEGES FOR ROLE giljo_owner IN SCHEMA public GRANT SELECT,USAGE ON SEQUENCES TO giljo_user;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: giljo_owner
--

ALTER DEFAULT PRIVILEGES FOR ROLE giljo_owner IN SCHEMA public GRANT SELECT,INSERT,DELETE,UPDATE ON TABLES TO giljo_user;


--
-- PostgreSQL database dump complete
--

