# SQL Query Agent - Production Deployment Guide for Windows

## Prerequisites

1. **Windows Server or Windows 10/11**
2. **Python 3.8+** installed
3. **Ollama Server** running at `http://192.168.105.58:11434`
4. **Administrator privileges** (for Windows Service installation)

## Quick Start Production Deployment

### 1. Initial Setup

```bash
# Clone or download your application
cd "F:\AI\sales com query generation\sql-query-agent"

# Run production setup script
production\scripts\setup_production.bat
```

### 2. Configure Environment

Edit the `.env` file created during setup:

```env
# Application Settings
ENVIRONMENT=production
DEBUG=False
LOG_LEVEL=INFO

# Server Configuration
HOST=0.0.0.0
PORT=8000

# AI Provider Settings
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://192.168.105.58:11434

# Update other settings as needed
```

### 3. Add Training Data

Place your training data file:

```
data/srf_sql_pairs.jsonl
```

### 4. Start Production Server

```bash
# Using PowerShell (Recommended)
production\manage.ps1 start

# OR using batch scripts
production\scripts\start_production.bat

# Check health
production\manage.ps1 health
# OR
production\scripts\health_check.bat
```

Your application will be available at: `http://localhost:8000`

## Advanced Deployment Options

### Option 1: PowerShell Management (Recommended)

```powershell
# Setup, start, monitor
production\manage.ps1 setup
production\manage.ps1 start
production\manage.ps1 health
production\manage.ps1 status
```

### Option 2: Manual Process Management

```bash
# Start
production\scripts\start_production.bat

# Stop
production\scripts\stop_production.bat

# Health check
production\scripts\health_check.bat
```

### Option 3: Windows Service (Recommended for Production)

```bash
# Install as Windows Service (Run as Administrator)
production\scripts\install_service.bat

# Manage service
python production\service.py start
python production\service.py stop
python production\service.py restart
```

### Option 4: Docker Deployment

```bash
# Standard deployment
cd production\docker
docker-compose up -d

# With monitoring
cd production\monitoring
docker-compose -f docker-compose.monitoring.yml up -d
```

## Production Configuration

### Uvicorn Configuration (`production/config/uvicorn_config.py`)

Key production settings:

- **Workers**: Single worker for Windows compatibility
- **Timeout**: 30 seconds graceful shutdown
- **Logging**: Separate access and error logs
- **Process management**: Windows-compatible settings

### Security Considerations

1. **Change default secrets** in `.env` file
2. **Configure firewall** to allow only necessary ports
3. **Use HTTPS** in production (configure reverse proxy)
4. **Restrict file upload sizes** and types
5. **Enable logging** and monitoring

### Performance Tuning

1. **Adjust worker count** in `uvicorn_config.py`
2. **Configure memory limits**
3. **Enable Redis caching** (optional)
4. **Monitor resource usage**

## Monitoring and Maintenance

### Log Files

- **Application logs**: `logs/app.log`
- **Access logs**: `logs/access.log`
- **Error logs**: `logs/error.log`

### Health Monitoring

```bash
# Automated health check
scripts\health_check.bat

# Or check manually
curl http://localhost:8000/health
```

### Backup and Updates

```bash
# Create backup
scripts\backup_data.bat

# Update application
scripts\update_app.bat
```

## Reverse Proxy Setup (Optional)

For production environments, consider using IIS or Nginx as a reverse proxy:

### IIS Configuration

1. Install IIS with Application Request Routing
2. Configure reverse proxy to `http://localhost:8000`
3. Add SSL certificate
4. Configure URL rewrite rules

### Nginx Configuration (if using Nginx on Windows)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Troubleshooting

### Common Issues

1. **Port already in use**

   ```bash
   netstat -ano | findstr :8000
   taskkill /PID <PID> /F
   ```

2. **Virtual environment issues**

   ```bash
   # Recreate virtual environment
   rmdir /s .venv
   python -m venv .venv
   scripts\setup_production.bat
   ```

3. **Permission errors**

   - Run scripts as Administrator
   - Check file permissions in logs directory

4. **Ollama connection issues**
   - Verify Ollama server is running
   - Check network connectivity
   - Update OLLAMA_BASE_URL in .env

### Performance Issues

1. **High memory usage**

   - Reduce worker count
   - Enable memory profiling
   - Check for memory leaks in logs

2. **Slow response times**
   - Check AI provider response times
   - Monitor database performance
   - Review application logs

## Scaling Considerations

### Horizontal Scaling

1. **Load balancer** (IIS ARR, Nginx, or hardware LB)
2. **Multiple application instances**
3. **Shared storage** for training data
4. **Redis cluster** for caching

### Vertical Scaling

1. **Increase server resources** (CPU, RAM)
2. **Optimize worker configuration**
3. **Database performance tuning**

## Security Checklist

- [ ] Changed default secrets in .env
- [ ] Configured firewall rules
- [ ] Set up HTTPS/SSL
- [ ] Restricted file upload types and sizes
- [ ] Enabled logging and monitoring
- [ ] Regular security updates
- [ ] Network access controls
- [ ] Data backup procedures

## Support and Maintenance

### Regular Tasks

1. **Daily**: Check application health and logs
2. **Weekly**: Review performance metrics and backup data
3. **Monthly**: Update dependencies and security patches
4. **Quarterly**: Review and optimize configuration

### Monitoring Alerts

Set up monitoring for:

- Application availability (health endpoint)
- Resource usage (CPU, memory, disk)
- Error rates in logs
- Response times
- AI provider connectivity

For additional support, check the application logs and ensure all dependencies are properly installed.
