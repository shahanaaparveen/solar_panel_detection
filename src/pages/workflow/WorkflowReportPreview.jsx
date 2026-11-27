import { useEffect, useState } from 'react';
import { ArrowRight, Edit2, Save, Download } from 'lucide-react';
import { getFindings, getPanels, saveReport, getProjectImageObjectUrl } from '../../api';

export default function WorkflowReportPreview({ project, onUpdateProject, onNext }) {
  const [editing, setEditing] = useState(false);
  const [findings, setFindings] = useState([]);
  const [panelObservations, setPanelObservations] = useState(0);
  const [saveError, setSaveError] = useState('');
  const [evidenceUrls, setEvidenceUrls] = useState({});
  useEffect(() => {
    if (!project._id) return;
    getFindings(project._id, project.jobId).then(setFindings).catch(() => setFindings([]));
    getPanels(project._id).then(rows => setPanelObservations(rows.reduce((n, row) => n + (row.panels?.length || 0), 0))).catch(() => setPanelObservations(0));
  }, [project._id, project.jobId]);
  useEffect(() => {
    let disposed = false;
    const urls = [];
    const imageIds = [...new Set(findings.flatMap(finding => (finding.evidence || []).map(item => item.imageId).filter(Boolean)))];
    Promise.allSettled(imageIds.map(async imageId => {
      const url = await getProjectImageObjectUrl(project._id, imageId);
      urls.push([imageId, url]);
    })).then(results => {
      if (disposed) urls.forEach(([, url]) => URL.revokeObjectURL(url));
      else setEvidenceUrls(Object.fromEntries(urls));
      if (results.some(result => result.status === 'rejected')) return;
    });
    return () => { disposed = true; urls.forEach(([, url]) => URL.revokeObjectURL(url)); };
  }, [project._id, findings]);
  const [info, setInfo] = useState({
    companyName:    project.companyName    || '',
    projectName:    project.projectName   || '',
    location:       project.location      || '',
    inspectorName:  project.inspectorName || '',
    date:           project.date          || '',
    notes:          project.notes         || '',
  });

  const save = async () => {
    try {
      const report = await saveReport(project._id, { title: `${info.projectName} Inspection Report`, notes: info.notes, jobId: project.jobId, metadata: info });
      onUpdateProject({ ...project, ...info, reportId: report._id,
        status: report.status === 'COMPLETED' ? 'Completed' : 'Analysis Incomplete' });
      setSaveError('');
      setEditing(false);
    } catch (error) {
      setSaveError(error.response?.data?.detail || 'Could not save the report.');
    }
  };

  const printPdf = () => window.print();

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <div style={s.pageTitle}>Report Preview</div>
          <div style={s.pageSub}>Review and edit before exporting</div>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          {!editing && <button style={s.btnSave} onClick={save}><Save size={13} /> Save Report</button>}
          {editing
            ? <button style={s.btnSave} onClick={save}><Save size={13} /> Save</button>
            : <button style={s.btnEdit} onClick={() => setEditing(true)}><Edit2 size={13} /> Edit</button>}
          <button style={s.btnPdf} onClick={printPdf}><Download size={13} /> Print / Save PDF</button>
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
            { label: 'Panel Observations', value: panelObservations || '—', color: '#1e293b' },
            { label: 'Healthy Panels',   value: '—', color: '#15803d' },
            { label: 'Finding Observations', value: findings.length, color: '#dc2626' },
            { label: 'Health Rate',      value: '—', color: '#15803d' },
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
            <tr>{['Panel No.', 'Defect Type', 'Inspection Priority', 'Confidence', 'Review / Recommendation', 'Evidence'].map(h => <th key={h} style={s.th}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {findings.map((r, i) => (
              <tr key={i} style={{ background: i % 2 === 0 ? '#fff' : '#f8fafc' }}>
                <td style={s.td}><strong>{r.panelId || 'Unassigned'}</strong></td>
                <td style={s.td}>{r.defectType} · {r.modality}</td>
                <td style={s.td}><span style={{ color: r.inspectionPriority === 'High' ? '#dc2626' : '#475569', fontWeight: 700 }}>{r.inspectionPriority || 'Unassigned'} · severity unvalidated</span></td>
                <td style={{ ...s.td, color: '#059669', fontWeight: 600 }}>{Math.round((r.modelConfidence || 0) * 100)}%</td>
                <td style={{ ...s.td, color: '#475569' }}>{r.recommendation}{r.reviewRequired ? ' · Review required' : ''}</td>
                <td style={s.td}>{evidenceUrls[r.evidence?.[0]?.imageId] ? <img src={evidenceUrls[r.evidence[0].imageId]} alt={`${r.defectType} evidence`} style={{ width: 84, height: 54, objectFit: 'cover' }} /> : '—'}</td>
              </tr>
            ))}
            {!findings.length && <tr><td colSpan={6} style={s.td}>No model findings are available for this project.</td></tr>}
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
        <span style={{ fontSize: 13, color: '#64748b' }}>Report observations are suspected; severity has not been validated.</span>
        <button style={s.btnNext} onClick={onNext}>Finish — View Reports <ArrowRight size={14} /></button>
      </div>
      {saveError && <div role="alert" style={{ color: '#b91c1c', marginTop: 12, fontSize: 13 }}>{saveError}</div>}
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
