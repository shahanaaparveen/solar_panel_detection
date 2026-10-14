import { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, ArrowRight, Loader } from 'lucide-react';
import { detectAndNumberPanels } from '../../utils/panelDetection';

export default function WorkflowMapping({ project, onUpdateProject, onNext }) {
  const [thermalUrls, setThermalUrls] = useState([]);
  const [thermalIdx, setThermalIdx] = useState(0);
  const [rgbResults, setRgbResults] = useState(project.rgbResults || []);
  const [rgbIdx, setRgbIdx] = useState(0);
  const [processing, setProcessing] = useState(false);
  const [processedCount, setProcessedCount] = useState(0);

  useEffect(() => {
    const created = (project.thermalFiles || []).map(f => URL.createObjectURL(f));
    setThermalUrls(created); setThermalIdx(0);
    return () => created.forEach(u => URL.revokeObjectURL(u));
  }, [project.thermalFiles]);

  useEffect(() => {
    if (!project.rgbFiles?.length || project.rgbResults?.length) return;
    let cancelled = false;
    setProcessing(true); setProcessedCount(0);
    (async () => {
      const results = [];
      for (let i = 0; i < project.rgbFiles.length; i++) {
        if (cancelled) break;
        const res = await detectAndNumberPanels(project.rgbFiles[i]);
        results.push({ ...res, fileName: project.rgbFiles[i].name });
        if (!cancelled) setProcessedCount(i + 1);
      }
      if (!cancelled) {
        setRgbResults(results);
        onUpdateProject({ ...project, rgbResults: results });
        setProcessing(false);
      }
    })();
    return () => { cancelled = true; };
  }, [project.rgbFiles]);

  const hasThermal = thermalUrls.length > 0;
  const hasRgb = rgbResults.length > 0;
  const cur = rgbResults[rgbIdx];
  const totalPanels = rgbResults.reduce((s, r) => s + r.panels.length, 0);

  // Defect summary table (mock per panel — real data comes from AI model)
  const defectRows = (project.thermalFiles || []).slice(0, 6).map((f, i) => ({
    thermal: f.name,
    panel: cur?.panels[i]?.id ? `Panel-${String(cur.panels[i].id).padStart(2,'0')}` : '—',
    defect: ['Hotspot', 'Bird Droppings', 'Loose Connection', 'Reverse Bias', 'Leaf Shading', 'Cracked Cell'][i % 6],
    confidence: [92, 88, 91, 87, 85, 93][i % 6],
    severity: ['High', 'Low', 'High', 'High', 'Low', 'High'][i % 6],
  }));

  return (
    <div>
      <div style={s.pageTitle}>Panel Mapping</div>
      <div style={s.pageSub}>Each thermal defect mapped to its corresponding numbered RGB panel</div>

      <div style={s.mapGrid}>
        {/* Thermal */}
        <div style={s.card}>
          <div style={s.cardHead}>
            <span style={s.cardTitle}>Thermal Image</span>
            {hasThermal && <span style={s.counter}>{thermalIdx + 1}/{thermalUrls.length}</span>}
          </div>
          {hasThermal ? (
            <>
              <img src={thermalUrls[thermalIdx]} alt="" style={s.mapImg} />
              <div style={s.navRow}>
                <button style={s.btnNav} disabled={thermalIdx === 0} onClick={() => setThermalIdx(i => i - 1)}><ChevronLeft size={12} /> Prev</button>
                <span style={s.navName}>{project.thermalFiles[thermalIdx]?.name}</span>
                <button style={s.btnNav} disabled={thermalIdx === thermalUrls.length - 1} onClick={() => setThermalIdx(i => i + 1)}>Next <ChevronRight size={12} /></button>
              </div>
            </>
          ) : <div style={s.emptyBox}>No thermal images</div>}
        </div>

        {/* Arrow */}
        <div style={s.arrowCol}>
          <div style={s.arrowLine} />
          <span style={s.arrowText}>→</span>
        </div>

        {/* RGB numbered */}
        <div style={s.card}>
          <div style={s.cardHead}>
            <span style={s.cardTitle}>Numbered RGB Image</span>
            {hasRgb && <span style={{ ...s.counter, color: '#10b981' }}>{cur?.panels.length} panels</span>}
          </div>
          {processing ? (
            <div style={s.processingBox}>
              <Loader size={24} color="#6366f1" style={{ animation: 'spin 1s linear infinite' }} />
              <div style={{ fontSize: 13, color: '#94a3b8', marginTop: 10 }}>Detecting panels... ({processedCount}/{project.rgbFiles?.length})</div>
              <div style={{ width: '70%', marginTop: 10 }}>
                <div style={s.progressBar}><div style={{ ...s.progressFill, width: `${(processedCount / (project.rgbFiles?.length || 1)) * 100}%` }} /></div>
              </div>
            </div>
          ) : hasRgb ? (
            <>
              <img src={cur.dataURL} alt="" style={s.mapImg} />
              <div style={s.navRow}>
                <button style={s.btnNav} disabled={rgbIdx === 0} onClick={() => setRgbIdx(i => i - 1)}><ChevronLeft size={12} /> Prev</button>
                <span style={s.navName}>{cur.fileName} · Panels 1–{cur.panels.length}</span>
                <button style={s.btnNav} disabled={rgbIdx === rgbResults.length - 1} onClick={() => setRgbIdx(i => i + 1)}>Next <ChevronRight size={12} /></button>
              </div>
            </>
          ) : <div style={s.emptyBox}>No RGB images uploaded</div>}
        </div>
      </div>

      {/* Defect summary table */}
      <div style={s.tableCard}>
        <div style={s.cardTitle2}>Defect Summary Table</div>
        <table style={s.table}>
          <thead>
            <tr>{['Thermal Image', 'Mapped Panel', 'Defect Type', 'Confidence', 'Severity'].map(h => <th key={h} style={s.th}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {defectRows.length > 0 ? defectRows.map((r, i) => (
              <tr key={i}>
                <td style={s.td}>{r.thermal}</td>
                <td style={s.td}><span style={s.panelBadge}>{r.panel}</span></td>
                <td style={s.td}>{r.defect}</td>
                <td style={{ ...s.td, color: '#10b981', fontWeight: 600 }}>{r.confidence}%</td>
                <td style={s.td}><span style={{ ...s.sevBadge, ...(r.severity === 'High' ? s.sevHigh : s.sevLow) }}>{r.severity}</span></td>
              </tr>
            )) : (
              <tr><td colSpan={5} style={{ ...s.td, textAlign: 'center', color: '#475569' }}>No defect data yet</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div style={s.footer}>
        <span style={{ fontSize: 13, color: '#64748b' }}>Total panels detected: <strong style={{ color: '#e2e8f0' }}>{totalPanels}</strong></span>
        <button style={s.btnNext} onClick={onNext}>Next — Defect Summary <ArrowRight size={14} /></button>
      </div>
      <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}

const s = {
  pageTitle: { fontSize: 20, fontWeight: 700, marginBottom: 4 },
  pageSub: { fontSize: 13, color: '#64748b', marginBottom: 20 },
  mapGrid: { display: 'grid', gridTemplateColumns: '1fr 40px 1fr', gap: 12, marginBottom: 20, alignItems: 'start' },
  card: { background: '#111827', border: '1px solid #1e2d45', borderRadius: 10, padding: 14 },
  cardHead: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  cardTitle: { fontSize: 13, fontWeight: 600, color: '#e2e8f0' },
  cardTitle2: { fontSize: 14, fontWeight: 600, color: '#e2e8f0', marginBottom: 14 },
  counter: { fontSize: 11, color: '#64748b' },
  mapImg: { width: '100%', height: 240, objectFit: 'contain', borderRadius: 7, background: '#000', display: 'block' },
  navRow: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10 },
  btnNav: { display: 'inline-flex', alignItems: 'center', gap: 3, padding: '4px 10px', background: 'transparent', color: '#94a3b8', border: '1px solid #1e2d45', borderRadius: 5, fontSize: 11, cursor: 'pointer' },
  navName: { fontSize: 11, color: '#64748b', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', textAlign: 'center' },
  emptyBox: { height: 240, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#334155', fontSize: 13, border: '1px dashed #1e2d45', borderRadius: 7 },
  processingBox: { height: 240, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', border: '1px dashed #1e2d45', borderRadius: 7 },
  arrowCol: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', paddingTop: 120 },
  arrowLine: { width: 2, height: 30, background: '#1e2d45' },
  arrowText: { fontSize: 22, color: '#6366f1', marginTop: 4 },
  progressBar: { height: 5, background: '#1e2d45', borderRadius: 3, overflow: 'hidden' },
  progressFill: { height: '100%', background: 'linear-gradient(90deg,#6366f1,#8b5cf6)', borderRadius: 3, transition: 'width 0.3s' },
  tableCard: { background: '#111827', border: '1px solid #1e2d45', borderRadius: 10, padding: 16, marginBottom: 20 },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { padding: '9px 12px', textAlign: 'left', fontSize: 11, color: '#64748b', fontWeight: 600, textTransform: 'uppercase', borderBottom: '1px solid #1e2d45' },
  td: { padding: '9px 12px', fontSize: 12.5, color: '#cbd5e1', borderBottom: '1px solid #0b1120' },
  panelBadge: { background: '#0c1a3a', color: '#60a5fa', padding: '2px 8px', borderRadius: 5, fontWeight: 700, fontSize: 11 },
  sevBadge: { padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 600 },
  sevHigh: { background: '#3f0a0a', color: '#f87171' },
  sevLow: { background: '#052e16', color: '#22c55e' },
  footer: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 20, borderTop: '1px solid #1e2d45' },
  btnNext: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '10px 24px', background: '#6366f1', color: '#fff', border: 'none', borderRadius: 7, fontSize: 13, fontWeight: 600, cursor: 'pointer' },
};
