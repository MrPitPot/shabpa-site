-- Public ratings from the Shabpa app. Only a SHA-256 of a random install id is kept (never an IP address or a user agent).
CREATE TABLE IF NOT EXISTS ratings (
  id_hash TEXT PRIMARY KEY,
  stars INTEGER NOT NULL CHECK (stars BETWEEN 1 AND 5),
  app_version TEXT,
  lang TEXT,
  created_at TEXT,
  updated_at TEXT
);

-- Flood control: a counter per (hash of IP and hour). The raw address is never stored; rows older than a day are deleted.
CREATE TABLE IF NOT EXISTS rate_limits (
  k TEXT PRIMARY KEY,
  n INTEGER NOT NULL DEFAULT 0,
  hour INTEGER NOT NULL
);
