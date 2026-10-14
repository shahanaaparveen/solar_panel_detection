import { useState } from 'react';
import { ArrowLeft, ArrowRight } from 'lucide-react';
import BrandLogo from '../components/BrandLogo';

const fields = [
  { key: 'companyName',    label: 'Company Name',       placeholder: 'e.g. SunPower Pvt. Ltd.' },
  { key: 'projectName',   label: 'Project Name',        placeholder: 'e.g. Solar Farm – North' },
  { key: 'address',       label: 'Address',             placeholder: 'Street address' },
  { key: 'location',      label: 'Location / City',     placeholder: 'e.g. Chennai, Tamil Nadu' },
  { key: 'inspectorName', label: 'Inspector Name',      placeholder: 'e.g. Rahul Sharma' },
  { key: 'contactEmail',  label: 'Contact Email',       placeholder: 'inspector@company.com' },
  { key: 'contactPhone',  label: 'Contact Phone',       placeholder: '+91 98765 43210' },
  { key: 'farmSize',      label: 'Farm Size (acres)',   placeholder: 'e.g. 50' },
  { key: 'totalPanels',   label: 'Expected Total Panels', placeholder: 'e.g. 2000' },
  { key: 'notes',         label: 'Additional Notes',   placeholder: 'Any special instructions...' },
];

export default function NewProjectInfo({ onBack, onCreate }) {
  const [form, setForm] = useState({});
  const [errors, setErrors] = useState({});

  const update = (k, v) => { setForm(f => ({ ...f, [k]: v })); setErrors(e => ({ ...e, [k]: '' })); };

  const validate = () => {
    const req = ['companyName', 'projectName', 'location', 'inspectorName'];
    const errs = {};
    req.forEach(k => { if (!form[k]?.trim()) errs[k] = 'Required'; });
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleNext = () => { if (validate()) onCreate(form); };

  return (
    <div style={s.page}>
      {/* Topbar */}
      <div style={s.topbar}>
        <div style={s.logo}>
          <BrandLogo />
        </div>
        <button style={s.btnBack} onClick={onBack}><ArrowLeft size={14} /> Back to Projects</button>
      </div>

      <div style={s.body}>
        <div style={s.card}>
          <div style={s.cardHead}>
            <div style={s.step}>Step 1 of 5</div>
            <div style={s.title}>New Inspection Project</div>
            <div style={s.sub}>Fill in the project details. These will appear in the final report.</div>
          </div>

          <div style={s.grid}>
            {fields.map(f => (
              <div key={f.key} style={f.key === 'notes' ? { ...s.formGroup, gridColumn: '1 / -1' } : s.formGroup}>
                <label style={s.label}>{f.label} {['companyName','projectName','location','inspectorName'].includes(f.key) && <span style={{ color: '#ef4444' }}>*</span>}</label>
                {f.key === 'notes' ? (
                  <textarea
                    style={{ ...s.input, height: 72, resize: 'vertical' }}
                    placeholder={f.placeholder}
                    value={form[f.key] || ''}
                    onChange={e => update(f.key, e.target.value)}
                  />
                ) : (
                  <input
                    style={{ ...s.input, borderColor: errors[f.key] ? '#ef4444' : undefined }}
                    placeholder={f.placeholder}
                    value={form[f.key] || ''}
                    onChange={e => update(f.key, e.target.value)}
                  />
                )}
                {errors[f.key] && <div style={s.err}>{errors[f.key]}</div>}
              </div>
            ))}
          </div>

          <div style={s.footer}>
            <button style={s.btnOutline} onClick={onBack}>Cancel</button>
            <button style={s.btnPrimary} onClick={handleNext}>Next — Upload Images <ArrowRight size={14} /></button>
          </div>
        </div>
      </div>
    </div>
  );
}

const s = {
  page: { minHeight: '100vh', background: '#ffffff', color: '#0a2545', fontFamily: "'Segoe UI',sans-serif", display: 'flex', flexDirection: 'column' },
  topbar: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 32px', background: '#ffffff', borderBottom: '1px solid #d9e2f0' },
  logo: { display: 'flex', alignItems: 'center', gap: 8 },
  btnBack: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 14px', background: 'transparent', color: '#0a2545', border: '1px solid #d9e2f0', borderRadius: 7, fontSize: 13, cursor: 'pointer' },
  body: { flex: 1, display: 'flex', justifyContent: 'center', padding: '40px 24px', background: '#ffffff' },
  card: { width: '100%', maxWidth: 820, background: '#ffffff', borderRadius: 14, border: '1px solid #d9e2f0', padding: '36px 40px', boxShadow: '0 2px 8px rgba(10,37,69,0.04)' },
  cardHead: { marginBottom: 28 },
  step: { fontSize: 11, color: '#0a2545', fontWeight: 700, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 },
  title: { fontSize: 22, fontWeight: 700, marginBottom: 4, color: '#0a2545' },
  sub: { fontSize: 13, color: '#55657f' },
  grid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px 24px', marginBottom: 32 },
  formGroup: {},
  label: { display: 'block', fontSize: 12, color: '#55657f', marginBottom: 5, fontWeight: 500 },
  input: { width: '100%', padding: '10px 13px', background: '#fff', border: '1px solid #d9e2f0', borderRadius: 7, color: '#0a2545', fontSize: 13, outline: 'none', fontFamily: 'inherit', boxSizing: 'border-box' },
  err: { fontSize: 11, color: '#b91c1c', marginTop: 3 },
  footer: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 20, borderTop: '1px solid #d9e2f0' },
  btnPrimary: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '10px 22px', background: '#0a2545', color: '#fff', border: 'none', borderRadius: 7, fontSize: 13, fontWeight: 600, cursor: 'pointer' },
  btnOutline: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '10px 18px', background: 'transparent', color: '#0a2545', border: '1px solid #d9e2f0', borderRadius: 7, fontSize: 13, cursor: 'pointer' },
};
