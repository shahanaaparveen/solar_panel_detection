import { useState } from 'react';
import { ArrowRight, Edit2, Save, Download, FileText } from 'lucide-react';

export default function WorkflowReportPreview({ project, onUpdateProject, onNext }) {
  const [editing, setEditing] = useState(false);
  const [info, setInfo] = useState({
    companyName:    project.companyName    || '',
    projectName:    project.projectName   || '',
    location:       project.location      || '',
    inspectorName:  project.inspectorName || '',
    date:           project.date          || '',
    notes:          project.notes         || '',
  });

  const save = () => {
    onUpdateProject({ ...project, ...info, status: 'Completed' });
    setEditing(false);
  };

  const totalPanels  = project.rgbResults?.reduce((s, r) => s + r.panels.length, 0) || 0;
  const defective    = 11;
  const healthy      = Math.max(0, totalPanels - defective);
  const healthRate   = totalPanels > 0 ? ((healthy / totalPanels) * 100).toFixed(1) : '—';

  const defectRows = [
    { panel: 'Panel-03', defect: 'Hotspot',          severity: 'High',   conf: 92, rec: 'Immediate replacement' },
    { panel: 'Panel-07', defect: 'Bird Droppings',   severity: 'Low',    conf: 88, rec: 'Clean surface' },
    { panel: 'Panel-12', defect: 'Loose Connection', severity: 'High',   conf: 91, rec: 'Re-tighten connections' },
    { panel: 'Panel-18', defect: 'Reverse Bias',     severity: 'High',   conf: 87, rec: 'Replace bypass diode' },
    { panel: 'Panel-24', defect: 'Leaf Shading',     severity: 'Low',    conf: 85, rec: 'Remove obstruction' },
    { panel: 'Panel-31', defect: 'Cracked Cell',     severity: 'High',   conf: 93, rec: 'Replace panel' },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <div style={s.pageTitle}>Report Preview</div>
          <div style={s.pageSub}>Review and edit before exporting</div>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          {editing
            ? <button style={s.btnSave} onClick={save}><Save size={13} /> Save</button>
            : <button style={s.btnEdit} onClick={() => setEditing(true)}><Edit2 size={13} /> Edit</button>}
          <button style={s.btnPdf}><Download size={13} /> Export PDF</button>
          <button style={s.btnWord}><FileText size={13} /> Export Word</button>
        </div>
      </div>

      {/* Report document */}
      <div style={s.doc}>
        {/* Header */}
        <div style={s.docHeader}>
          <div style={s.docTitle}>SOLAR PANEL INSPECTION REPORT</div>
          <div style={s.docSub}>AI-Powered Thermal & RGB Analysis System</div>
          <div style={s.docLine} />
        </div>

        {/* Project info grid */}
        <div style={s.infoGrid}>
          {[
            { label: 'Company Name',  key: 'companyName' },
            { label: 'Project Name',  key: 'projectName' },
            { label: 'Location',      key: 'location' },
            { label: 'Inspector',     key: 'inspectorName' },
            { label: 'Date',          key: 'date' },
            { label: 'Notes',         key: 'notes' },
          ].map(f => (
            <div key={f.key} style={s.infoCell}>
              <div style={s.infoLabel}>{f.label}</div>
              {editing
                ? <input style={s.editInput} value={info[f.key]} onChange={e => setInfo(p => ({ ...p, [f.key]: e.target.value }))} />
                : <div style={s.infoVal}>{info[f.key] || '—'}</div>}
            </div>
          ))}
        </div>

        {/* Stats */}
        <div style={s.statsRow}>
          {[
            { label: 'Total Panels',     value: totalPanels || '—', color: '#1e293b' },
            { label: 'Healthy Panels',   value: totalPanels ? healthy : '—', color: '#15803d' },
            { label: 'Defective Panels', value: defective,  color: '#dc2626' },
            { label: 'Health Rate',      value: totalPanels ? `${healthRate}%` : '—', color: '#15803d' },
          ].map(st => (
            <div key={st.label} style={s.statBox}>
              <div style={{ ...s.statVal, color: st.color }}>{st.value}</div>
              <div style={s.statLabel}>{st.label}</div>
            </div>
          ))}
        </div>

        {/* Defect table */}
        <div style={s.sectionTitle}>Defect Details</div>
        <table style={s.table}>
          <thead style={{ background: '#f1f5f9' }}>
            <tr>{['Panel No.', 'Defect Type', 'Severity', 'Confidence', 'Recommendation'].map(h => <th key={h} style={s.th}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {defectRows.map((r, i) => (
              <tr key={i} style={{ background: i % 2 === 0 ? '#fff' : '#f8fafc' }}>
                <td style={s.td}><strong>{r.panel}</strong></td>
                <td style={s.td}>{r.defect}</td>
                <td style={s.td}><span style={{ color: r.severity === 'High' ? '#dc2626' : '#16a34a', fontWeight: 700 }}>{r.severity}</span></td>
                <td style={{ ...s.td, color: '#059669', fontWeight: 600 }}>{r.conf}%</td>
                <td style={{ ...s.td, color: '#475569' }}>{r.rec}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* Footer */}
        <div style={s.docFooter}>
          <span>Solar Inspect AI System</span>
          <span>Confidential — For Internal Use Only</span>
          <span>{info.date}</span>
        </div>
      </div>

      <div style={s.footer}>
        <span style={{ fontSize: 13, color: '#64748b' }}>Report ready for export</span>
        <button style={s.btnNext} onClick={onNext}>Finish — View Reports <ArrowRight size={14} /></button>
      </div>
    </div>
  );
}

const s = {
  pageTitle: { fontSize: 20, fontWeight: 700, marginBottom: 4, color: '#0a2545' },
  pageSub: { fontSize: 13, color: '#55657f' },
  btnEdit:  { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 16px', background: '#ffffff', color: '#0a2545', border: '1px solid #d9e2f0', borderRadius: 7, fontSize: 12, cursor: 'pointer' },
  btnSave:  { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 16px', background: '#0a2545', color: '#fff', border: 'none', borderRadius: 7, fontSize: 12, cursor: 'pointer' },
  btnPdf:   { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 16px', background: '#b91c1c', color: '#fff', border: 'none', borderRadius: 7, fontSize: 12, cursor: 'pointer' },
  btnWord:  { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 16px', background: '#0a2545', color: '#fff', border: 'none', borderRadius: 7, fontSize: 12, cursor: 'pointer' },
  doc: { background: '#fff', color: '#1e293b', borderRadius: 10, padding: '36px 40px', marginBottom: 24, fontFamily: "'Segoe UI', sans-serif" },
  docHeader: { textAlign: 'center', marginBottom: 24 },
  docTitle: { fontSize: 20, fontWeight: 800, color: '#1e293b', letterSpacing: 1 },
  docSub: { fontSize: 12, color: '#64748b', marginTop: 4 },
  docLine: { height: 2, background: '#6366f1', marginTop: 14, borderRadius: 1 },
  infoGrid: { display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12, marginBottom: 20 },
  infoCell: { background: '#ffffff', padding: '10px 14px', borderRadius: 7, border: '1px solid #edf3fa' },
  infoLabel: { fontSize: 10, color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.5, fontWeight: 600 },
  infoVal: { fontSize: 13, fontWeight: 600, color: '#1e293b', marginTop: 3 },
  editInput: { width: '100%', marginTop: 3, padding: '5px 8px', border: '1px solid #6366f1', borderRadius: 5, fontSize: 13, color: '#1e293b', outline: 'none', boxSizing: 'border-box' },
  statsRow: { display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 20 },
  statBox: { background: '#ffffff', padding: '12px', borderRadius: 7, textAlign: 'center', border: '1px solid #edf3fa' },
  statVal: { fontSize: 24, fontWeight: 700 },
  statLabel: { fontSize: 10, color: '#64748b', marginTop: 3 },
  sectionTitle: { fontSize: 13, fontWeight: 700, color: '#1e293b', marginBottom: 10, paddingBottom: 6, borderBottom: '1px solid #e2e8f0' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 12 },
  th: { padding: '9px 12px', textAlign: 'left', color: '#475569', fontWeight: 600, fontSize: 11, textTransform: 'uppercase' },
  td: { padding: '9px 12px', color: '#1e293b', borderBottom: '1px solid #f1f5f9' },
  docFooter: { display: 'flex', justifyContent: 'space-between', marginTop: 24, paddingTop: 12, borderTop: '1px solid #e2e8f0', fontSize: 11, color: '#94a3b8' },
  footer: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 20, borderTop: '1px solid #1e2d45' },
  btnNext: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '10px 24px', background: '#6366f1', color: '#fff', border: 'none', borderRadius: 7, fontSize: 13, fontWeight: 600, cursor: 'pointer' },
};
