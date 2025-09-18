-- Role Shuffler Bot Database Setup
-- Run this script as a PostgreSQL superuser (usually 'postgres')

-- Create database
CREATE DATABASE role_shuffler;

-- Create user for the bot
CREATE USER bot_user WITH PASSWORD 'change_this_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE role_shuffler TO bot_user;

-- Connect to the database
\c role_shuffler;

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO bot_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO bot_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO bot_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO bot_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO bot_user;

-- Confirm setup
\du bot_user
\l role_shuffler