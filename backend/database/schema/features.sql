-- features.sql
-- Stores the 7 GLCM texture features extracted per image
-- Features are computed from Equations 8–14 of the paper
--
-- Columns:
--   id          TEXT PRIMARY KEY — UUID
--   image_id    TEXT NOT NULL    — FK → images.id
--   entropy     REAL             — Eq. 8:  Σ T_xy * log(T_xy)
--   correlation REAL             — Eq. 9:  (x,y)*t(x,y) - μi*μj / σi*σj
--   energy      REAL             — Eq. 10: Σ T²_xy
--   contrast    REAL             — Eq. 11: Σ m² * Σ T(x,y)²
--   mean        REAL             — Eq. 12: Σ x * t(x)
--   std_dev     REAL             — Eq. 13: sqrt(Σ (x-μ)² * t(x))
--   variance    REAL             — Eq. 14: Σ (x-μ) * t(x)
--   created_at  TEXT NOT NULL    — ISO 8601 timestamp

CREATE TABLE IF NOT EXISTS features (
  id          TEXT PRIMARY KEY,
  image_id    TEXT NOT NULL,
  entropy     REAL,
  correlation REAL,
  energy      REAL,
  contrast    REAL,
  mean        REAL,
  std_dev     REAL,
  variance    REAL,
  created_at  TEXT NOT NULL,
  FOREIGN KEY (image_id) REFERENCES images(id)
);
