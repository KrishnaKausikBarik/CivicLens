-- Restrict password-reset storage to the Flask database connection.
-- RLS with no policies denies Data API roles. The backend connects with its
-- server-side PostgreSQL role and continues to use the ORM as before.
ALTER TABLE public.password_reset_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.password_reset_rate_limits ENABLE ROW LEVEL SECURITY;

REVOKE ALL PRIVILEGES ON TABLE public.password_reset_tokens,
    public.password_reset_rate_limits
    FROM PUBLIC, anon, authenticated, service_role;

REVOKE ALL PRIVILEGES ON SEQUENCE public.password_reset_tokens_id_seq
    FROM PUBLIC, anon, authenticated, service_role;
