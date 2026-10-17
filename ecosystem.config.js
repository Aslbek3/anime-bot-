module.exports = {
  apps: [
    {
      name: "qogoz-bot",
      script: "main.py",
      // venv ishlatsangiz: "./venv/bin/python3"
      interpreter: "python3",
      cwd: __dirname,
      autorestart: true,
      restart_delay: 5000,
      max_restarts: 20,
      watch: false,
      env: {
        PYTHONUNBUFFERED: "1",
      },
      out_file: "./logs/out.log",
      error_file: "./logs/error.log",
      merge_logs: true,
      time: true,
    },
  ],
};
