import { useEffect, useState } from 'react';
import { ArrowRight } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';
import { getFindings, getPanels } from '../../api';

const tt = { contentStyle: { background: '#111827', border: '1px solid #1e2d45', borderRadius: 8, color: '#e2e8f0', fontSize: 12 } };

export default function WorkflowSummary({ project, onNext }) {
  const [findings, setFindings] = useState([]);
  const [panels, setPanels] = useState([]);
  useEffect(() => {
    if (!project._id) return;
    getFindings(project._id, project.jobId).then(setFindings).catch(() => setFindings([]));
    getPanels(project._id).then(setPanels).catch(() => setPanels([]));
  }, [project._id, project.jobId]);
  const colors = ['#ef4444', '#f59e0b', '#3b82f6', '#8b5cf6', '#10b981', '#06b6d4', '#ec4899'];
  const counts = findings.reduce((all, finding) => ({ ...all, [finding.defectType]: (all[finding.defectType] || 0) + 1 }), {});
  const defectTypes = Object.entries(counts).map(([name, value], i) => ({ name, value, color: colors[i % colors.length] }));
  const priorityColors = { High: '#ef4444', Medium: '#f59e0b', Low: '#10b981' };
  const priorityData = ['High', 'Medium', 'Low'].map(name => ({ name, value: findings.filter(f => f.inspectionPriority === name).length, color: priorityColors[name] })).filter(d => d.value > 0);
  const totalPanels = panels.reduce((total, row) => total + (row.panels?.length || 0), 0);
  const affectedFindings = findings.length;

  return (
    <div>
      <div style={s.pageTitle}>Defect Summary</div>
      <div style={s.pageSub}>Complete analysis of all detected defects across {project.projectName}</div>

      {/* Stats */}
      <div style={s.statsRow}>
        {[
          { label: 'Total Panels',     value: totalPanels || '—', color: '#e2e8f0' },
          { label: 'Healthy Panels',   value: '—', color: '#22c55e' },
          { label: 'Finding Observations', value: affectedFindings, color: '#ef4444' },
          { label: 'Health Rate',      value: '—', color: '#22c55e' },
        ].map(st => (
          <div key={st.label} style={s.statCard}>
            <div style={{ ...s.statVal, color: st.color }}>{st.value}</div>
            <div style={s.statLabel}>{st.label}</div>
          </div>
        ))}
      </div>

      <div style={s.grid2}>
        {/* Defect distribution pie */}
        <div style={s.card}>
          <div style={s.cardTitle}>Defect Distribution</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
            <ResponsiveContainer width={160} height={160}>
              <PieChart>
                <Pie data={defectTypes} cx="50%" cy="50%" innerRadius={42} outerRadius={72} dataKey="value" paddingAngle={2}>
                  {defectTypes.map((e, i) => <Cell key={i} fill={e.color} />)}
                </Pie>
                <Tooltip {...tt} />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
              {defectTypes.map(d => (
                <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
                  <div style={{ width: 9, height: 9, borderRadius: '50%', background: d.color, flexShrink: 0 }} />
                  <span style={{ flex: 1, color: '#cbd5e1' }}>{d.name}</span>
                  <span style={{ color: '#64748b' }}>{d.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Inspection priority pie */}
        <div style={s.card}>
          <div style={s.cardTitle}>Inspection Priority (not validated severity)</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
            <ResponsiveContainer width={160} height={160}>
              <PieChart>
                <Pie data={priorityData} cx="50%" cy="50%" innerRadius={42} outerRadius={72} dataKey="value" paddingAngle={2}>
                  {priorityData.map((e, i) => <Cell key={i} fill={e.color} />)}
                </Pie>
                <Tooltip {...tt} />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
              {priorityData.map(d => (
                <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12 }}>
                  <div style={{ width: 9, height: 9, borderRadius: '50%', background: d.color, flexShrink: 0 }} />
                  <span style={{ flex: 1, color: '#cbd5e1' }}>{d.name}</span>
                  <span style={{ color: '#64748b' }}>{d.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Bar chart */}
      <div style={s.card}>
        <div style={s.cardTitle}>Defect Count by Type</div>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={defectTypes} margin={{ top: 0, right: 10, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2d45" />
            <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#64748b' }} />
            <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
            <Tooltip {...tt} />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {defectTypes.map((e, i) => <Cell key={i} fill={e.color} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Defect breakdown table */}
      <div style={s.card}>
        <div style={s.cardTitle}>Defect Breakdown Table</div>
        <table style={s.table}>
          <thead>
            <tr>{['Defect Type', 'Count', 'Percentage', 'Inspection Priority'].map(h => <th key={h} style={s.th}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {defectTypes.map(d => (
              <tr key={d.name}>
                <td style={s.td}><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: d.color, marginRight: 8 }} />{d.name}</td>
                <td style={s.td}>{d.value}</td>
                <td style={s.td}>{findings.length ? `${((d.value / findings.length) * 100).toFixed(1)}%` : '—'}</td>
                <td style={s.td}>See per finding; severity unvalidated</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={s.footer}>
        <span style={{ fontSize: 13, color: '#64748b' }}>Localized panel detections are image-level observations; cross-image identity is unverified.</span>
        <button style={s.btnNext} onClick={onNext}>Next — Report Preview <ArrowRight size={14} /></button>
      </div>
    </div>
  );
}

const s = {
  pageTitle: { fontSize: 20, fontWeight: 700, marginBottom: 4 },
  pageSub: { fontSize: 13, color: '#64748b', marginBottom: 20 },
  statsRow: { display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 14, marginBottom: 20 },
  statCard: { background: '#111827', border: '1px solid #1e2d45', borderRadius: 10, padding: '16px', textAlign: 'center' },
  statVal: { fontSize: 28, fontWeight: 700 },
  statLabel: { fontSize: 11, color: '#64748b', marginTop: 4 },
  grid2: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 },
  card: { background: '#111827', border: '1px solid #1e2d45', borderRadius: 10, padding: 16, marginBottom: 16 },
  cardTitle: { fontSize: 13, fontWeight: 600, color: '#e2e8f0', marginBottom: 14 },
  table: { width: '100%', borderCollapse: 'collapse' },
  th: { padding: '9px 12px', textAlign: 'left', fontSize: 11, color: '#64748b', fontWeight: 600, textTransform: 'uppercase', borderBottom: '1px solid #1e2d45' },
  td: { padding: '9px 12px', fontSize: 12.5, color: '#cbd5e1', borderBottom: '1px solid #0b1120' },
  sev: { padding: '2px 9px', borderRadius: 10, fontSize: 11, fontWeight: 600 },
  sevH: { background: '#3f0a0a', color: '#f87171' },
  sevM: { background: '#431407', color: '#fb923c' },
  sevL: { background: '#052e16', color: '#22c55e' },
  footer: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 20, borderTop: '1px solid #1e2d45' },
  btnNext: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '10px 24px', background: '#6366f1', color: '#fff', border: 'none', borderRadius: 7, fontSize: 13, fontWeight: 600, cursor: 'pointer' },
};
