import { Plus, Bell } from 'lucide-react';

export default function Dashboard({ onNavigate }) {
  const stats = [
    { label: 'Total Projects',   value: '—', cls: '' },
    { label: 'Total Images',     value: '—', cls: '' },
    { label: 'Total Panels',     value: '—', cls: '' },
    { label: 'Defective Panels', value: '—', cls: 'danger' },
    { label: 'Health Rate',      value: '—', cls: 'success' },
  ];

  return (
    <div>
      <div className="topbar">
        <div>
          <div className="page-title">Dashboard</div>
          <div className="page-subtitle">Overview of your solar inspection projects</div>
        </div>
        <div className="flex items-center gap-3">
          <button className="btn btn-outline" style={{ padding: '7px 10px' }}><Bell size={15} /></button>
          <div className="avatar">A</div>
          <span style={{ fontSize: 13, color: '#94a3b8' }}>Admin</span>
          <button className="btn btn-primary" onClick={() => onNavigate('projects')}>
            <Plus size={14} /> New Project
          </button>
        </div>
      </div>

      <div className="stat-grid">
        {stats.map(s => (
          <div key={s.label} className="stat-card">
            <div className="stat-label">{s.label}</div>
            <div className={`stat-value ${s.cls}`}>{s.value}</div>
          </div>
        ))}
      </div>

      <div className="grid-2">
        <div className="card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 220 }}>
          <div className="section-title mb-3">Defect Distribution</div>
          <div style={{ color: '#334155', fontSize: 13, textAlign: 'center', marginTop: 40 }}>
            <div style={{ fontSize: 36, marginBottom: 10 }}>📊</div>
            No inspection data yet.<br />Upload images and run analysis to see results.
          </div>
        </div>

        <div className="card">
          <div className="section-title mb-4">Recent Projects</div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 160, color: '#334155', fontSize: 13, textAlign: 'center' }}>
            <div style={{ fontSize: 36, marginBottom: 10 }}>📁</div>
            No projects yet.<br />
            <button className="btn btn-primary mt-4" onClick={() => onNavigate('projects')}>
              <Plus size={14} /> Create First Project
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
