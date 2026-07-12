'use strict';

const fs   = require('fs');
const path = require('path');
const config = require('../config');

/**
 * Ensure a directory exists, creating it recursively if needed.
 * Synchronous — safe to call before any file write operation.
 *
 * @param {string} dirPath
 */
function ensureDirectoryExists(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

/**
 * Generate a standardised output file path for a given pipeline stage.
 * Creates the target directory if it does not exist.
 *
 * Stage → directory mapping:
 *  'resized'   → dataset/processed/resized/
 *  'enhanced'  → dataset/processed/enhanced/
 *  'denoised'  → dataset/processed/noise_removed/
 *  'segmented' → dataset/processed/segmented/
 *
 * @param {string} imageId   - UUID of the image
 * @param {string} stage     - 'resized' | 'enhanced' | 'denoised' | 'segmented'
 * @param {string} [ext]     - file extension without dot, default 'png'
 * @returns {string} absolute output path
 */
function generateOutputPath(imageId, stage, ext = 'png') {
  const stageMap = {
    resized:   config.paths.resizedDir,
    enhanced:  config.paths.enhancedDir,
    denoised:  config.paths.denoisedDir,
    segmented: config.paths.segmentedDir,
  };

  const dir = stageMap[stage];
  if (!dir) {
    throw new Error(`Unknown pipeline stage: "${stage}". Must be one of: ${Object.keys(stageMap).join(', ')}`);
  }

  ensureDirectoryExists(dir);
  return path.join(dir, `${imageId}_${stage}.${ext}`);
}

/**
 * Read an image file and return a flat grayscale pixel array.
 * Uses Jimp (loaded lazily to avoid startup cost when not needed).
 *
 * NOTE: Full pixel-level implementation used during pipeline phases.
 *       Returns a stub object in foundation phase.
 *
 * @param {string} imagePath - absolute path to image file
 * @returns {Promise<{ pixels: Uint8Array, width: number, height: number }>}
 */
async function readPixelArray(imagePath) {
  // Jimp loaded lazily — not required at server startup
  const Jimp = require('jimp');
  const image = await Jimp.read(imagePath);
  const { width, height } = image.bitmap;
  const pixels = new Uint8Array(width * height);

  image.scan(0, 0, width, height, function (x, y, idx) {
    // Convert RGBA → grayscale using luminance formula
    const r = this.bitmap.data[idx];
    const g = this.bitmap.data[idx + 1];
    const b = this.bitmap.data[idx + 2];
    pixels[y * width + x] = Math.round(0.299 * r + 0.587 * g + 0.114 * b);
  });

  return { pixels, width, height };
}

/**
 * Write a flat grayscale pixel array back to an image file.
 * Creates a single-channel PNG at the specified output path.
 *
 * @param {Uint8Array} pixels     - flat grayscale pixel array
 * @param {number}     width      - image width
 * @param {number}     height     - image height
 * @param {string}     outputPath - absolute path for output file
 * @returns {Promise<void>}
 */
async function writePixelArray(pixels, width, height, outputPath) {
  const Jimp = require('jimp');
  ensureDirectoryExists(path.dirname(outputPath));

  const image = new Jimp(width, height);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const val = pixels[y * width + x];
      // Set RGBA — grayscale so R=G=B=val, A=255
      const pixelColor = Jimp.rgbaToInt(val, val, val, 255);
      image.setPixelColor(pixelColor, x, y);
    }
  }

  ensureDirectoryExists(path.dirname(outputPath));
  await image.writeAsync(outputPath);
}

/**
 * Convert an image file to a base64 data URI for embedding in API responses.
 * Detects MIME type from file extension.
 *
 * @param {string} imagePath - absolute path to image
 * @returns {string} base64 data URI  e.g. "data:image/png;base64,..."
 */
function imageToBase64(imagePath) {
  if (!fs.existsSync(imagePath)) {
    throw new Error(`imageToBase64: file not found at ${imagePath}`);
  }
  const ext = path.extname(imagePath).toLowerCase().replace('.', '');
  const mimeMap = { jpg: 'image/jpeg', jpeg: 'image/jpeg', png: 'image/png' };
  const mime = mimeMap[ext] || 'image/png';
  const data = fs.readFileSync(imagePath);
  return `data:${mime};base64,${data.toString('base64')}`;
}

/**
 * Convert an absolute server filesystem path to a relative URL path
 * that can be served as a static asset.
 *
 * e.g. /abs/path/to/uploads/abc.jpg  →  /uploads/abc.jpg
 *
 * @param {string} absolutePath
 * @param {string} baseDir  - the root directory from which URL is relative
 * @returns {string} URL-style relative path
 */
function toStaticUrl(absolutePath, baseDir) {
  const rel = path.relative(baseDir, absolutePath);
  // Normalise Windows backslashes to forward slashes
  return '/' + rel.replace(/\\/g, '/');
}

module.exports = {
  ensureDirectoryExists,
  generateOutputPath,
  readPixelArray,
  writePixelArray,
  imageToBase64,
  toStaticUrl,
};
