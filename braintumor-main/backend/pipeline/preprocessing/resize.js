'use strict';

/**
 * resize.js — Image Resizing Module
 *
 * Resizes all MRI images to a uniform 256×256 dimension before preprocessing.
 * The Kaggle dataset contains images of varying sizes; consistent dimensions
 * are required for GLCM computation and EDN-SVM classification.
 *
 * Target dimensions: 256×256 (config.image.targetWidth / targetHeight)
 * Library: Jimp v0.22 (already a project dependency)
 * Interpolation: bilinear (Jimp default — RESIZE_BILINEAR)
 *
 * Output format: PNG (lossless, preserves full 8-bit intensity range for ACEA)
 */

const Jimp   = require('jimp');
const path   = require('path');
const config = require('../../config');
const { ensureDirectoryExists, generateOutputPath } = require('../../utils/imageUtils');
const logger = require('../../utils/logger');

const TARGET_W = config.image.targetWidth;   // 256
const TARGET_H = config.image.targetHeight;  // 256

/**
 * Resize an MRI image to TARGET_W × TARGET_H and save as PNG.
 *
 * @param {string} inputPath  - Absolute path to source image (JPEG or PNG)
 * @param {string} outputPath - Absolute path where the resized PNG is saved
 * @returns {Promise<{ outputPath: string, width: number, height: number }>}
 */
async function resizeImage(inputPath, outputPath) {
  ensureDirectoryExists(path.dirname(outputPath));

  const img = await Jimp.read(inputPath);

  img.resize(TARGET_W, TARGET_H, Jimp.RESIZE_BILINEAR);

  await img.writeAsync(outputPath);

  logger.info(`[RESIZE] ${path.basename(inputPath)} → ${TARGET_W}×${TARGET_H} → ${path.basename(outputPath)}`);

  return { outputPath, width: TARGET_W, height: TARGET_H };
}

/**
 * Convenience wrapper: derives the output path from the imageId
 * using the standard pipeline naming convention.
 *
 * @param {string} imageId   - UUID from images table
 * @param {string} inputPath - Absolute path to uploaded file
 * @returns {Promise<{ outputPath: string, width: number, height: number }>}
 */
async function resizeById(imageId, inputPath) {
  const outputPath = generateOutputPath(imageId, 'resized', 'png');
  return resizeImage(inputPath, outputPath);
}

module.exports = { resizeImage, resizeById };
