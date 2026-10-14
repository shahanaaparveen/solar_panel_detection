import { useState } from 'react';
import { Save } from 'lucide-react';

export default function Settings() {
  const [theme, setTheme] = useState('dark');
  const [form, setForm] = useState({
    company: 'Solar Inspect Pvt. Ltd.',
    email: 'admin@solarinspect.com',
    phone: '+91 98765 43210',
    address: 'Chennai, Tamil Nadu, India',
    reportTitle: 'Solar Panel Inspection Report',
    notifications: true,
  });

  const update = (k, v) => setForm(f => ({ ...f, [k]: v }));

  return (
    <div>
      <div className="page-title">Settings</div>
      <div className="page-subtitle">Customize your software preferences</div>

      <div className="grid-2">
        <div className="card">
          <div className="section-title mb-4">Company Details</div>
          {[
            { label: 'Company Name', key: 'company' },
            { label: 'Email', key: 'email' },
            { label: 'Phone', key: 'phone' },
            { label: 'Address', key: 'address' },
          ].map(f => (
            <div key={f.key} className="form-group">
              <label className="form-label">{f.label}</label>
              <input className="form-input" value={form[f.key]} onChange={e => update(f.key, e.target.value)} />
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div className="card">
            <div className="section-title mb-4">Report Template</div>
            <div className="form-group">
              <label className="form-label">Report Title</label>
              <input className="form-input" value={form.reportTitle} onChange={e => update('reportTitle', e.target.value)} />
            </div>
          </div>

          <div className="card">
            <div className="section-title mb-4">Theme</div>
            <div className="flex gap-3">
              {['dark', 'light'].map(t => (
                <button key={t} className={`btn ${theme === t ? 'btn-primary' : 'btn-outline'}`} onClick={() => setTheme(t)} style={{ flex: 1, textTransform: 'capitalize' }}>
                  {t === 'dark' ? '🌙' : '☀️'} {t.charAt(0).toUpperCase() + t.slice(1)} Mode
                </button>
              ))}
            </div>
          </div>

          <div className="card">
            <div className="section-title mb-4">Notifications</div>
            <label style={{ display: 'flex', alignItems: 'center', gap: 12, cursor: 'pointer' }}>
              <div style={{ position: 'relative', width: 44, height: 24 }}>
                <input type="checkbox" checked={form.notifications} onChange={e => update('notifications', e.target.checked)} style={{ opacity: 0, width: 0, height: 0 }} />
                <div style={{ position: 'absolute', inset: 0, background: form.notifications ? '#6366f1' : '#334155', borderRadius: 12, transition: '0.2s' }} />
                <div style={{ position: 'absolute', top: 3, left: form.notifications ? 23 : 3, width: 18, height: 18, background: '#fff', borderRadius: '50%', transition: '0.2s' }} />
              </div>
              <span>Enable email notifications for completed inspections</span>
            </label>
          </div>
        </div>
      </div>

      <div style={{ marginTop: 24, textAlign: 'right' }}>
        <button className="btn btn-primary flex items-center gap-2" style={{ marginLeft: 'auto' }}>
          <Save size={16} /> Save Settings
        </button>
      </div>
    </div>
  );
}
