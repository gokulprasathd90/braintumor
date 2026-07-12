# MRI Brain Tumor Detection System

## Overview
A full-stack web application for detecting brain tumors from MRI scans using the
EDN-SVM (Ensemble Deep Neural Support Vector Machine) approach described in:

> "MRI brain tumor detection using deep learning and machine learning approaches"
> Anantharajan et al., Measurement: Sensors 31 (2024) 101026

## Pipeline
Raw MRI → Resize → ACEA Preprocessing → Median Filter → FCM Segmentation → GLCM Feature Extraction → EDN-SVM Classification → Result

## Technology Stack
- **Frontend**: React.js + Vite + JavaScript + Tailwind CSS
- **Backend**: Node.js + Express.js
- **Database**: SQLite (better-sqlite3)
- **Image Processing**: Jimp, Sharp, TensorFlow.js
- **API**: REST APIs

## Performance Targets (from paper)
- Accuracy: 97.93%
- Sensitivity: 92%
- Specificity: 98%
- PSNR: 52.98%

## Setup Instructions
<!-- To be completed during implementation phase -->

## Dataset
Download from Kaggle: Brain MRI Images for Brain Tumor Detection
- 255 T1-mode MRI images
- 98 healthy brain slices
- 155 tumorous brain slices

## Usage
<!-- To be completed during implementation phase -->
