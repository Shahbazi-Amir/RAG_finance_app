-- 001_history_l1.up.sql | synthetic-only PostgreSQL 17 L1
-- Migration must run as history_migrator, never the unprivileged app role.
CREATE SCHEMA history_l1;
CREATE TABLE history_l1.conversations (
 owner_id text NOT NULL, id text NOT NULL, title text,
 state text NOT NULL DEFAULT 'active' CHECK (state IN ('active','deletion_requested')),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY (owner_id,id)
);
CREATE INDEX conversation_order_idx ON history_l1.conversations(owner_id,created_at DESC,id DESC) WHERE state='active';
CREATE TABLE history_l1.create_receipts (
 owner_id text NOT NULL, client_conversation_id text NOT NULL, idempotency_key text NOT NULL,
 payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
 conversation_id text NOT NULL, created_snapshot jsonb NOT NULL,
 PRIMARY KEY(owner_id,client_conversation_id,idempotency_key),
 FOREIGN KEY(owner_id,conversation_id) REFERENCES history_l1.conversations(owner_id,id)
);
CREATE TABLE history_l1.messages (
 owner_id text NOT NULL, id text NOT NULL, conversation_id text NOT NULL,
 role text NOT NULL CHECK (role IN ('user','assistant')),
 body text NOT NULL CHECK (length(btrim(body))>0),
 answer_id text,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(owner_id,id), UNIQUE(owner_id,conversation_id,id),
 FOREIGN KEY(owner_id,conversation_id) REFERENCES history_l1.conversations(owner_id,id)
);
CREATE INDEX message_order_idx ON history_l1.messages(owner_id,conversation_id,created_at ASC,id ASC);
CREATE TABLE history_l1.send_receipts (
 id text NOT NULL, owner_id text NOT NULL, requested_conversation_id text,
 resolved_conversation_id text NOT NULL, user_message_id text NOT NULL,
 client_message_id text NOT NULL, idempotency_key text NOT NULL,
 payload_sha256 text NOT NULL CHECK(payload_sha256 ~ '^[0-9a-f]{64}$'),
 initial_request_id text NOT NULL, initial_trace_id text NOT NULL,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(owner_id,id), UNIQUE NULLS NOT DISTINCT(owner_id,requested_conversation_id,client_message_id,idempotency_key),
 FOREIGN KEY(owner_id,resolved_conversation_id) REFERENCES history_l1.conversations(owner_id,id),
 FOREIGN KEY(owner_id,resolved_conversation_id,user_message_id)
  REFERENCES history_l1.messages(owner_id,conversation_id,id)
);
CREATE TABLE history_l1.execution_attempts (
 owner_id text NOT NULL, id text NOT NULL, send_receipt_id text NOT NULL,
 attempt_request_id text NOT NULL, attempt_trace_id text NOT NULL,
 reserved_answer_id text NOT NULL,
 state text NOT NULL DEFAULT 'attempt_pending'
  CHECK(state IN ('attempt_pending','attempt_unknown','answer_committed','failed','cancelled')),
 error_code text,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(owner_id,id), UNIQUE(owner_id,id,reserved_answer_id),
 FOREIGN KEY(owner_id,send_receipt_id) REFERENCES history_l1.send_receipts(owner_id,id)
);
-- UNIQUE(owner_id,send_receipt_id) is installed only in 002 after a
-- fail-closed legacy multi-attempt preflight; never rewrite old rows.
CREATE TABLE history_l1.answers (
 owner_id text NOT NULL, id text NOT NULL, conversation_id text NOT NULL,
 message_id text NOT NULL, attempt_id text NOT NULL,
 payload jsonb NOT NULL CHECK(jsonb_typeof(payload)='object'),
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(owner_id,id), UNIQUE(owner_id,attempt_id), UNIQUE(owner_id,message_id),
 FOREIGN KEY(owner_id,conversation_id,message_id) REFERENCES history_l1.messages(owner_id,conversation_id,id),
 FOREIGN KEY(owner_id,attempt_id,id) REFERENCES history_l1.execution_attempts(owner_id,id,reserved_answer_id)
);
-- Role-based SQL boundary: owned by history_migrator, accessed by history_app.
GRANT USAGE ON SCHEMA history_l1 TO history_app;
-- Immutable history receipts/messages/answers: app may INSERT and READ only.
-- Only mutable conversation metadata and attempt terminal state are UPDATE-able.
GRANT SELECT,INSERT ON ALL TABLES IN SCHEMA history_l1 TO history_app;
GRANT UPDATE(title,state,updated_at) ON history_l1.conversations TO history_app;
GRANT UPDATE(state,error_code) ON history_l1.execution_attempts TO history_app;
DO $$
DECLARE table_name text;
BEGIN
 FOR table_name IN SELECT tablename FROM pg_tables WHERE schemaname='history_l1'
 LOOP
  EXECUTE format('ALTER TABLE history_l1.%I ENABLE ROW LEVEL SECURITY',table_name);
  EXECUTE format('ALTER TABLE history_l1.%I FORCE ROW LEVEL SECURITY',table_name);
  EXECUTE format('CREATE POLICY owner_only ON history_l1.%I FOR ALL TO history_app USING (owner_id = NULLIF(current_setting(''app.owner_id'', true), '''')) WITH CHECK (owner_id = NULLIF(current_setting(''app.owner_id'', true), ''''))',table_name);
 END LOOP;
END $$;
