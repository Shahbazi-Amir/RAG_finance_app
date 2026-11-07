-- 002_one_attempt.up.sql | fail closed on legacy, never delete/mutate data.
DO $$
BEGIN
 IF EXISTS (
  SELECT 1 FROM history_l1.execution_attempts
  GROUP BY owner_id, send_receipt_id HAVING count(*) > 1
 ) THEN
  RAISE EXCEPTION 'HISTORY_LEGACY_MULTI_ATTEMPT: preserve historical rows and review before migration';
 END IF;
END $$;
CREATE UNIQUE INDEX one_attempt_per_send_receipt
 ON history_l1.execution_attempts(owner_id,send_receipt_id);
