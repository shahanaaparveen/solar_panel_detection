/**
 * Genuine frontend coordinate and polygon utilities for backend-detected panels.
 * Fixed geometric panel grids and client-side simulated detections have been removed;
 * all panel geometry originates strictly from backend model inference and clustering.
 */

export function formatPolygonPoints(geometry) {
  if (!Array.isArray(geometry) || geometry.length < 3) return '';
  return geometry
    .map(pt => (Array.isArray(pt) && pt.length >= 2 ? `${Number(pt[0])},${Number(pt[1])}` : null))
    .filter(Boolean)
    .join(' ');
}

export function formatGridCoordinate(panel) {
  if (!panel) return '—';
  const row = panel.row_label || (panel.row_id != null ? `R-${String(panel.row_id).padStart(2, '0')}` : null);
  const col = panel.column_label || (panel.column_id != null ? `C-${String(panel.column_id).padStart(2, '0')}` : null);
  if (row && col) return `${row} · ${col}`;
  return panel.panel_id || '—';
}

export function getPanelVisualStyle(panel, { isSelected = false, findingsForPanel = [] } = {}) {
  if (isSelected) {
    return {
      fill: 'rgba(16, 185, 129, 0.32)',
      stroke: '#34d399',
    };
  }
  const hasHigh = findingsForPanel.some(f => (f.inspectionPriority || f.inspection_priority) === 'High');
  const hasAny = findingsForPanel.length > 0;
  if (hasHigh) {
    return {
      fill: 'rgba(239, 68, 68, 0.22)',
      stroke: '#f87171',
    };
  }
  if (hasAny) {
    return {
      fill: 'rgba(245, 158, 11, 0.22)',
      stroke: '#fbbf24',
    };
  }
  if (panel?.is_partial) {
    return {
      fill: 'rgba(148, 163, 184, 0.16)',
      stroke: '#94a3b8',
    };
  }
  return {
    fill: 'rgba(99, 102, 241, 0.14)',
    stroke: '#a5b4fc',
  };
}
