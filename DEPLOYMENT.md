# Deployment Guide

## Overview

This guide covers deploying the Swing Trading System to a production VPS.

## Prerequisites

- Ubuntu 22.04+ LTS
- Docker 24+ and Docker Compose v2
- Domain name with DNS pointing to VPS
- SSL certificates (Let's Encrypt recommended)
- PostgreSQL 16 (or use Docker Compose)

## Quick Start with Docker Compose

### 1. Clone Repository

```bash
git clone <repository-url> /opt/swing-trading
cd /opt/swing-trading
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your credentials
nano .env
```

Required settings:
```env
ANGEL_ONE_API_KEY=your_api_key
ANGEL_ONE_CLIENT_ID=your_client_id
ANGEL_ONE_PASSWORD=your_password
ANGEL_ONE_TOTP_SECRET=your_totp_secret
TRADING_MODE=DRY_RUN
TOTAL_PORTFOLIO_CAPITAL=100000
POSTGRES_PASSWORD=secure_random_password
```

### 3. Start Services

```bash
docker-compose up -d
```

### 4. Verify Deployment

```bash
# Check health
curl https://trading.yourdomain.com/api/health

# View logs
docker-compose logs -f app
```

## Manual Deployment (Systemd)

### 1. System Setup

```bash
# Create user
sudo useradd -r -s /bin/bash -d /opt/swing-trading appuser

# Create directories
sudo mkdir -p /opt/swing-trading /opt/swing-trading/logs /opt/swing-trading/data
sudo chown -R appuser:appuser /opt/swing-trading
```

### 2. Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.12
sudo apt install -y python3.12 python3.12-venv python3.12-dev

# Install PostgreSQL
sudo apt install -y postgresql-16 postgresql-client-16

# Install nginx
sudo apt install -y nginx

# Install certbot for SSL
sudo apt install -y certbot python3-certbot-nginx
```

### 3. Database Setup

```bash
sudo -u postgres psql -c "CREATE DATABASE trading;"
sudo -u postgres psql -c "CREATE USER trading_user WITH ENCRYPTED PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE trading TO trading_user;"
```

### 4. Application Setup

```bash
cd /opt/swing-trading

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
nano .env

# Run migrations
alembic upgrade head

# Seed initial data
python app/scripts/seed.py
```

### 5. Configure Systemd Service

```bash
sudo cp deployment/swing-trading.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable swing-trading
sudo systemctl start swing-trading
sudo systemctl status swing-trading
```

### 6. Configure Nginx

```bash
sudo cp deployment/nginx.conf /etc/nginx/sites-available/swing-trading
sudo ln -s /etc/nginx/sites-available/swing-trading /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 7. SSL Certificate

```bash
sudo certbot --nginx -d trading.yourdomain.com
# Follow prompts, select redirect option
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ANGEL_ONE_API_KEY` | Yes | - | Angel One API key |
| `ANGEL_ONE_CLIENT_ID` | Yes | - | Angel One client ID |
| `ANGEL_ONE_PASSWORD` | Yes | - | Angel One password |
| `ANGEL_ONE_TOTP_SECRET` | Yes | - | TOTP secret for 2FA |
| `TRADING_MODE` | No | `DRY_RUN` | `DRY_RUN` or `LIVE` |
| `TOTAL_PORTFOLIO_CAPITAL` | No | `100000` | Total capital in INR |
| `MAX_RISK_PERCENT` | No | `0.01` | Max risk per trade (1%) |
| `MAX_DAILY_LOSS_PERCENT` | No | `0.02` | Max daily loss (2%) |
| `MAX_OPEN_POSITIONS` | No | `3` | Max concurrent positions |
| `MAX_STOP_LOSS_PERCENT` | No | `0.08` | Max stop loss distance (8%) |
| `MIN_RISK_REWARD` | No | `2.0` | Minimum risk/reward ratio |
| `SIGNAL_EXECUTION_TIME` | No | `15:45` | Daily run time (IST) |
| `TIMEZONE` | No | `Asia/Kolkata` | Timezone |
| `DATABASE_URL` | No | `sqlite:///./trading.db` | Database connection string |
| `LOG_LEVEL` | No | `INFO` | Logging level |

### Risk Settings (per account)

Can be updated via API:
- `max_risk_percent`
- `max_daily_loss_percent`
- `max_open_positions`
- `max_stop_loss_percent`
- `min_risk_reward`
- `swing_low_lookback`
- `event_exclusion_window`
- `daily_loss_action`
- `max_position_concentration_percent`
- `max_sector_concentration_percent`

## Monitoring

### Health Checks

```bash
# Basic health
curl https://trading.yourdomain.com/api/health

# Detailed checks
curl https://trading.yourdomain.com/api/health | jq .

# Readiness probe
curl https://trading.yourdomain.com/api/health/ready

# Liveness probe
curl https://trading.yourdomain.com/api/health/live
```

### Prometheus Metrics

```bash
curl https://trading.yourdomain.com/api/metrics
```

Key metrics:
- `trading_runs_total` - Trading runs by status
- `signals_generated_total` - Signals by decision
- `orders_placed_total` - Orders by status
- `positions_open` - Open positions per symbol
- `portfolio_value_inr` - Portfolio value
- `daily_pnl_inr` - Daily P&L
- `trade_r_multiple` - Trade R-multiple distribution
- `max_drawdown_pct` - Maximum drawdown

### Logs

```bash
# Application logs
tail -f /opt/swing-trading/logs/trading.log

# Systemd logs
journalctl -u swing-trading -f

# Nginx logs
tail -f /var/log/nginx/swing-trading-access.log
tail -f /var/log/nginx/swing-trading-error.log
```

## Backup Strategy

### Database Backup

```bash
#!/bin/bash
# /opt/swing-trading/scripts/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/swing-trading/backups"
mkdir -p $BACKUP_DIR

# Database dump
pg_dump -U trading_user -h localhost trading | gzip > $BACKUP_DIR/trading_$DATE.sql.gz

# Keep last 30 days
find $BACKUP_DIR -name "trading_*.sql.gz" -mtime +30 -delete

# Upload to S3 (optional)
# aws s3 cp $BACKUP_DIR/trading_$DATE.sql.gz s3://your-bucket/backups/
```

Add to crontab:
```bash
0 2 * * * /opt/swing-trading/scripts/backup.sh
```

### Application Backup

```bash
# Backup config and data
tar -czf /opt/swing-trading/backups/app_$(date +%Y%m%d).tar.gz \
  /opt/swing-trading/.env \
  /opt/swing-trading/data \
  /opt/swing-trading/logs
```

## Updates

### Docker Compose

```bash
cd /opt/swing-trading
git pull
docker-compose build --no-cache
docker-compose up -d
```

### Systemd

```bash
cd /opt/swing-trading
git pull
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
sudo systemctl restart swing-trading
```

## Troubleshooting

### Common Issues

1. **Database connection failed**
   - Check PostgreSQL is running: `systemctl status postgresql`
   - Verify credentials in `.env`
   - Check firewall: `sudo ufw status`

2. **Angel One authentication fails**
   - Verify TOTP secret is correct
   - Check system time is synchronized: `timedatectl status`
   - Check API key permissions

3. **Market data not updating**
   - Check Yahoo Finance API limits
   - Verify network connectivity
   - Check logs for `DataValidationError`

4. **Scheduler not running**
   - Check timezone: `timedatectl`
   - Verify `SIGNAL_EXECUTION_TIME` format (HH:MM)
   - Check logs for APScheduler errors

5. **High memory usage**
   - Reduce `yfinance` cache TTL
   - Limit `MAX_OPEN_POSITIONS`
   - Check for memory leaks in custom code

### Debug Mode

```bash
# Enable debug logging
echo "LOG_LEVEL=DEBUG" >> .env
docker-compose restart app
# or
sudo systemctl restart swing-trading
```

## Security Checklist

- [ ] Change default PostgreSQL password
- [ ] Use strong `POSTGRES_PASSWORD` in `.env`
- [ ] Enable firewall: `sudo ufw enable && sudo ufw allow 22 && sudo ufw allow 443`
- [ ] Disable root SSH login
- [ ] Use SSH keys only
- [ ] Configure fail2ban for SSH
- [ ] Regular security updates: `apt update && apt upgrade -y`
- [ ] Monitor audit logs via `/api/logs`
- [ ] Never commit `.env` to git
- [ ] Rotate API keys periodically
- [ ] Restrict `/api/metrics` to monitoring network only

## Rollback Procedure

```bash
# Docker Compose
docker-compose down
git checkout <previous-tag>
docker-compose up -d

# Systemd
sudo systemctl stop swing-trading
git checkout <previous-tag>
source venv/bin/activate
pip install -r requirements.txt
alembic downgrade -1  # if migration issues
sudo systemctl start swing-trading
```

## Support

For issues:
1. Check logs first
2. Verify health endpoint
3. Check GitHub issues
4. Contact system administrator