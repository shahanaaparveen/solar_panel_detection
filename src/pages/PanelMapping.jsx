import { useState, useEffect } from 'react';
import { ArrowRight, ChevronLeft, ChevronRight, Loader } from 'lucide-react';
import { detectAndNumberPanels } from '../utils/panelDetection';

export default function PanelMapping({ thermalFiles, rgbFiles }) {
  const [thermalUrls, setThermalUrls]   = useState([]);
  const [thermalIdx, setThermalIdx]     = useState(0);
  const [rgbIdx, setRgbIdx]             = useState(0);

  // Processed RGB results: [{ dataURL, panels, fileName }]
  const [rgbResults, setRgbResults]     = useState([]);
  const [processing, setProcessing]     = useState(false);
  const [processedCount, setProcessedCount] = useState(0);

  // Thermal URLs
  useEffect(() => {
    const created = thermalFiles.map(f => URL.createObjectURL(f));
    setThermalUrls(created);
    setThermalIdx(0);
    return () => created.forEach(u => URL.revokeObjectURL(u));
  }, [thermalFiles]);

  // Run detection pipeline on each RGB image
  useEffect(() => {
    if (rgbFiles.length === 0) { setRgbResults([]); return; }

    let cancelled = false;
    setProcessing(true);
    setProcessedCount(0);
    setRgbResults([]);
    setRgbIdx(0);

    (async () => {
      const results = [];
      for (let i = 0; i < rgbFiles.length; i++) {
        if (cancelled) break;
        const { dataURL, panels } = await detectAndNumberPanels(rgbFiles[i]);
        results.push({ dataURL, panels, fileName: rgbFiles[i].name });
        if (!cancelled) setProcessedCount(i + 1);
      }
      if (!cancelled) {
        setRgbResults(results);
        setProcessing(false);
      }
    })();

    return () => { cancelled = true; };
  }, [rgbFiles]);

  const hasThermal  = thermalUrls.length > 0;
  const hasRgb      = rgbResults.length > 0;
  const currentRgb  = rgbResults[rgbIdx];

  const totalPanels = rgbResults.reduce((s, r) => s + r.panels.length, 0);

  return (
    <div>
      <div className="topbar">
        <div>
          <div className="page-title">Panel Mapping <span style={{ color: '#6366f1' }}>(With Numbered Images)</span></div>
          <div className="page-subtitle">YOLO-style detection → row clustering → left-to-right numbering</div>
        </div>
        <div style={{ background: '#0b1120', padding: '8px 16px', borderRadius: 8, fontSize: 13 }}>
          Mapping Accuracy: <strong style={{ color: hasThermal && hasRgb ? '#10b981' : '#64748b' }}>—</strong>
        </div>
      </div>

      <div className="mapping-layout">

        {/* ── Thermal ── */}
        <div className="card" style={{ padding: 14 }}>
          <div className="flex justify-between items-center mb-3">
            <div className="section-title">Detected (Thermal)</div>
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

        {/* ── Arrow ── */}
        <div className="map-arrow-col">
          <ArrowRight size={28} color={hasThermal && hasRgb ? '#6366f1' : '#334155'} />
          <ArrowRight size={28} color={hasThermal && hasRgb ? '#6366f1' : '#334155'} style={{ opacity: 0.4 }} />
        </div>

        {/* ── RGB numbered ── */}
        <div className="card" style={{ padding: 14 }}>
          <div className="flex justify-between items-center mb-3">
            <div className="section-title">Numbered RGB Image</div>
            {hasRgb && (
              <span style={{ fontSize: 11, color: '#64748b' }}>
                {rgbIdx + 1}/{rgbResults.length} &nbsp;·&nbsp;
                <span style={{ color: '#10b981', fontWeight: 700 }}>{currentRgb?.panels.length} panels</span>
              </span>
            )}
          </div>

          {processing ? (
            <div style={{ height: 260, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', border: '1px dashed #1e2d45', borderRadius: 8, gap: 12 }}>
              <Loader size={28} color="#6366f1" style={{ animation: 'spin 1s linear infinite' }} />
              <div style={{ fontSize: 13, color: '#94a3b8' }}>
                Detecting panels... ({processedCount}/{rgbFiles.length})
              </div>
              <div style={{ width: '60%' }}>
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${(processedCount / rgbFiles.length) * 100}%` }} />
                </div>
              </div>
            </div>
          ) : hasRgb ? (
            <>
              <div style={{ position: 'relative', borderRadius: 8, overflow: 'hidden', background: '#000' }}>
                <img
                  src={currentRgb.dataURL}
                  alt={currentRgb.fileName}
                  style={{ width: '100%', height: 260, objectFit: 'contain', display: 'block' }}
                />
              </div>
              <div className="flex justify-between items-center mt-3">
                <button className="btn btn-outline" style={{ padding: '4px 10px', fontSize: 11 }} disabled={rgbIdx === 0} onClick={() => setRgbIdx(i => i - 1)}>
                  <ChevronLeft size={12} /> Prev
                </button>
                <span style={{ fontSize: 11, color: '#64748b', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', textAlign: 'center' }}>
                  {currentRgb.fileName}
                </span>
                <button className="btn btn-outline" style={{ padding: '4px 10px', fontSize: 11 }} disabled={rgbIdx === rgbResults.length - 1} onClick={() => setRgbIdx(i => i + 1)}>
                  Next <ChevronRight size={12} />
                </button>
              </div>
            </>
          ) : (
            <EmptyBox icon="🗺️" text="No RGB images uploaded yet." />
          )}
        </div>
      </div>

      {/* ── Summary ── */}
      <div className="card mt-4">
        <div className="section-title mb-3">Detection Summary</div>
        {hasRgb ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12 }}>
            {[
              { label: 'Thermal Images',       value: thermalUrls.length || '—' },
              { label: 'RGB Images',            value: rgbResults.length },
              { label: 'Total Panels Detected', value: totalPanels },
              { label: 'Defects Mapped',        value: '—' },
            ].map(s => (
              <div key={s.label} style={{ background: '#0b1120', padding: '12px 16px', borderRadius: 8, textAlign: 'center' }}>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#e2e8f0' }}>{s.value}</div>
                <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>{s.label}</div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 80, color: '#334155', fontSize: 13 }}>
            Upload RGB images to run panel detection.
          </div>
        )}
      </div>

      {/* ── Per-image panel count table ── */}
      {hasRgb && (
        <div className="card mt-4">
          <div className="section-title mb-3">Per-Image Panel Count</div>
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>File Name</th>
                <th>Panels Detected</th>
                <th>Panel IDs</th>
              </tr>
            </thead>
            <tbody>
              {rgbResults.map((r, i) => (
                <tr key={i} style={{ cursor: 'pointer', background: i === rgbIdx ? 'rgba(99,102,241,0.08)' : undefined }} onClick={() => setRgbIdx(i)}>
                  <td className="text-muted">{i + 1}</td>
                  <td style={{ fontWeight: 500 }}>{r.fileName}</td>
                  <td><span style={{ color: '#10b981', fontWeight: 700 }}>{r.panels.length}</span></td>
                  <td className="text-muted" style={{ fontSize: 11 }}>
                    Panel-{String(r.panels[0]?.id).padStart(2,'0')} → Panel-{String(r.panels[r.panels.length-1]?.id).padStart(2,'0')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function EmptyBox({ icon, text }) {
  return (
    <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#334155', fontSize: 13, textAlign: 'center', border: '1px dashed #1e2d45', borderRadius: 8 }}>
      <div><div style={{ fontSize: 36, marginBottom: 10 }}>{icon}</div>{text}</div>
    </div>
  );
}
