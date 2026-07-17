-- images.sql
-- Stores metadata for every uploaded MRI image
--
-- Columns:
--   id          TEXT PRIMARY KEY   — UUID generated at upload time
--   filename    TEXT NOT NULL      — Original filename from client
--   raw_path    TEXT NOT NULL      — Absolute path saved by Multer under uploads/
--   upload_time TEXT NOT NULL      — ISO 8601 timestamp of upload

CREATE TABLE IF NOT EXISTS images (
  id          TEXT PRIMARY KEY,
  filename    TEXT NOT NULL,
  raw_path    TEXT NOT NULL,
  upload_time TEXT NOT NULL
);
