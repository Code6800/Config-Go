// PM2 Ecosystem Configuration for WinDoorPro Backend
// This file helps manage the backend as a service

module.exports = {
  apps: [{
    name: 'windoorpro-backend',
    script: 'server.py',
    interpreter: '/usr/bin/python3',
    // If using virtual environment, use the interpreter path:
    // interpreter: '/var/www/jopp/backend/venv/bin/python',
    args: '-m uvicorn server:app --host 0.0.0.0 --port 8000',
    cwd: '/var/www/jopp/backend',
    // Or use absolute path:
    // cwd: __dirname,
    instances: 1,
    exec_mode: 'fork',
    env: {
      NODE_ENV: 'production',
      PYTHONUNBUFFERED: '1'
    },
    error_file: './logs/error.log',
    out_file: './logs/out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    merge_logs: true,
    autorestart: true,
    watch: false,
    max_memory_restart: '500M',
    // Environment variables (or use .env file)
    // env_production: {
    //   NODE_ENV: 'production'
    // }
  }]
};

// Usage:
// 1. Install PM2: npm install -g pm2
// 2. Start: pm2 start ecosystem.config.js
// 3. Save: pm2 save
// 4. Enable startup: pm2 startup (follow instructions)
// 5. View logs: pm2 logs windoorpro-backend
// 6. Restart: pm2 restart windoorpro-backend
// 7. Stop: pm2 stop windoorpro-backend

