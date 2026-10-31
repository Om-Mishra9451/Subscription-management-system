# Subscription Management System — Frontend

React + Vite frontend starter for the Subscription Management System hackathon project.

## Requirements
- Node.js 18+
- npm

## Run locally
```bash
npm install
npm run dev
```
Open the local URL printed by Vite (usually http://localhost:5173).

## Production build
```bash
npm run build
npm run preview
```

## Backend integration
The UI currently uses local demo data so it can be previewed before backend APIs are ready.
Set `VITE_API_BASE_URL` in a local `.env` file using `.env.example` as a template.
Do not commit real credentials or secrets.

The API service placeholder is in `src/services/api.js`. Coordinate endpoint paths and request/response formats with the backend developer before connecting it.

## Current screens
- Overview dashboard
- Subscriptions
- Products & plans
- Customers
- Invoices
- Payments
- Reports

## Team
- Om Mishra — Frontend
- Ekalvya — Backend