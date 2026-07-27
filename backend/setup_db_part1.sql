-- Part 1: Run in pgAdmin Query Tool while connected to the "postgres" database as user "postgres".

CREATE DATABASE study_space_finder;

CREATE USER studyspace_user WITH PASSWORD 'studyspace_dev_password';

GRANT ALL PRIVILEGES ON DATABASE study_space_finder TO studyspace_user;
