This file is just meant to be used for reference in the production context. 

# Cronjob setting
To enable the market to be automatically updated, 

paste into `/etc/systemd/system/market-updater.service`: 
```ini
[Unit]
Description=Run market updater

[Service]
Type=oneshot
WorkingDirectory=/home/ec2-user/portfolio-management
EnvironmentFile=/home/ec2-user/portfolio-management/.env
ExecStart=/home/ec2-user/portfolio-management/venv/bin/python /home/ec2-user/portfolio-management/market_updater.py
```


paste into `/etc/systemd/system/market-updater.timer`: 
```ini
[Unit]
Description=Updates market on weekdays

[Timer]
OnCalendar=Mon..Fri 09:00
Persistent=true

[Install]
WantedBy=timers.target
```

finally run to enable the daemon
```sh
sudo systemctl daemon-reload
sudo systemctl enable --now market-updater.timer
systemctl list-timers | grep market-updater
```