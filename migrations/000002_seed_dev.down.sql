-- AMACTIVE — Rollback do seed de desenvolvimento

BEGIN;

DELETE FROM usuario WHERE email = 'admin@amactive.dev';

COMMIT;
