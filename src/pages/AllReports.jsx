import { ArrowLeft, Download, FileText } from 'lucide-react';
import BrandLogo from '../components/BrandLogo';

export default function AllReports({ projects, onBack }) {
  const completed = projects.filter(p => p.status === 'Completed');

  return (
    <div style={s.page}>
      <div style={s.topbar}>
        <div style={s.logo}><BrandLogo /></div>
        <button style={s.btnBack} onClick={onBack}><ArrowLeft size={13} /> Back to Projects</button>
      </div>

      <div style={s.content}>
        <div style={s.heading}>All Reports</div>
        <div style={s.sub}>Reports generated from all completed inspection projects</div>

        {completed.length === 0 ? (
          <div style={s.empty}>
            <FileText size={48} color="#334155" />
            <div style={{ marginTop: 12, color: '#64748b', fontSize: 14 }}>No completed projects yet.</div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {completed.map((p, i) => (
              <div key={p.id} style={s.reportCard}>
                <div style={s.reportLeft}>
                  <div style={s.reportNum}>{i + 1}</div>
                  <div>
                    <div style={s.reportName}>{p.projectName}</div>
                    <div style={s.reportMeta}>{p.companyName} · {p.location} · {p.date}</div>
                  </div>
                </div>
                <div style={s.reportRight}>
                  <span style={s.badgeGreen}>Completed</span>
                  <button style={s.btnPdf}><Download size={12} /> PDF</button>
                  <button style={s.btnWord}><FileText size={12} /> Word</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

const s = {
  page: { minHeight: '100vh', background: '#ffffff', color: '#0a2545', fontFamily: "'Segoe UI',sans-serif", display: 'flex', flexDirection: 'column' },
  topbar: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 32px', background: '#ffffff', borderBottom: '1px solid #d9e2f0' },
  logo: { display: 'flex', alignItems: 'center', gap: 8 },
  btnBack: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 14px', background: 'transparent', color: '#0a2545', border: '1px solid #d9e2f0', borderRadius: 7, fontSize: 13, cursor: 'pointer' },
  content: { flex: 1, padding: '36px 48px', background: '#ffffff' },
  heading: { fontSize: 24, fontWeight: 700, marginBottom: 4, color: '#0a2545' },
  sub: { fontSize: 13, color: '#55657f', marginBottom: 28 },
  empty: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '80px 0', color: '#55657f' },
  reportCard: { background: '#ffffff', border: '1px solid #d9e2f0', borderRadius: 10, padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', boxShadow: '0 2px 8px rgba(10,37,69,0.04)' },
  reportLeft: { display: 'flex', alignItems: 'center', gap: 16 },
  reportNum: { width: 32, height: 32, borderRadius: '50%', background: '#0a2545', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 700, color: '#fff', flexShrink: 0 },
  reportName: { fontSize: 15, fontWeight: 600, color: '#0a2545', marginBottom: 3 },
  reportMeta: { fontSize: 12, color: '#55657f' },
  reportRight: { display: 'flex', alignItems: 'center', gap: 10 },
  badgeGreen: { display: 'inline-block', padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 600, background: '#eefdf5', color: '#0a2545', border: '1px solid #b7d7c7' },
  btnPdf:  { display: 'inline-flex', alignItems: 'center', gap: 5, padding: '6px 14px', background: '#b91c1c', color: '#fff', border: 'none', borderRadius: 6, fontSize: 12, cursor: 'pointer' },
  btnWord: { display: 'inline-flex', alignItems: 'center', gap: 5, padding: '6px 14px', background: '#0a2545', color: '#fff', border: 'none', borderRadius: 6, fontSize: 12, cursor: 'pointer' },
};
