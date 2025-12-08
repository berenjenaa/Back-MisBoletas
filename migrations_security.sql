-- Tabla para almacenar códigos de verificación temporales
-- Estos se usan en lugar de pasar tokens en URLs

CREATE TABLE IF NOT EXISTS auth_codes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code VARCHAR(10) NOT NULL UNIQUE,
  email VARCHAR(255) NOT NULL,
  type VARCHAR(50) NOT NULL, -- 'signup', 'recovery', etc
  access_token TEXT, -- Token asociado (si aplica)
  refresh_token TEXT,
  user_id UUID,
  created_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '10 minutes',
  used_at TIMESTAMP,
  used BOOLEAN DEFAULT FALSE,
  created_by_ip VARCHAR(50)
);

-- Índices para queries frecuentes
CREATE INDEX IF NOT EXISTS idx_auth_codes_code ON auth_codes(code);
CREATE INDEX IF NOT EXISTS idx_auth_codes_email ON auth_codes(email);
CREATE INDEX IF NOT EXISTS idx_auth_codes_expires_at ON auth_codes(expires_at);

-- Policy para que solo el backend acceda (via Service Role)
ALTER TABLE auth_codes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role can manage auth codes"
  ON auth_codes
  FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

-- Función para limpiar códigos expirados (llamar cada hora)
CREATE OR REPLACE FUNCTION cleanup_expired_auth_codes()
RETURNS void AS $$
BEGIN
  DELETE FROM auth_codes WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Comentarios
COMMENT ON TABLE auth_codes IS 'Códigos temporales seguros para verificación de email y reset password. Expiran en 10 minutos.';
COMMENT ON COLUMN auth_codes.code IS 'Código de 6-10 caracteres único';
COMMENT ON COLUMN auth_codes.type IS 'Tipo: signup, recovery, email_verification';
COMMENT ON COLUMN auth_codes.access_token IS 'Token de Supabase (solo para recovery)';
COMMENT ON COLUMN auth_codes.used IS 'Si el código ya fue utilizado';
