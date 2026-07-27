-- Part 2: Run in pgAdmin Query Tool while connected to the "study_space_finder" database as user "postgres".

GRANT ALL ON SCHEMA public TO studyspace_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO studyspace_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO studyspace_user;
