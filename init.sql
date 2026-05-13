-- Initialize KarigAI database
CREATE DATABASE IF NOT EXISTS karigai;

-- Create user if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'karigai_user') THEN
        CREATE USER karigai_user WITH PASSWORD 'karigai_password';
    END IF;
END
$$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE karigai TO karigai_user;

-- Connect to karigai database
\c karigai;

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO karigai_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO karigai_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO karigai_user;