-- processedImages.sql
-- Stores file paths for every stage of the preprocessing and segmentation pipeline
--
-- Columns:
--   id              TEXT PRIMARY KEY  — UUID
--   image_id        TEXT NOT NULL     — FK → images.id
--   resized_path    TEXT              — Path after resize.js (256×256)
--   enhanced_path   TEXT              — Path after acea.js (contrast enhanced)
--   denoised_path   TEXT              — Path after medianFilter.js (noise removed)
--   segmented_path  TEXT              — Path after fcm.js (cluster overlay)
--   created_at      TEXT NOT NULL     — ISO 8601 timestamp

CREATE TABLE IF NOT EXISTS processed_images (
  id              TEXT PRIMARY KEY,
  image_id        TEXT NOT NULL,
  resized_path    TEXT,
  enhanced_path   TEXT,
  denoised_path   TEXT,
  segmented_path  TEXT,
  created_at      TEXT NOT NULL,
  FOREIGN KEY (image_id) REFERENCES images(id)
);
