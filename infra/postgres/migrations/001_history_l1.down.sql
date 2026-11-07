-- ONLY against disposable CI database. Destructive schema rollback; never run on real data.
DROP SCHEMA history_l1 CASCADE;
