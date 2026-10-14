import { ArrowLeft, Image, Thermometer, GitMerge, BarChart2, FileText, Play, Sun } from 'lucide-react';
import BrandLogo from '../components/BrandLogo';

const navItems = [
  { key: 'overview',  label: 'Project Overview',        icon: Sun },
  { key: 'thermal',   label: 'Uploaded Thermal Images', icon: Thermometer },
  { key: 'rgb',       label: 'Uploaded RGB Images',     icon: Image },
  { key: 'defects',   label: 'Defects Found',           icon: GitMerge },
  { key: 'summary',   label: 'Defect Summary',          icon: BarChart2 },
  { key: 'report',    label: 'Report',                  icon: FileText },
];

export default function ProjectDetail({ project, onBack, onContinue }) {
  const p = project || {};

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return d.toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div style={s.page}>
      {/* Topbar */}
      <div style={s.topbar}>
        <div style={s.logo}>
          <BrandLogo compact size={0.75} style={{ maxHeight: '32px', width: 'auto' }} />
        </div>
        <button style={s.btnBack} onClick={onBack}>
          <ArrowLeft size={14} /> Back to Projects
        </button>
      </div>

      <div style={s.body}>
        {/* Left panel */}
        <div style={s.leftPanel}>
          <div style={s.panelTitle}>Project Menu</div>
          {navItems.map(({ key, label, icon: Icon }) => (
            <div key={key} style={s.navItem}>
              <Icon size={14} color="#64748b" />
              <span>{label}</span>
            </div>
          ))}
          <div style={{ marginTop: 'auto', paddingTop: 24 }}>
            <button style={s.btnContinue} onClick={onContinue}>
              <Play size={14} /> Continue Workflow
            </button>
          </div>
        </div>

        {/* Main content */}
        <div style={s.main}>
          <div style={s.pageTitle}>{p.projectName}</div>
          <div style={s.pageSub}>Project Details & Overview</div>

          <div style={s.infoGrid}>
            {[
              { label: 'Company Name',    value: p.companyName || '—' },
              { label: 'Project Name',    value: p.projectName || '—' },
              { label: 'Location',        value: p.location || '—' },
              { label: 'Inspector',       value: p.inspectorName || '—' },
              { label: 'Contact Email',   value: p.contactEmail || '—' },
              { label: 'Contact Phone',   value: p.contactPhone || '—' },
              { label: 'Farm Size',       value: p.farmSize ? `${p.farmSize} acres` : '—' },
              { label: 'Expected Panels', value: p.totalPanels || '—' },
              { label: 'Date Created',    value: formatDate(p.createdAt || p.date) },
              { label: 'Status',          value: p.status || 'In Progress' },
            ].map(item => (
              <div key={item.label} style={s.infoCard}>
                <div style={s.infoLabel}>{item.label}</div>
                <div style={s.infoValue}>{item.value}</div>
              </div>
            ))}
          </div>

          {p.notes && (
            <div style={s.notesBox}>
              <div style={s.infoLabel}>Notes</div>
              <div style={{ fontSize: 13, color: '#334155', marginTop: 6 }}>{p.notes}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const s = {
  page: { minHeight: '100vh', background: '#ffffff', color: '#0a2545', fontFamily: "'Segoe UI',sans-serif", display: 'flex', flexDirection: 'column' },
  topbar: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 28px', minHeight: '48px', background: '#ffffff', borderBottom: '1px solid #d9e2f0' },
  logo: { display: 'flex', alignItems: 'center', gap: 8, maxHeight: '34px' },
  btnBack: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 14px', background: 'transparent', color: '#0a2545', border: '1px solid #d9e2f0', borderRadius: 6, fontSize: 13, cursor: 'pointer' },
  body: { flex: 1, display: 'flex', background: '#ffffff' },
  leftPanel: { width: 220, background: '#ffffff', borderRight: '1px solid #d9e2f0', padding: '24px 12px', display: 'flex', flexDirection: 'column', gap: 2 },
  panelTitle: { fontSize: 10, color: '#55657f', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, padding: '0 8px', marginBottom: 8 },
  navItem: { display: 'flex', alignItems: 'center', gap: 9, padding: '9px 12px', borderRadius: 7, fontSize: 12.5, color: '#0a2545', cursor: 'pointer' },
  btnContinue: { display: 'flex', alignItems: 'center', gap: 6, width: '100%', padding: '10px 14px', background: '#0a2545', color: '#fff', border: 'none', borderRadius: 7, fontSize: 13, fontWeight: 600, cursor: 'pointer', justifyContent: 'center' },
  main: { flex: 1, padding: '32px 40px', overflowY: 'auto', background: '#ffffff' },
  pageTitle: { fontSize: 22, fontWeight: 700, marginBottom: 4, color: '#0a2545' },
  pageSub: { fontSize: 13, color: '#55657f', marginBottom: 28 },
  infoGrid: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginBottom: 20 },
  infoCard: { background: '#ffffff', border: '1px solid #d9e2f0', borderRadius: 9, padding: '14px 16px', boxShadow: '0 2px 8px rgba(10,37,69,0.04)' },
  infoLabel: { fontSize: 10, color: '#55657f', textTransform: 'uppercase', letterSpacing: 0.5, fontWeight: 600 },
  infoValue: { fontSize: 14, fontWeight: 600, color: '#0a2545', marginTop: 4 },
  notesBox: { background: '#ffffff', border: '1px solid #d9e2f0', borderRadius: 9, padding: '14px 16px', marginBottom: 20 },
};
