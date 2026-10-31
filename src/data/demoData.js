export const demoStats = [
  { label: 'Monthly recurring revenue', value: '₹4,82,500', change: '+12.8%', tone: 'green', icon: 'revenue' },
  { label: 'Active subscriptions', value: '1,284', change: '+8.2%', tone: 'green', icon: 'active' },
  { label: 'Outstanding invoices', value: '₹68,400', change: '12 invoices', tone: 'amber', icon: 'invoice' },
  { label: 'Total customers', value: '856', change: '+5.4%', tone: 'green', icon: 'customers' },
];

export const subscriptions = [
  { id: 'SUB-1048', customer: 'Acme Technologies', email: 'finance@acme.io', plan: 'Business Annual', amount: '₹24,000', cycle: 'Yearly', next: '12 Nov 2026', status: 'Active' },
  { id: 'SUB-1047', customer: 'Northstar Labs', email: 'accounts@northstar.in', plan: 'Growth Monthly', amount: '₹4,999', cycle: 'Monthly', next: '02 Nov 2026', status: 'Active' },
  { id: 'SUB-1046', customer: 'Pixel & Co.', email: 'hello@pixel.co', plan: 'Starter Monthly', amount: '₹1,499', cycle: 'Monthly', next: '29 Oct 2026', status: 'Past due' },
  { id: 'SUB-1045', customer: 'Greenfield Retail', email: 'billing@greenfield.in', plan: 'Business Annual', amount: '₹24,000', cycle: 'Yearly', next: '18 Nov 2026', status: 'Active' },
  { id: 'SUB-1044', customer: 'Vertex Consulting', email: 'ops@vertex.com', plan: 'Growth Monthly', amount: '₹4,999', cycle: 'Monthly', next: '21 Oct 2026', status: 'Paused' },
];

export const invoices = [
  { id: 'INV-2081', customer: 'Acme Technologies', date: '28 Oct 2026', due: '04 Nov 2026', amount: '₹24,000', status: 'Confirmed' },
  { id: 'INV-2080', customer: 'Northstar Labs', date: '27 Oct 2026', due: '03 Nov 2026', amount: '₹4,999', status: 'Paid' },
  { id: 'INV-2079', customer: 'Pixel & Co.', date: '20 Oct 2026', due: '27 Oct 2026', amount: '₹1,499', status: 'Overdue' },
  { id: 'INV-2078', customer: 'Greenfield Retail', date: '18 Oct 2026', due: '25 Oct 2026', amount: '₹24,000', status: 'Paid' },
];

export const products = [
  { name: 'Starter', type: 'Software', price: '₹1,499', interval: 'Monthly', status: 'Published' },
  { name: 'Growth', type: 'Software', price: '₹4,999', interval: 'Monthly', status: 'Published' },
  { name: 'Business', type: 'Software', price: '₹24,000', interval: 'Yearly', status: 'Published' },
];

export const customers = [
  { name: 'Acme Technologies', email: 'finance@acme.io', subscriptions: 3, total: '₹72,000', status: 'Active' },
  { name: 'Northstar Labs', email: 'accounts@northstar.in', subscriptions: 2, total: '₹9,998', status: 'Active' },
  { name: 'Pixel & Co.', email: 'hello@pixel.co', subscriptions: 1, total: '₹1,499', status: 'Past due' },
  { name: 'Greenfield Retail', email: 'billing@greenfield.in', subscriptions: 2, total: '₹48,000', status: 'Active' },
];