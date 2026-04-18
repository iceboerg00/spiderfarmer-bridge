module.exports = {
  apps: [
    {
      name: 'sf-proxy',
      script: '.venv/bin/python3',
      args: 'main_proxy.py',
      cwd: '/opt/spiderfarmer-bridge',
      autorestart: true,
      watch: false,
      max_memory_restart: '256M',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
    },
    {
      name: 'sf-discovery',
      script: '.venv/bin/python3',
      args: 'main_discovery.py',
      cwd: '/opt/spiderfarmer-bridge',
      autorestart: true,
      watch: false,
      max_memory_restart: '128M',
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
    },
  ],
}
