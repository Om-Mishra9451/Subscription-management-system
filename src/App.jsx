import { useMemo, useState } from 'react';
import {
  Activity, ArrowDownRight, ArrowUpRight, Bell, Box, CalendarDays, Check,
  ChevronDown, CircleHelp, CreditCard, Download, FileText, LayoutDashboard,
  Menu, MoreHorizontal, Package, Plus, Search, Settings, ShieldCheck,
  Users, Wallet, X, Zap
} from 'lucide-react';
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis } from 'recharts';
import { customers, demoStats, invoices, products, subscriptions } from './data/demoData';

const nav = [
  { label: 'Overview', icon: LayoutDashboard },
  { label: 'Subscriptions', icon: Activity, count: '1,284' },
  { label: 'Products & Plans', icon: Package },
  { label: 'Customers', icon: Users },
  { label: 'Invoices', icon: FileText, count: '12' },
  { label: 'Payments', icon: CreditCard },
  { label: 'Reports', icon: Wallet },
];
const chartData = [
  { month: 'May', revenue: 290 }, { month: 'Jun', revenue: 340 },
  { month: 'Jul', revenue: 315 }, { month: 'Aug', revenue: 390 },
  { month: 'Sep', revenue: 420 }, { month: 'Oct', revenue: 483 },
];
const payments = [
  { name: 'Acme Technologies', detail: 'Annual plan · Today, 10:42 AM', amount: '+₹24,000', initials: 'AT', color: 'lavender' },
  { name: 'Northstar Labs', detail: 'Growth plan · Yesterday', amount: '+₹4,999', initials: 'NL', color: 'mint' },
  { name: 'Greenfield Retail', detail: 'Annual plan · 26 Oct 2026', amount: '+₹24,000', initials: 'GR', color: 'peach' },
];

function Status({ value }) {
  const key = value.toLowerCase().replace(' ', '-');
  return <span className={`status ${key}`}>{value}</span>;
}
function Sidebar({ active, setActive, open, setOpen }) {
  return <>
    {open && <div className="mobile-shade" onClick={() => setOpen(false)} />}
    <aside className={`sidebar ${open ? 'sidebar-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><Zap size={19} fill="currentColor" /></div><span>subscript<span className="brand-dot">.</span></span><button className="icon-btn mobile-close" onClick={() => setOpen(false)}><X size={18}/></button></div>
      <div className="workspace"><div className="workspace-logo">B</div><div><strong>Brightloop Software</strong><small>Workspace</small></div><ChevronDown size={15}/></div>
      <div className="nav-label">WORKSPACE</div>
      <nav>{nav.map(item => { const Icon = item.icon; return <button key={item.label} className={`nav-item ${active === item.label ? 'selected' : ''}`} onClick={() => { setActive(item.label); setOpen(false); }}><Icon size={18}/><span>{item.label}</span>{item.count && <small>{item.count}</small>}</button>; })}</nav>
      <div className="sidebar-bottom">
        <div className="help-card"><div className="help-icon"><CircleHelp size={17}/></div><strong>Need a hand?</strong><p>Visit our help center for tips and guides.</p><button>Get support <span>↗</span></button></div>
        <button className="nav-item"><Settings size={18}/><span>Settings</span></button>
        <div className="profile"><div className="avatar avatar-purple">OM</div><div><strong>Om Mishra</strong><small>Administrator</small></div><MoreHorizontal size={19}/></div>
      </div>
    </aside>
  </>;
}
function Header({ active, setOpen }) {
  return <header className="topbar"><div className="top-left"><button className="icon-btn menu-btn" onClick={() => setOpen(true)}><Menu size={20}/></button><span className="crumb">Workspace</span><span className="crumb-slash">/</span><strong>{active}</strong></div><div className="top-actions"><div className="searchbox"><Search size={16}/><input placeholder="Search anything..." /><kbd>⌘ K</kbd></div><button className="icon-btn notification"><Bell size={18}/><i/></button><div className="avatar avatar-purple top-avatar">OM</div></div></header>;
}
function StatCard({ item, index }) {
  const icons = [Wallet, Activity, FileText, Users]; const Icon = icons[index];
  return <div className="stat-card"><div className="stat-top"><span>{item.label}</span><div className={`stat-icon stat-icon-${index}`}><Icon size={17}/></div></div><div className="stat-value">{item.value}</div><div className="stat-foot"><span className={`change ${item.tone}`}>{item.tone === 'amber' ? <CalendarDays size={13}/> : <ArrowUpRight size={14}/>} {item.change}</span><span className="vs">vs last month</span></div></div>;
}
function Overview() {
  return <><div className="welcome-row"><div><div className="eyebrow">SATURDAY, OCTOBER 31, 2026</div><h1>Good morning, Om <span>✦</span></h1><p>Here's what's happening with your subscriptions today.</p></div><button className="button button-primary"><Plus size={17}/> Create subscription</button></div>
    <div className="stats-grid">{demoStats.map((item, i) => <StatCard key={item.label} item={item} index={i}/>)}</div>
    <div className="dashboard-grid"><section className="panel revenue-panel"><div className="panel-heading"><div><h2>Revenue overview</h2><p>Keep an eye on your recurring revenue</p></div><button className="select-button">Last 6 months <ChevronDown size={14}/></button></div><div className="revenue-total"><strong>₹4,82,500</strong><span className="change green"><ArrowUpRight size={14}/> 12.8%</span></div><div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><BarChart data={chartData} barSize={29}><CartesianGrid vertical={false} stroke="#edf0f5" strokeDasharray="4 4"/><XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill: '#98a1b2', fontSize: 12 }} dy={10}/><Tooltip cursor={{fill:'#f5f4ff'}} formatter={(v) => [`₹${v},000`, 'Revenue']}/><Bar dataKey="revenue" fill="#7667e8" radius={[6,6,0,0]}/></BarChart></ResponsiveContainer></div><div className="chart-legend"><span><i/> Recurring revenue</span><small>Values shown in INR</small></div></section>
      <section className="panel activity-panel"><div className="panel-heading"><div><h2>Recent payments</h2><p>Your latest successful transactions</p></div><button className="more-btn"><MoreHorizontal size={20}/></button></div><div className="payment-list">{payments.map(p=><div className="payment-row" key={p.name}><div className={`payment-avatar ${p.color}`}>{p.initials}</div><div className="payment-info"><strong>{p.name}</strong><small>{p.detail}</small></div><strong className="payment-amount">{p.amount}</strong></div>)}</div><button className="text-link">View all payments <span>→</span></button></section></div>
    <section className="panel table-panel"><div className="panel-heading"><div><h2>Recent subscriptions</h2><p>A quick look at your latest customer subscriptions</p></div><button className="text-link">View all <span>→</span></button></div><SubscriptionTable rows={subscriptions.slice(0,4)}/></section>
  </>;
}
function SubscriptionTable({ rows }) {
  return <div className="table-scroll"><table><thead><tr><th>SUBSCRIPTION</th><th>CUSTOMER</th><th>PLAN</th><th>AMOUNT</th><th>NEXT BILLING</th><th>STATUS</th><th></th></tr></thead><tbody>{rows.map(s=><tr key={s.id}><td><strong className="id-text">{s.id}</strong></td><td><div className="customer-cell"><div className="mini-avatar">{s.customer.slice(0,1)}</div><div><strong>{s.customer}</strong><small>{s.email}</small></div></div></td><td>{s.plan}</td><td className="amount-cell">{s.amount}<small> / {s.cycle.toLowerCase()}</small></td><td>{s.next}</td><td><Status value={s.status}/></td><td><button className="more-btn"><MoreHorizontal size={18}/></button></td></tr>)}</tbody></table></div>;
}
function GenericPage({ active }) {
  const [query, setQuery] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [newName, setNewName] = useState('');
  const config = {
    Subscriptions: { title: 'Subscriptions', desc: 'Manage plans, renewals and customer subscriptions.', rows: subscriptions, action: 'Create subscription', headers: ['SUBSCRIPTION','CUSTOMER','PLAN','AMOUNT','NEXT BILLING','STATUS'], search: r => `${r.id} ${r.customer} ${r.plan}` },
    'Products & Plans': { title: 'Products & Plans', desc: 'Create products, configure plans and manage pricing.', rows: products, action: 'Create product', headers: ['PRODUCT / PLAN','TYPE','PRICE','BILLING CYCLE','STATUS'], search: r => `${r.name} ${r.type}` },
    Customers: { title: 'Customers', desc: 'View customer accounts and their subscription activity.', rows: customers, action: 'Add customer', headers: ['CUSTOMER','SUBSCRIPTIONS','LIFETIME VALUE','STATUS'], search: r => `${r.name} ${r.email}` },
    Invoices: { title: 'Invoices', desc: 'Track billing, payment status and outstanding invoices.', rows: invoices, action: 'Create invoice', headers: ['INVOICE','CUSTOMER','ISSUED ON','DUE DATE','AMOUNT','STATUS'], search: r => `${r.id} ${r.customer}` },
    Payments: { title: 'Payments', desc: 'Monitor collected payments and transaction history.', rows: payments, action: 'Record payment', headers: ['CUSTOMER','DETAILS','AMOUNT'], search: r => `${r.name} ${r.detail}` },
    Reports: { title: 'Reports', desc: 'Understand recurring revenue and subscription performance.', rows: [], action: 'Export report', headers: [], search: () => true },
  }[active];
  const filtered = config.rows.filter(r => config.search(r).toLowerCase().includes(query.toLowerCase()));
  return <><div className="welcome-row"><div><div className="eyebrow">BRIGHTLOOP WORKSPACE</div><h1>{config.title}</h1><p>{config.desc}</p></div><button className="button button-primary" onClick={() => setShowModal(true)}>{active === 'Reports' ? <Download size={16}/> : <Plus size={17}/>} {config.action}</button></div>
    {active === 'Reports' ? <div className="stats-grid">{demoStats.map((s,i)=><StatCard item={s} index={i} key={s.label}/>)}</div> :
    <section className="panel table-panel generic-table"><div className="table-toolbar"><div className="searchbox"><Search size={16}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder={`Search ${active.toLowerCase()}...`}/></div><button className="select-button"><Download size={15}/> Export</button></div>
    {filtered.length ? <div className="table-scroll"><table><thead><tr>{config.headers.map(h=><th key={h}>{h}</th>)}<th></th></tr></thead><tbody>{filtered.map((r,i)=><tr key={r.id || r.name || i}>{active === 'Subscriptions' ? <><td><strong className="id-text">{r.id}</strong></td><td><div className="customer-cell"><div className="mini-avatar">{r.customer[0]}</div><div><strong>{r.customer}</strong><small>{r.email}</small></div></div></td><td>{r.plan}</td><td className="amount-cell">{r.amount}</td><td>{r.next}</td><td><Status value={r.status}/></td></> :
    active === 'Products & Plans' ? <><td><strong>{r.name}</strong></td><td>{r.type}</td><td className="amount-cell">{r.price}</td><td>{r.interval}</td><td><Status value={r.status}/></td></> :
    active === 'Customers' ? <><td><div className="customer-cell"><div className="mini-avatar">{r.name[0]}</div><div><strong>{r.name}</strong><small>{r.email}</small></div></div></td><td>{r.subscriptions}</td><td className="amount-cell">{r.total}</td><td><Status value={r.status}/></td></> :
    active === 'Invoices' ? <><td><strong className="id-text">{r.id}</strong></td><td>{r.customer}</td><td>{r.date}</td><td>{r.due}</td><td className="amount-cell">{r.amount}</td><td><Status value={r.status}/></td></> :
    <><td><strong>{r.name}</strong></td><td>{r.detail}</td><td className="amount-cell">{r.amount}</td></> }<td><button className="more-btn"><MoreHorizontal size={18}/></button></td></tr>)}</tbody></table></div> : <div className="empty-state">No matching records found.</div>}</section>}
    {showModal && <div className="modal-backdrop" onClick={()=>setShowModal(false)}><div className="modal" onClick={e=>e.stopPropagation()}><div className="modal-head"><h2>{config.action}</h2><button className="icon-btn" onClick={()=>setShowModal(false)}><X size={18}/></button></div><p>This form will be connected to the backend API during integration.</p><label>{active === 'Products & Plans' ? 'Product name' : active === 'Customers' ? 'Customer name' : 'Name'}<input value={newName} onChange={e=>setNewName(e.target.value)} placeholder="Enter a name"/></label><div className="modal-actions"><button className="button button-light" onClick={()=>setShowModal(false)}>Cancel</button><button className="button button-primary" onClick={()=>setShowModal(false)}><Check size={16}/> Done</button></div></div></div>}
  </>;
}
export default function App() {
  const [active, setActive] = useState('Overview');
  const [menuOpen, setMenuOpen] = useState(false);
  const page = useMemo(() => active === 'Overview' ? <Overview/> : <GenericPage active={active}/>, [active]);
  return <div className="app-shell"><Sidebar active={active} setActive={setActive} open={menuOpen} setOpen={setMenuOpen}/><main className="main-area"><Header active={active} setOpen={setMenuOpen}/><div className="page-content">{page}<footer>© 2026 Subscript · Subscription management, made simpler.<span>All systems operational <i/></span></footer></div></main></div>;
}