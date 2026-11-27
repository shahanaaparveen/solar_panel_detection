import { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, ArrowRight } from 'lucide-react';
import { getPanels, getFindings, registerImages, getProjectImageObjectUrl } from '../../api';

function PanelOverlay({ src, panels, imageSize, selectedPanel, onSelect }) {
  const width = imageSize?.width || 1;
  const height = imageSize?.height || 1;
  return (
    <div style={{ position: 'relative', width: '100%', height: 240, background: '#000', borderRadius: 7, overflow: 'hidden' }}>
      <img src={src} alt="Localized solar panels" style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }} />
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none' }}>
        {(panels || []).map(panel => {
          const { x1, y1, x2, y2 } = panel.bbox;
          return <g key={panel.panel_id} onClick={() => onSelect(panel.panel_id)} style={{ pointerEvents: 'all', cursor: 'pointer' }}><rect x={x1} y={y1} width={x2 - x1} height={y2 - y1} fill={selectedPanel === panel.panel_id ? 'rgba(16,185,129,0.30)' : 'rgba(99,102,241,0.12)'} stroke={selectedPanel === panel.panel_id ? '#34d399' : '#a5b4fc'} strokeWidth={Math.max(2, width / 800)} /><text x={(x1 + x2) / 2} y={(y1 + y2) / 2} fill="#fff" stroke="#111827" strokeWidth={Math.max(2, width / 600)} paintOrder="stroke" textAnchor="middle" dominantBaseline="middle" fontSize={Math.max(14, width / 45)} fontWeight="700">{panel.panel_id}</text></g>;
        })}
      </svg>
    </div>
  );
}

export default function WorkflowMapping({ project, onNext }) {
  const [thermalIdx, setThermalIdx] = useState(0);
  const [rgbResults, setRgbResults] = useState([]);
  const [rgbIdx, setRgbIdx] = useState(0);
  const [findings, setFindings] = useState([]);
  const [selectedPanel, setSelectedPanel] = useState(null);
  const [registration, setRegistration] = useState(null);
  const [registering, setRegistering] = useState(false);
  const [panelsLoading, setPanelsLoading] = useState(true);
  const [thermalUrl, setThermalUrl] = useState('');
  const [rgbUrl, setRgbUrl] = useState('');

  useEffect(() => {
    if (!project._id) return;
    setPanelsLoading(true);
    getPanels(project._id).then(setRgbResults).catch(() => setRgbResults([])).finally(() => setPanelsLoading(false));
    getFindings(project._id, project.jobId).then(setFindings).catch(() => setFindings([]));
  }, [project._id, project.jobId]);
  useEffect(() => {
    setRegistration(null);
    setSelectedPanel(null);
  }, [rgbIdx, thermalIdx]);

  useEffect(() => {
    const image = project.thermalImages?.[thermalIdx];
    let disposed = false;
    let objectUrl;
    setThermalUrl('');
    if (project._id && image?.imageId) getProjectImageObjectUrl(project._id, image.imageId).then(url => {
      if (disposed) URL.revokeObjectURL(url);
      else { objectUrl = url; setThermalUrl(url); }
    }).catch(() => setThermalUrl(''));
    return () => { disposed = true; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [project._id, project.thermalImages, thermalIdx]);

  useEffect(() => {
    const image = rgbResults[rgbIdx];
    let disposed = false;
    let objectUrl;
    setRgbUrl('');
    if (project._id && image?.imageId) getProjectImageObjectUrl(project._id, image.imageId).then(url => {
      if (disposed) URL.revokeObjectURL(url);
      else { objectUrl = url; setRgbUrl(url); }
    }).catch(() => setRgbUrl(''));
    return () => { disposed = true; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [project._id, rgbResults, rgbIdx]);

  const thermalImages = project.thermalImages || [];
  const rgbImages = project.rgbImages || [];
  const hasThermal = thermalImages.length > 0;
  const cur = rgbResults[rgbIdx];
  const hasRgb = cur?.status === 'COMPLETED';
  const totalPanels = rgbResults.reduce((s, r) => s + (r.panels?.length || 0), 0);
  const defectRows = selectedPanel ? findings.filter(row => row.panelId === selectedPanel) : findings;
  const registerCurrentPair = async () => {
    const rgbImage = rgbImages.find(image => image.imageId === cur?.imageId);
    const thermalImage = thermalImages[thermalIdx];
    if (!rgbImage || !thermalImage) return;
    setRegistering(true);
    try {
      const result = await registerImages(project._id, rgbImage.imageId, thermalImage.imageId);
      setRegistration(result);
      getFindings(project._id, project.jobId).then(setFindings).catch(() => {});
    } catch (error) {
      setRegistration({ status: 'UNREGISTERED', reason: error.response?.data?.detail || 'Registration request failed' });
    } finally {
      setRegistering(false);
    }
  };

  return (
    <div>
      <div style={s.pageTitle}>Panel Mapping</div>
      <div style={s.pageSub}>Panel localization is model-backed. Cross-modal matches require verified image registration.</div>

      <div style={s.mapGrid}>
        {/* Thermal */}
        <div style={s.card}>
          <div style={s.cardHead}>
            <span style={s.cardTitle}>Thermal Image</span>
            {hasThermal && <span style={s.counter}>{thermalImages.length} images</span>}
          </div>
          {hasThermal ? (
            <>
              {thermalUrl ? <img src={thermalUrl} alt={thermalImages[thermalIdx].imageName} style={s.mapImg} /> : <div style={s.emptyBox}>Loading protected image…</div>}
              <div style={s.navRow}>
                <button style={s.btnNav} disabled={thermalIdx === 0} onClick={() => setThermalIdx(i => i - 1)}><ChevronLeft size={12} /> Prev</button>
                <span style={s.navName}>{thermalImages[thermalIdx].imageName}</span>
                <button style={s.btnNav} disabled={thermalIdx === thermalImages.length - 1} onClick={() => setThermalIdx(i => i + 1)}>Next <ChevronRight size={12} /></button>
              </div>
            </>
          ) : <div style={s.emptyBox}>No thermal images</div>}
        </div>

        {/* Arrow */}
        <div style={s.arrowCol}>
          <div style={s.arrowLine} />
          <span style={s.arrowText}>→</span>
          <button style={s.btnNav} disabled={!cur || !thermalImages.length || registering} onClick={registerCurrentPair}>{registering ? 'Aligning…' : 'Align pair'}</button>
          {registration && <span style={{ ...s.counter, color: registration.status === 'REGISTERED' ? '#10b981' : '#f59e0b', textAlign: 'center' }}>{registration.status}{registration.quality != null ? ` · ${Math.round(registration.quality * 100)}%` : ''}</span>}
        </div>

        {/* RGB numbered */}
        <div style={s.card}>
          <div style={s.cardHead}>
            <span style={s.cardTitle}>Numbered RGB Image</span>
            {cur?.status === 'COMPLETED' && <span style={{ ...s.counter, color: '#10b981' }}>{cur.panels?.length || 0} panels</span>}
          </div>
          {hasRgb ? (
            <>
              {rgbUrl && <PanelOverlay src={rgbUrl} panels={cur.panels} imageSize={cur.imageSize} selectedPanel={selectedPanel} onSelect={setSelectedPanel} />}
              <div style={s.navRow}>
                <button style={s.btnNav} disabled={rgbIdx === 0} onClick={() => setRgbIdx(i => i - 1)}><ChevronLeft size={12} /> Prev</button>
                <span style={s.navName}>{cur.panels?.length || 0} localized panels</span>
                <button style={s.btnNav} disabled={rgbIdx === rgbResults.length - 1} onClick={() => setRgbIdx(i => i + 1)}>Next <ChevronRight size={12} /></button>
              </div>
            </>
          ) : <div style={s.emptyBox}>{!rgbImages.length ? 'No RGB images uploaded' : panelsLoading ? 'Loading saved panel results…' : cur ? (cur.message || `Panel model status: ${cur.status}`) : 'No panel result yet; run analysis first.'}</div>}
        </div>
      </div>

      {/* Defect summary table */}
      <div style={s.tableCard}>
        <div style={{ ...s.cardTitle2, display: 'flex', justifyContent: 'space-between' }}><span>Finding Observations</span>{selectedPanel && <button style={s.btnNav} onClick={() => setSelectedPanel(null)}>Clear panel filter · {selectedPanel}</button>}</div>
        <table style={s.table}>
          <thead>
            <tr>{['Modality', 'Mapped Panel', 'Defect Type', 'Confidence', 'Inspection Priority'].map(h => <th key={h} style={s.th}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {defectRows.length > 0 ? defectRows.map((r, i) => (
              <tr key={i}>
                <td style={s.td}>{r.modality}</td>
                <td style={s.td}><span style={s.panelBadge}>{r.panelId || r.matchStatus}</span></td>
                <td style={s.td}>{r.defectType}</td>
                <td style={{ ...s.td, color: '#10b981', fontWeight: 600 }}>{Math.round((r.modelConfidence || 0) * 100)}%</td>
                <td style={s.td}><span style={{ ...s.sevBadge, ...(r.inspectionPriority === 'High' ? s.sevHigh : s.sevLow) }}>{r.inspectionPriority || 'Unassigned'} · severity unvalidated{r.reviewRequired ? ' · Review' : ''}</span></td>
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
