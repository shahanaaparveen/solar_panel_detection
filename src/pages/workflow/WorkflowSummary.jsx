import { ArrowRight } from 'lucide-react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts';

const defectTypes = [
  { name: 'Hotspot',          value: 4,  color: '#ef4444' },
  { name: 'Bird Droppings',   value: 3,  color: '#f59e0b' },
  { name: 'Loose Connection', value: 2,  color: '#3b82f6' },
  { name: 'Reverse Bias',     value: 1,  color: '#8b5cf6' },
  { name: 'Leaf Shading',     value: 1,  color: '#10b981' },
];

const severityData = [
  { name: 'High',   value: 7, color: '#ef4444' },
  { name: 'Medium', value: 2, color: '#f59e0b' },
  { name: 'Low',    value: 2, color: '#10b981' },
];

const tt = { contentStyle: { background: '#111827', border: '1px solid #1e2d45', borderRadius: 8, color: '#e2e8f0', fontSize: 12 } };

export default function WorkflowSummary({ project, onNext }) {
  const totalPanels = project.rgbResults?.reduce((s, r) => s + r.panels.length, 0) || 0;
  const defective = defectTypes.reduce((s, d) => s + d.value, 0);
  const healthy = Math.max(0, totalPanels - defective);
  const healthRate = totalPanels > 0 ? ((healthy / totalPanels) * 100).toFixed(1) : '—';

  return (
    <div>
      <div style={s.pageTitle}>Defect Summary</div>
      <div style={s.pageSub}>Complete analysis of all detected defects across {project.projectName}</div>

      {/* Stats */}
      <div style={s.statsRow}>
        {[
          { label: 'Total Panels',     value: totalPanels || '—', color: '#e2e8f0' },
          { label: 'Healthy Panels',   value: totalPanels ? healthy : '—', color: '#22c55e' },
          { label: 'Defective Panels', value: defective, color: '#ef4444' },
          { label: 'Health Rate',      value: totalPanels ? `${healthRate}%` : '—', color: '#22c55e' },
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

        {/* Severity pie */}
        <div style={s.card}>
          <div style={s.cardTitle}>Severity Distribution</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
            <ResponsiveContainer width={160} height={160}>
              <PieChart>
                <Pie data={severityData} cx="50%" cy="50%" innerRadius={42} outerRadius={72} dataKey="value" paddingAngle={2}>
                  {severityData.map((e, i) => <Cell key={i} fill={e.color} />)}
                </Pie>
                <Tooltip {...tt} />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
              {severityData.map(d => (
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
            <tr>{['Defect Type', 'Count', 'Percentage', 'Severity'].map(h => <th key={h} style={s.th}>{h}</th>)}</tr>
          </thead>
          <tbody>
            {defectTypes.map(d => (
              <tr key={d.name}>
                <td style={s.td}><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: d.color, marginRight: 8 }} />{d.name}</td>
                <td style={s.td}>{d.value}</td>
                <td style={s.td}>{((d.value / defective) * 100).toFixed(1)}%</td>
                <td style={s.td}><span style={{ ...s.sev, ...(d.value >= 3 ? s.sevH : d.value === 2 ? s.sevM : s.sevL) }}>{d.value >= 3 ? 'High' : d.value === 2 ? 'Medium' : 'Low'}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={s.footer}>
        <span style={{ fontSize: 13, color: '#64748b' }}>Analysis complete for {project.projectName}</span>
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
