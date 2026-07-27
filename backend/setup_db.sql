-- Run this in pgAdmin (Query Tool) or SQL Shell while connected as postgres.
-- Replace the password below if you prefer a different one, then match it in .env

CREATE DATABASE study_space_finder;

CREATE USER studyspace_user WITH PASSWORD 'studyspace_dev_password';

GRANT ALL PRIVILEGES ON DATABASE study_space_finder TO studyspace_user;

-- PostgreSQL 15+ requires explicit schema grants
\c study_space_finder
GRANT ALL ON SCHEMA public TO studyspace_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO studyspace_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO studyspace_user;
