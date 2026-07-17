/**
 * src/components/GradCAMViewer.test.tsx
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import GradCAMViewer from './GradCAMViewer';

describe('GradCAMViewer', () => {
  it('shows placeholder when gradcamPath is null', () => {
    render(<GradCAMViewer gradcamPath={null} />);
    expect(screen.getByText(/grad-cam not generated/i)).toBeInTheDocument();
  });

  it('shows placeholder when gradcamPath is undefined', () => {
    render(<GradCAMViewer gradcamPath={undefined} />);
    expect(screen.getByText(/grad-cam not generated/i)).toBeInTheDocument();
  });

  it('renders image when gradcamPath is provided', () => {
    render(<GradCAMViewer gradcamPath="/path/to/overlay.png" />);
    expect(screen.getByTestId('gradcam-viewer')).toBeInTheDocument();
    const img = screen.getByRole('img', { name: /heatmap/i });
    expect(img).toBeInTheDocument();
  });

  it('renders original image when originalSrc is provided', () => {
    render(<GradCAMViewer gradcamPath="/overlay.png" originalSrc="data:image/png;base64,abc" />);
    const images = screen.getAllByRole('img');
    expect(images.length).toBeGreaterThanOrEqual(2);
  });

  it('renders label heading when path provided', () => {
    render(<GradCAMViewer gradcamPath="/overlay.png" />);
    expect(screen.getByText(/grad-cam heatmap/i)).toBeInTheDocument();
  });
});
