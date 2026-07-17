-- results.sql
-- Stores the EDN-SVM classification result and all evaluation metrics per image
--
-- Columns:
--   id                  TEXT PRIMARY KEY — UUID
--   image_id            TEXT NOT NULL    — FK → images.id
--   prediction          TEXT NOT NULL    — "normal" | "abnormal"
--   confidence          REAL             — Classifier confidence score [0.0 – 1.0]
--   accuracy            REAL             — Eq. 28: (tp+tn)/(tp+tn+fp+fn)
--   sensitivity         REAL             — Eq. 31: TP/(TP+FN) * 100
--   specificity         REAL             — Eq. 32: TN/(TN+FP) * 100
--   psnr                REAL             — Eq. 30: 10*log10(255²/MSE)
--   jaccard             REAL             — Eq. 29: A∩B / A∪B
--   ber                 REAL             — Bit Error Rate: fp/(fp+tn)
--   computational_time  REAL             — Processing time in milliseconds
--   created_at          TEXT NOT NULL    — ISO 8601 timestamp

CREATE TABLE IF NOT EXISTS results (
  id                  TEXT PRIMARY KEY,
  image_id            TEXT NOT NULL,
  prediction          TEXT NOT NULL,
  confidence          REAL,
  accuracy            REAL,
  sensitivity         REAL,
  specificity         REAL,
  psnr                REAL,
  jaccard             REAL,
  ber                 REAL,
  computational_time  REAL,
  created_at          TEXT NOT NULL,
  FOREIGN KEY (image_id) REFERENCES images(id)
);

-- Stores overall model evaluation metrics from training runs
CREATE TABLE IF NOT EXISTS model_metrics (
  id                  TEXT PRIMARY KEY,
  accuracy            REAL,
  sensitivity         REAL,
  specificity         REAL,
  psnr                REAL,
  jaccard             REAL,
  ber                 REAL,
  computational_time  REAL,
  trained_at          TEXT NOT NULL
);

-- Stores per-model comparison data for /api/compare endpoint
-- Mirrors Figures 9–14 of the paper
CREATE TABLE IF NOT EXISTS comparison_results (
  id                  TEXT PRIMARY KEY,
  model_name          TEXT NOT NULL,
  accuracy            REAL,
  sensitivity         REAL,
  specificity         REAL,
  psnr                REAL,
  jaccard             REAL,
  ber                 REAL,
  computational_time  REAL,
  created_at          TEXT NOT NULL
);
