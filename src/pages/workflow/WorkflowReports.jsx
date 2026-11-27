import { useEffect, useState } from 'react';
import { Download, ArrowLeft } from 'lucide-react';
import { getFindings, getPanels, getReport, getProjectImageObjectUrl } from '../../api';

export default function WorkflowReports({ project, onBackToProjects }) {
  const [defectRows, setDefectRows] = useState([]);
  const [panelCount, setPanelCount] = useState(0);
  const [report, setReport] = useState(null);
  const [evidenceUrls, setEvidenceUrls] = useState({});
  useEffect(() => {
    if (!project._id) return;
    getReport(project._id).then(async saved => {
      setReport(saved);
      if (saved.findings) {
        setDefectRows(saved.findings);
        setPanelCount((saved.imageResults || []).reduce((n, row) => n + (row.panelCount || 0), 0));
        return;
      }
      const [rows, panels] = await Promise.all([
        getFindings(project._id, saved.jobId || project.jobId),
        getPanels(project._id),
      ]);
      setDefectRows(rows);
      setPanelCount(panels.reduce((n, row) => n + (row.panels?.length || 0), 0));
    }).catch(() => {
      setReport(null);
      getFindings(project._id, project.jobId).then(setDefectRows).catch(() => setDefectRows([]));
      setPanelCount(0);
    });
  }, [project._id, project.jobId]);
  useEffect(() => {
    let disposed = false;
    const urls = [];
    const imageIds = [...new Set(defectRows.flatMap(finding => (finding.evidence || []).map(item => item.imageId).filter(Boolean)))];
    Promise.allSettled(imageIds.map(async imageId => {
      const url = await getProjectImageObjectUrl(project._id, imageId);
      urls.push([imageId, url]);
    })).then(() => {
      if (disposed) urls.forEach(([, url]) => URL.revokeObjectURL(url));
      else setEvidenceUrls(Object.fromEntries(urls));
    });
    return () => { disposed = true; urls.forEach(([, url]) => URL.revokeObjectURL(url)); };
  }, [project._id, defectRows]);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
        <div>
          <div style={s.pageTitle}>Reports</div>
          <div style={s.pageSub}>Inspection report for {project.projectName}{report ? ` · ${report.status} · Saved ${new Date(report.createdAt).toLocaleString()}` : ' · Not saved yet'}</div>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button style={s.btnPdf} onClick={() => window.print()}><Download size={13} /> Print / Save PDF</button>
        </div>
      </div>

      {/* Report summary card */}
      <div style={s.card}>
        <div style={s.cardTitle}>Report Summary</div>
        <div style={s.infoGrid}>
          {[
            { label: 'Company',    value: project.companyName },
            { label: 'Project',    value: project.projectName },
            { label: 'Location',   value: project.location },
            { label: 'Inspector',  value: project.inspectorName },
            { label: 'Date',       value: project.date },
            { label: 'Report Status', value: report?.status || project.status },
          ].map(f => (
            <div key={f.label} style={s.infoCell}>
              <div style={s.infoLabel}>{f.label}</div>
              <div style={s.infoVal}>{f.value || '—'}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div style={s.statsRow}>
        {[
          { label: 'Thermal Images',   value: project.thermalImages?.length || 0 },
          { label: 'RGB Images',       value: project.rgbImages?.length || 0 },
          { label: 'Panel Observations', value: panelCount },
          { label: 'Finding Observations', value: defectRows.length },
        ].map(st => (
          <div key={st.label} style={s.statCard}>
            <div style={s.statVal}>{st.value}</div>
            <div style={s.statLabel}>{st.label}</div>
          </div>
        ))}
      </div>

      {/* Defect table */}
      <div style={s.card}>
        <div style={s.cardTitle}>Defect Report</div>
        <table style={s.table}>
          <thead>
            <tr>{['S.No', 'Panel No.', 'Defect Type', 'Inspection Priority', 'Confidence', 'Recommendation', 'Evidence'].map(h => <th key={h} style={s.th}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {defectRows.map((r, i) => (
              <tr key={i}>
                <td style={s.td}>{i + 1}</td>
                <td style={s.td}><span style={s.panelBadge}>{r.panelId || r.matchStatus || 'Unassigned'}</span></td>
                <td style={s.td}>{r.defectType} ({r.modality})</td>
                <td style={s.td}><span style={{ ...s.sev, ...(r.inspectionPriority === 'High' ? s.sevH : s.sevL) }}>{r.inspectionPriority || 'Unassigned'} · unvalidated severity</span></td>
                <td style={{ ...s.td, color: '#10b981', fontWeight: 600 }}>{Math.round((r.modelConfidence || 0) * 100)}%</td>
                <td style={{ ...s.td, color: '#64748b', fontSize: 12 }}>{r.recommendation}{r.reviewRequired ? ' · Review required' : ''}</td>
                <td style={s.td}>{evidenceUrls[r.evidence?.[0]?.imageId] ? <img src={evidenceUrls[r.evidence[0].imageId]} alt={`${r.defectType} evidence`} style={{ width: 84, height: 54, objectFit: 'cover' }} /> : '—'}</td>
              </tr>
            ))}
            {!defectRows.length && <tr><td colSpan={7} style={s.td}>No model findings are available for this project.</td></tr>}
          </tbody>
        </table>
      </div>

      <div style={s.footer}>
        <button style={s.btnBack} onClick={onBackToProjects}><ArrowLeft size={13} /> Back to Projects</button>
        <span style={{ fontSize: 13, color: report?.status === 'COMPLETED' ? '#22c55e' : '#f59e0b', fontWeight: 600 }}>{report?.status === 'COMPLETED' ? '✓ Inspection Complete' : 'Analysis incomplete · Draft report'}</span>
      </div>
    </div>
  );
}

const s = {
  pageTitle: { fontSize: 20, fontWeight: 700, marginBottom: 4, color: '#e2e8f0' },
  pageSub: { fontSize: 13, color: '#64748b' },
  btnPdf:  { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 16px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: 7, fontSize: 12, cursor: 'pointer' },
  btnWord: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 16px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: 7, fontSize: 12, cursor: 'pointer' },
  card: { background: '#111827', border: '1px solid #1e2d45', borderRadius: 10, padding: 18, marginBottom: 16 },
  cardTitle: { fontSize: 13, fontWeight: 600, color: '#e2e8f0', marginBottom: 14 },
  infoGrid: { display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12 },
  infoCell: { background: '#0b1120', padding: '10px 14px', borderRadius: 7 },
  infoLabel: { fontSize: 10, color: '#64748b', textTransform: 'uppercase', letterSpacing: 0.5, fontWeight: 600 },
  infoVal: { fontSize: 13, fontWeight: 600, color: '#e2e8f0', marginTop: 3 },
  statsRow: { display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14, marginBottom: 16 },
  statCard: { background: '#111827', border: '1px solid #1e2d45', borderRadius: 10, padding: 16, textAlign: 'center' },
  statVal: { fontSize: 26, fontWeight: 700, color: '#e2e8f0' },
  statLabel: { fontSize: 11, color: '#64748b', marginTop: 4 },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { padding: '9px 12px', textAlign: 'left', fontSize: 11, color: '#64748b', fontWeight: 600, textTransform: 'uppercase', borderBottom: '1px solid #1e2d45' },
  td: { padding: '9px 12px', fontSize: 12.5, color: '#cbd5e1', borderBottom: '1px solid #0b1120' },
  panelBadge: { background: '#0c1a3a', color: '#60a5fa', padding: '2px 8px', borderRadius: 5, fontWeight: 700, fontSize: 11 },
  sev: { padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 600 },
  sevH: { background: '#3f0a0a', color: '#f87171' },
  sevL: { background: '#052e16', color: '#22c55e' },
  footer: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 20, borderTop: '1px solid #1e2d45' },
  btnBack: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '10px 20px', background: 'transparent', color: '#94a3b8', border: '1px solid #1e2d45', borderRadius: 7, fontSize: 13, cursor: 'pointer' },
};
