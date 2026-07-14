/**
 * src/components/ModelSelector.test.tsx
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ModelSelector from './ModelSelector';
import { makeModelList } from '@/test/fixtures';

describe('ModelSelector', () => {
  it('renders testid', () => {
    render(<ModelSelector value="efficientnet" onChange={vi.fn()} />);
    expect(screen.getByTestId('model-selector')).toBeInTheDocument();
  });

  it('renders label', () => {
    render(<ModelSelector value="efficientnet" onChange={vi.fn()} label="Architecture" />);
    expect(screen.getByText('Architecture')).toBeInTheDocument();
  });

  it('renders all four architectures as options', () => {
    render(<ModelSelector value="efficientnet" onChange={vi.fn()} />);
    const select = screen.getByRole('combobox');
    const options = Array.from(select.querySelectorAll('option'));
    const names = options.map((o) => o.value);
    expect(names).toContain('cnn');
    expect(names).toContain('vgg16');
    expect(names).toContain('resnet50');
    expect(names).toContain('efficientnet');
  });

  it('calls onChange with new value on change', () => {
    const onChange = vi.fn();
    render(<ModelSelector value="efficientnet" onChange={onChange} />);
    fireEvent.change(screen.getByRole('combobox'), { target: { value: 'resnet50' } });
    expect(onChange).toHaveBeenCalledWith('resnet50');
  });

  it('marks unavailable models as disabled when models prop given', () => {
    const models = makeModelList(); // only efficientnet available
    render(<ModelSelector value="efficientnet" onChange={vi.fn()} models={models} />);
    const select = screen.getByRole('combobox');
    const cnnOpt = Array.from(select.querySelectorAll('option')).find((o) => o.value === 'cnn');
    expect(cnnOpt?.disabled).toBe(true);
  });

  it('is disabled when disabled=true', () => {
    render(<ModelSelector value="efficientnet" onChange={vi.fn()} disabled />);
    expect(screen.getByRole('combobox')).toBeDisabled();
  });

  it('shows current value as selected', () => {
    render(<ModelSelector value="resnet50" onChange={vi.fn()} />);
    expect((screen.getByRole('combobox') as HTMLSelectElement).value).toBe('resnet50');
  });
});
