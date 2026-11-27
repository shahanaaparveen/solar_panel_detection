import { useState, useEffect } from 'react';
import { ArrowRight, ChevronLeft, ChevronRight } from 'lucide-react';
import { formatGridCoordinate, formatPolygonPoints, getPanelVisualStyle } from '../utils/panelDetection';

/**
 * Standalone Panel Mapping view backed strictly by backend model panel results.
 * Never fabricates client-side grid detections when backend detections are unavailable.
 */
export default function PanelMapping({ thermalFiles = [], rgbFiles = [], panelResults = [] }) {
  const [thermalUrls, setThermalUrls] = useState([]);
  const [rgbUrls, setRgbUrls] = useState([]);
  const [thermalIdx, setThermalIdx] = useState(0);
  const [rgbIdx, setRgbIdx] = useState(0);

  useEffect(() => {
    const created = thermalFiles.map(f => URL.createObjectURL(f));
    setThermalUrls(created);
    setThermalIdx(0);
    return () => created.forEach(u => URL.revokeObjectURL(u));
  }, [thermalFiles]);

  useEffect(() => {
    const created = rgbFiles.map(f => URL.createObjectURL(f));
    setRgbUrls(created);
    setRgbIdx(0);
    return () => created.forEach(u => URL.revokeObjectURL(u));
  }, [rgbFiles]);

  const hasThermal = thermalUrls.length > 0;
  const hasRgb = rgbUrls.length > 0;
  const currentResult = panelResults[rgbIdx];
  const currentPanels = currentResult?.status === 'COMPLETED' ? (currentResult.panels || []) : [];
  const totalPanels = panelResults.reduce(
    (sum, row) => sum + (row?.status === 'COMPLETED' ? (row.panels?.length || 0) : 0),
    0
  );
  const width = currentResult?.imageSize?.width || 1000;
  const height = currentResult?.imageSize?.height || 750;

  return (
    <div>
      <div className="topbar">
        <div>
          <div className="page-title">Panel Mapping <span style={{ color: '#6366f1' }}>(Model-Backed)</span></div>
          <div className="page-subtitle">Backend panel detection → PCA row/column clustering → deterministic numbering</div>
        </div>
        <div style={{ background: '#0b1120', padding: '8px 16px', borderRadius: 8, fontSize: 13 }}>
          Measured Accuracy: <strong style={{ color: '#64748b' }}>Unmeasured (no validation ground truth)</strong>
        </div>
      </div>

      <div className="mapping-layout">
        <div className="card" style={{ padding: 14 }}>
          <div className="flex justify-between items-center mb-3">
            <div className="section-title">Thermal Image</div>
            {hasThermal && <span style={{ fontSize: 11, color: '#64748b' }}>{thermalIdx + 1}/{thermalUrls.length}</span>}
          </div>

          {hasThermal ? (
            <>
              <div style={{ position: 'relative', borderRadius: 8, overflow: 'hidden', background: '#000' }}>
                <img src={thermalUrls[thermalIdx]} alt="" style={{ width: '100%', height: 260, objectFit: 'contain', display: 'block' }} />
              </div>
              <div className="flex justify-between items-center mt-3">
                <button className="btn btn-outline" style={{ padding: '4px 10px', fontSize: 11 }} disabled={thermalIdx === 0} onClick={() => setThermalIdx(i => i - 1)}>
                  <ChevronLeft size={12} /> Prev
                </button>
                <span style={{ fontSize: 11, color: '#64748b', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {thermalFiles[thermalIdx]?.name}
                </span>
                <button className="btn btn-outline" style={{ padding: '4px 10px', fontSize: 11 }} disabled={thermalIdx === thermalUrls.length - 1} onClick={() => setThermalIdx(i => i + 1)}>
                  Next <ChevronRight size={12} />
                </button>
              </div>
            </>
          ) : (
            <EmptyBox icon="🌡️" text="No thermal images uploaded yet." />
          )}
        </div>

        <div className="map-arrow-col">
          <ArrowRight size={28} color={hasThermal && hasRgb ? '#6366f1' : '#334155'} />
        </div>

        <div className="card" style={{ padding: 14 }}>
          <div className="flex justify-between items-center mb-3">
            <div className="section-title">Numbered RGB Image</div>
            {hasRgb && (
              <span style={{ fontSize: 11, color: '#64748b' }}>
                {rgbIdx + 1}/{rgbUrls.length} &nbsp;·&nbsp;
                <span style={{ color: '#10b981', fontWeight: 700 }}>{currentPanels.length} panels</span>
              </span>
            )}
          </div>

          {hasRgb && currentPanels.length > 0 ? (
            <>
              <div style={{ position: 'relative', borderRadius: 8, overflow: 'hidden', background: '#000', height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div style={{ position: 'relative', aspectRatio: `${width} / ${height}`, maxHeight: '100%', maxWidth: '100%' }}>
                  <img src={rgbUrls[rgbIdx]} alt={rgbFiles[rgbIdx]?.name} style={{ width: '100%', height: '100%', display: 'block' }} />
                  <svg viewBox={`0 0 ${width} ${height}`} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
                    {currentPanels.map(panel => {
                      const style = getPanelVisualStyle(panel);
                      const poly = formatPolygonPoints(panel.geometry);
                      const { x1, y1, x2, y2 } = panel.bbox;
                      return (
                        <g key={panel.panel_id}>
                          {poly ? (
                            <polygon points={poly} fill={style.fill} stroke={style.stroke} strokeWidth={Math.max(2, width / 800)} />
                          ) : (
                            <rect x={x1} y={y1} width={x2 - x1} height={y2 - y1} fill={style.fill} stroke={style.stroke} strokeWidth={Math.max(2, width / 800)} />
                          )}
                          <text
                            x={(x1 + x2) / 2}
                            y={(y1 + y2) / 2}
                            fill="#fff"
                            stroke="#111827"
                            strokeWidth={Math.max(2, width / 600)}
                            paintOrder="stroke"
                            textAnchor="middle"
                            dominantBaseline="middle"
                            fontSize={Math.max(12, width / 55)}
                            fontWeight="700"
                          >
                            {formatGridCoordinate(panel)}
                          </text>
                        </g>
                      );
                    })}
                  </svg>
                </div>
              </div>
              <div className="flex justify-between items-center mt-3">
                <button className="btn btn-outline" style={{ padding: '4px 10px', fontSize: 11 }} disabled={rgbIdx === 0} onClick={() => setRgbIdx(i => i - 1)}>
                  <ChevronLeft size={12} /> Prev
                </button>
                <span style={{ fontSize: 11, color: '#64748b', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', textAlign: 'center' }}>
                  {rgbFiles[rgbIdx]?.name}
                </span>
                <button className="btn btn-outline" style={{ padding: '4px 10px', fontSize: 11 }} disabled={rgbIdx === rgbUrls.length - 1} onClick={() => setRgbIdx(i => i + 1)}>
                  Next <ChevronRight size={12} />
                </button>
              </div>
            </>
          ) : (
            <EmptyBox
              icon="🗺️"
              text={
                hasRgb
                  ? (currentResult?.message || 'No backend panel detections available. Run project analysis with configured panel weights.')
                  : 'No RGB images uploaded yet.'
              }
            />
          )}
        </div>
      </div>

      <div className="card mt-4">
        <div className="section-title mb-3">Detection Summary</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12 }}>
          {[
            { label: 'Thermal Images', value: thermalUrls.length || '—' },
            { label: 'RGB Images', value: rgbUrls.length || '—' },
            { label: 'Total Panels Detected', value: totalPanels || '—' },
            { label: 'Defects Mapped', value: '—' },
          ].map(s => (
            <div key={s.label} style={{ background: '#0b1120', padding: '12px 16px', borderRadius: 8, textAlign: 'center' }}>
              <div style={{ fontSize: 22, fontWeight: 700, color: '#e2e8f0' }}>{s.value}</div>
              <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function EmptyBox({ icon, text }) {
  return (
    <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#334155', fontSize: 13, textAlign: 'center', border: '1px dashed #1e2d45', borderRadius: 8, padding: 16 }}>
      <div><div style={{ fontSize: 36, marginBottom: 10 }}>{icon}</div>{text}</div>
    </div>
  );
}
