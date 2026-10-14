export default function DefectSummary() {
  const stats = [
    { label: 'Total Panels',     value: '—', cls: '' },
    { label: 'Healthy Panels',   value: '—', cls: 'success' },
    { label: 'Defective Panels', value: '—', cls: 'danger' },
    { label: 'Health Rate',      value: '—', cls: 'success' },
  ];

  return (
    <div>
      <div className="page-title">Defect Summary</div>
      <div className="page-subtitle">Overall inspection results and defect analysis</div>

      <div className="stat-grid" style={{ gridTemplateColumns: 'repeat(4,1fr)' }}>
        {stats.map(s => (
          <div key={s.label} className="stat-card">
            <div className="stat-label">{s.label}</div>
            <div className={`stat-value ${s.cls}`}>{s.value}</div>
          </div>
        ))}
      </div>

      <div className="grid-2 mt-4">
        <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 200 }}>
          <div className="section-title mb-3">Defect Type Breakdown</div>
          <div style={{ color: '#334155', fontSize: 13, textAlign: 'center', marginTop: 20 }}>
            <div style={{ fontSize: 36, marginBottom: 10 }}>🔍</div>
            No defects detected yet.<br />Run an analysis to see the breakdown.
          </div>
        </div>

        <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 200 }}>
          <div className="section-title mb-3">Severity Distribution</div>
          <div style={{ color: '#334155', fontSize: 13, textAlign: 'center', marginTop: 20 }}>
            <div style={{ fontSize: 36, marginBottom: 10 }}>📉</div>
            No severity data available yet.
          </div>
        </div>
      </div>
    </div>
  );
}
