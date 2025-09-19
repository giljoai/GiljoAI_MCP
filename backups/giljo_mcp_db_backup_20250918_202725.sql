--
-- PostgreSQL database dump
--

\restrict y36y7dXsDZofmukYeWbkQyWkfKIzqgXcn4rhtM5ufDuOo6PnQOq929Faq1Siwxs

-- Dumped from database version 15.14
-- Dumped by pg_dump version 15.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: giljo_mcp; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA giljo_mcp;


ALTER SCHEMA giljo_mcp OWNER TO postgres;

--
-- Name: pg_stat_statements; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_stat_statements WITH SCHEMA public;


--
-- Name: EXTENSION pg_stat_statements; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pg_stat_statements IS 'track planning and execution statistics of all SQL statements executed';


--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: agent_status; Type: TYPE; Schema: giljo_mcp; Owner: postgres
--

CREATE TYPE giljo_mcp.agent_status AS ENUM (
    'idle',
    'working',
    'handoff',
    'completed',
    'error'
);


ALTER TYPE giljo_mcp.agent_status OWNER TO postgres;

--
-- Name: message_priority; Type: TYPE; Schema: giljo_mcp; Owner: postgres
--

CREATE TYPE giljo_mcp.message_priority AS ENUM (
    'low',
    'normal',
    'high',
    'critical'
);


ALTER TYPE giljo_mcp.message_priority OWNER TO postgres;

--
-- Name: message_status; Type: TYPE; Schema: giljo_mcp; Owner: postgres
--

CREATE TYPE giljo_mcp.message_status AS ENUM (
    'pending',
    'acknowledged',
    'processing',
    'completed',
    'failed'
);


ALTER TYPE giljo_mcp.message_status OWNER TO postgres;

--
-- Name: project_status; Type: TYPE; Schema: giljo_mcp; Owner: postgres
--

CREATE TYPE giljo_mcp.project_status AS ENUM (
    'active',
    'paused',
    'completed',
    'archived'
);


ALTER TYPE giljo_mcp.project_status OWNER TO postgres;

--
-- Name: task_status; Type: TYPE; Schema: giljo_mcp; Owner: postgres
--

CREATE TYPE giljo_mcp.task_status AS ENUM (
    'pending',
    'in_progress',
    'completed',
    'failed',
    'cancelled'
);


ALTER TYPE giljo_mcp.task_status OWNER TO postgres;

--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: giljo_mcp; Owner: postgres
--

CREATE FUNCTION giljo_mcp.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


ALTER FUNCTION giljo_mcp.update_updated_at_column() OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: agents; Type: TABLE; Schema: giljo_mcp; Owner: postgres
--

CREATE TABLE giljo_mcp.agents (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    project_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    role character varying(100),
    status giljo_mcp.agent_status DEFAULT 'idle'::giljo_mcp.agent_status,
    context_used integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    last_active timestamp with time zone,
    metadata jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT check_agent_context CHECK ((context_used >= 0))
);


ALTER TABLE giljo_mcp.agents OWNER TO postgres;

--
-- Name: configurations; Type: TABLE; Schema: giljo_mcp; Owner: postgres
--

CREATE TABLE giljo_mcp.configurations (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    key character varying(255) NOT NULL,
    value jsonb NOT NULL,
    category character varying(100),
    description text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE giljo_mcp.configurations OWNER TO postgres;

--
-- Name: messages; Type: TABLE; Schema: giljo_mcp; Owner: postgres
--

CREATE TABLE giljo_mcp.messages (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    project_id uuid NOT NULL,
    from_agent character varying(255),
    to_agents text[],
    content text NOT NULL,
    message_type character varying(50) DEFAULT 'direct'::character varying,
    priority giljo_mcp.message_priority DEFAULT 'normal'::giljo_mcp.message_priority,
    status giljo_mcp.message_status DEFAULT 'pending'::giljo_mcp.message_status,
    acknowledged_by text[],
    completed_by text[],
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at timestamp with time zone,
    completed_at timestamp with time zone,
    metadata jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE giljo_mcp.messages OWNER TO postgres;

--
-- Name: projects; Type: TABLE; Schema: giljo_mcp; Owner: postgres
--

CREATE TABLE giljo_mcp.projects (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_key character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    mission text,
    status giljo_mcp.project_status DEFAULT 'active'::giljo_mcp.project_status,
    context_budget integer DEFAULT 150000,
    context_used integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamp with time zone,
    metadata jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT check_context_budget CHECK ((context_budget > 0)),
    CONSTRAINT check_context_used CHECK ((context_used >= 0))
);


ALTER TABLE giljo_mcp.projects OWNER TO postgres;

--
-- Name: sessions; Type: TABLE; Schema: giljo_mcp; Owner: postgres
--

CREATE TABLE giljo_mcp.sessions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    project_id uuid NOT NULL,
    agent_id uuid,
    started_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    ended_at timestamp with time zone,
    context_snapshot jsonb,
    metadata jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE giljo_mcp.sessions OWNER TO postgres;

--
-- Name: tasks; Type: TABLE; Schema: giljo_mcp; Owner: postgres
--

CREATE TABLE giljo_mcp.tasks (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    project_id uuid NOT NULL,
    agent_id uuid,
    title character varying(255) NOT NULL,
    description text,
    status giljo_mcp.task_status DEFAULT 'pending'::giljo_mcp.task_status,
    priority giljo_mcp.message_priority DEFAULT 'normal'::giljo_mcp.message_priority,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    started_at timestamp with time zone,
    completed_at timestamp with time zone,
    metadata jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE giljo_mcp.tasks OWNER TO postgres;

--
-- Name: vision_documents; Type: TABLE; Schema: giljo_mcp; Owner: postgres
--

CREATE TABLE giljo_mcp.vision_documents (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    project_id uuid NOT NULL,
    document_name character varying(255) NOT NULL,
    chunk_index integer NOT NULL,
    total_chunks integer NOT NULL,
    content text NOT NULL,
    token_count integer,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    metadata jsonb DEFAULT '{}'::jsonb
);


ALTER TABLE giljo_mcp.vision_documents OWNER TO postgres;

--
-- Data for Name: agents; Type: TABLE DATA; Schema: giljo_mcp; Owner: postgres
--

COPY giljo_mcp.agents (id, project_id, name, role, status, context_used, created_at, updated_at, last_active, metadata) FROM stdin;
\.


--
-- Data for Name: configurations; Type: TABLE DATA; Schema: giljo_mcp; Owner: postgres
--

COPY giljo_mcp.configurations (id, key, value, category, description, created_at, updated_at) FROM stdin;
dbffb0bb-9066-49ee-a657-d56fc838ae76	system.version	"1.0.0"	system	System version	2025-09-14 17:41:25.610851+00	2025-09-14 17:41:25.610851+00
20398776-e1b8-49cf-957d-eabbe6c65cde	agents.max_per_project	20	agents	Maximum agents per project	2025-09-14 17:41:25.610851+00	2025-09-14 17:41:25.610851+00
620640a8-5f50-41ed-9f77-981a95dccda7	agents.context_limit	150000	agents	Context token limit per agent	2025-09-14 17:41:25.610851+00	2025-09-14 17:41:25.610851+00
31ee659c-201f-451a-b4a6-94b01b3e9d7c	messages.batch_size	10	messages	Message processing batch size	2025-09-14 17:41:25.610851+00	2025-09-14 17:41:25.610851+00
076cab4f-fe8f-47a5-a671-49a86e900a61	vision.chunk_size	20000	vision	Vision document chunk size in tokens	2025-09-14 17:41:25.610851+00	2025-09-14 17:41:25.610851+00
\.


--
-- Data for Name: messages; Type: TABLE DATA; Schema: giljo_mcp; Owner: postgres
--

COPY giljo_mcp.messages (id, project_id, from_agent, to_agents, content, message_type, priority, status, acknowledged_by, completed_by, created_at, acknowledged_at, completed_at, metadata) FROM stdin;
\.


--
-- Data for Name: projects; Type: TABLE DATA; Schema: giljo_mcp; Owner: postgres
--

COPY giljo_mcp.projects (id, tenant_key, name, mission, status, context_budget, context_used, created_at, updated_at, completed_at, metadata) FROM stdin;
\.


--
-- Data for Name: sessions; Type: TABLE DATA; Schema: giljo_mcp; Owner: postgres
--

COPY giljo_mcp.sessions (id, project_id, agent_id, started_at, ended_at, context_snapshot, metadata) FROM stdin;
\.


--
-- Data for Name: tasks; Type: TABLE DATA; Schema: giljo_mcp; Owner: postgres
--

COPY giljo_mcp.tasks (id, project_id, agent_id, title, description, status, priority, created_at, updated_at, started_at, completed_at, metadata) FROM stdin;
\.


--
-- Data for Name: vision_documents; Type: TABLE DATA; Schema: giljo_mcp; Owner: postgres
--

COPY giljo_mcp.vision_documents (id, project_id, document_name, chunk_index, total_chunks, content, token_count, created_at, metadata) FROM stdin;
\.


--
-- Name: agents agents_pkey; Type: CONSTRAINT; Schema: giljo_mcp; Owner: postgres
--

ALTER TABLE ONLY giljo_mcp.agents
    ADD CONSTRAINT agents_pkey PRIMARY KEY (id);


--
-- Name: agents agents_project_id_name_key; Type: CONSTRAINT; Schema: giljo_mcp; Owner: postgres
--

ALTER TABLE ONLY giljo_mcp.agents
    ADD CONSTRAINT agents_project_id_name_key UNIQUE (project_id, name);


--
-- Name: configurations configurations_key_key; Type: CONSTRAINT; Schema: giljo_mcp; Owner: postgres
--

ALTER TABLE ONLY giljo_mcp.configurations
    ADD CONSTRAINT configurations_key_key UNIQUE (key);


--
-- Name: configurations configurations_pkey; Type: CONSTRAINT; Schema: giljo_mcp; Owner: postgres
--

ALTER TABLE ONLY giljo_mcp.configurations
    ADD CONSTRAINT configurations_pkey PRIMARY KEY (id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: giljo_mcp; Owner: postgres
--

ALTER TABLE ONLY giljo_mcp.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id);


--
-- Name: projects projects_pkey; Type: CONSTRAINT; Schema: giljo_mcp; Owner: postgres
--

ALTER TABLE ONLY giljo_mcp.projects
    ADD CONSTRAINT projects_pkey PRIMARY KEY (id);


--
-- Name: projects projects_tenant_key_key; Type: CONSTRAINT; Schema: giljo_mcp; Owner: postgres
--

ALTER TABLE ONLY giljo_mcp.projects
    ADD CONSTRAINT projects_tenant_key_key UNIQUE (tenant_key);


--
-- Name: sessions sessions_pkey; Type: CONSTRAINT; Schema: giljo_mcp; Owner: postgres
--

ALTER TABLE ONLY giljo_mcp.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (id);


--
-- Name: tasks tasks_pkey; Type: CONSTRAINT; Schema: giljo_mcp; Owner: postgres
--

ALTER TABLE ONLY giljo_mcp.tasks
    ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);


--
-- Name: vision_documents vision_documents_pkey; Type: CONSTRAINT; Schema: giljo_mcp; Owner: postgres
--

ALTER TABLE ONLY giljo_mcp.vision_documents
    ADD CONSTRAINT vision_documents_pkey PRIMARY KEY (id);


--
-- Name: vision_documents vision_documents_project_id_document_name_chunk_index_key; Type: CONSTRAINT; Schema: giljo_mcp; Owner: postgres
--

ALTER TABLE ONLY giljo_mcp.vision_documents
    ADD CONSTRAINT vision_documents_project_id_document_name_chunk_index_key UNIQUE (project_id, document_name, chunk_index);


--
-- Name: idx_agents_last_active; Type: INDEX; Schema: giljo_mcp; Owner: postgres
--

CREATE INDEX idx_agents_last_active ON giljo_mcp.agents USING btree (last_active DESC);


--
-- Name: idx_agents_project_id; Type: INDEX; Schema: giljo_mcp; Owner: postgres
--

CREATE INDEX idx_agents_project_id ON giljo_mcp.agents USING btree (project_id);


--
-- Name: idx_agents_status; Type: INDEX; Schema: giljo_mcp; Owner: postgres
--

CREATE INDEX idx_agents_status ON giljo_mcp.agents USING btree (status);


--
-- Name: idx_messages_created_at; Type: INDEX; Schema: giljo_mcp; Owner: postgres
--

CREATE INDEX idx_messages_created_at ON giljo_mcp.messages USING btree (created_at DESC);


--
-- Name: idx_messages_priority; Type: INDEX; Schema: giljo_mcp; Owner: postgres
--

CREATE INDEX idx_messages_priority ON giljo_mcp.messages USING btree (priority);


--
-- Name: idx_messages_project_id; Type: INDEX; Schema: giljo_mcp; Owner: postgres
--

CREATE INDEX idx_messages_project_id ON giljo_mcp.messages USING btree (project_id);


--
-- Name: idx_messages_status; Type: INDEX; Schema: giljo_mcp; Owner: postgres
--

CREATE INDEX idx_messages_status ON giljo_mcp.messages USING btree (status);


--
-- Name: idx_messages_to_agents; Type: INDEX; Schema: giljo_mcp; Owner: postgres
--

CREATE INDEX idx_messages_to_agents ON giljo_mcp.messages USING gin (to_agents);


--
-- Name: idx_projects_created_at; Type: INDEX; Schema: giljo_mcp; Owner: postgres
--

CREATE INDEX idx_projects_created_at ON giljo_mcp.projects USING btree (created_at DESC);


--
-- Name: idx_projects_status; Type: INDEX; Schema: giljo_mcp; Owner: postgres
--

CREATE INDEX idx_projects_status ON giljo_mcp.projects USING btree (status);


--
-- Name: idx_projects_tenant_key; Type: INDEX; Schema: giljo_mcp; Owner: postgres
--

CREATE INDEX idx_projects_tenant_key ON giljo_mcp.projects USING btree (tenant_key);


--
-- Name: idx_sessions_agent_id; Type: INDEX; Schema: giljo_mcp; Owner: postgres
--

CREATE INDEX idx_sessions_agent_id ON giljo_mcp.sessions USING btree (agent_id);


--
-- Name: idx_sessions_project_id; Type: INDEX; Schema: giljo_mcp; Owner: postgres
--

CREATE INDEX idx_sessions_project_id ON giljo_mcp.sessions USING btree (project_id);


--
-- Name: idx_tasks_agent_id; Type: INDEX; Schema: giljo_mcp; Owner: postgres
--

CREATE INDEX idx_tasks_agent_id ON giljo_mcp.tasks USING btree (agent_id);


--
-- Name: idx_tasks_priority; Type: INDEX; Schema: giljo_mcp; Owner: postgres
--

CREATE INDEX idx_tasks_priority ON giljo_mcp.tasks USING btree (priority);


--
-- Name: idx_tasks_project_id; Type: INDEX; Schema: giljo_mcp; Owner: postgres
--

CREATE INDEX idx_tasks_project_id ON giljo_mcp.tasks USING btree (project_id);


--
-- Name: idx_tasks_status; Type: INDEX; Schema: giljo_mcp; Owner: postgres
--

CREATE INDEX idx_tasks_status ON giljo_mcp.tasks USING btree (status);


--
-- Name: idx_vision_project_doc; Type: INDEX; Schema: giljo_mcp; Owner: postgres
--

CREATE INDEX idx_vision_project_doc ON giljo_mcp.vision_documents USING btree (project_id, document_name);


--
-- Name: agents update_agents_updated_at; Type: TRIGGER; Schema: giljo_mcp; Owner: postgres
--

CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON giljo_mcp.agents FOR EACH ROW EXECUTE FUNCTION giljo_mcp.update_updated_at_column();


--
-- Name: configurations update_configurations_updated_at; Type: TRIGGER; Schema: giljo_mcp; Owner: postgres
--

CREATE TRIGGER update_configurations_updated_at BEFORE UPDATE ON giljo_mcp.configurations FOR EACH ROW EXECUTE FUNCTION giljo_mcp.update_updated_at_column();


--
-- Name: projects update_projects_updated_at; Type: TRIGGER; Schema: giljo_mcp; Owner: postgres
--

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON giljo_mcp.projects FOR EACH ROW EXECUTE FUNCTION giljo_mcp.update_updated_at_column();


--
-- Name: tasks update_tasks_updated_at; Type: TRIGGER; Schema: giljo_mcp; Owner: postgres
--

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON giljo_mcp.tasks FOR EACH ROW EXECUTE FUNCTION giljo_mcp.update_updated_at_column();


--
-- Name: agents agents_project_id_fkey; Type: FK CONSTRAINT; Schema: giljo_mcp; Owner: postgres
--

ALTER TABLE ONLY giljo_mcp.agents
    ADD CONSTRAINT agents_project_id_fkey FOREIGN KEY (project_id) REFERENCES giljo_mcp.projects(id) ON DELETE CASCADE;


--
-- Name: messages messages_project_id_fkey; Type: FK CONSTRAINT; Schema: giljo_mcp; Owner: postgres
--

ALTER TABLE ONLY giljo_mcp.messages
    ADD CONSTRAINT messages_project_id_fkey FOREIGN KEY (project_id) REFERENCES giljo_mcp.projects(id) ON DELETE CASCADE;


--
-- Name: sessions sessions_agent_id_fkey; Type: FK CONSTRAINT; Schema: giljo_mcp; Owner: postgres
--

ALTER TABLE ONLY giljo_mcp.sessions
    ADD CONSTRAINT sessions_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES giljo_mcp.agents(id) ON DELETE SET NULL;


--
-- Name: sessions sessions_project_id_fkey; Type: FK CONSTRAINT; Schema: giljo_mcp; Owner: postgres
--

ALTER TABLE ONLY giljo_mcp.sessions
    ADD CONSTRAINT sessions_project_id_fkey FOREIGN KEY (project_id) REFERENCES giljo_mcp.projects(id) ON DELETE CASCADE;


--
-- Name: tasks tasks_agent_id_fkey; Type: FK CONSTRAINT; Schema: giljo_mcp; Owner: postgres
--

ALTER TABLE ONLY giljo_mcp.tasks
    ADD CONSTRAINT tasks_agent_id_fkey FOREIGN KEY (agent_id) REFERENCES giljo_mcp.agents(id) ON DELETE SET NULL;


--
-- Name: tasks tasks_project_id_fkey; Type: FK CONSTRAINT; Schema: giljo_mcp; Owner: postgres
--

ALTER TABLE ONLY giljo_mcp.tasks
    ADD CONSTRAINT tasks_project_id_fkey FOREIGN KEY (project_id) REFERENCES giljo_mcp.projects(id) ON DELETE CASCADE;


--
-- Name: vision_documents vision_documents_project_id_fkey; Type: FK CONSTRAINT; Schema: giljo_mcp; Owner: postgres
--

ALTER TABLE ONLY giljo_mcp.vision_documents
    ADD CONSTRAINT vision_documents_project_id_fkey FOREIGN KEY (project_id) REFERENCES giljo_mcp.projects(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict y36y7dXsDZofmukYeWbkQyWkfKIzqgXcn4rhtM5ufDuOo6PnQOq929Faq1Siwxs

