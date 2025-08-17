# Production Deployment Files

This folder contains all files needed for production deployment of the SQL Query Agent.

## 📁 Folder Structure

```
production/
├── config/                    # Configuration files
│   ├── .env.production       # Environment variables template
│   └── uvicorn_config.py     # Uvicorn server configuration
├── scripts/                   # Deployment scripts (Windows)
│   ├── setup_production.bat  # Initial setup
│   ├── start_production.bat  # Start application
│   ├── stop_production.bat   # Stop application
│   ├── health_check.bat      # Health monitoring
│   ├── backup_data.bat       # Data backup
│   ├── update_app.bat        # Update application
│   └── install_service.bat   # Install Windows service
├── docker/                   # Docker deployment
│   ├── Dockerfile           # Application container
│   ├── docker-compose.yml   # Complete stack
│   └── nginx.conf           # Nginx reverse proxy
├── monitoring/               # Monitoring setup
│   ├── prometheus.yml       # Prometheus config
│   └── docker-compose.monitoring.yml
├── requirements-prod.txt     # Production dependencies
└── service.py               # Windows service wrapper
```

## 🚀 Quick Start

### Option 1: Using PowerShell (Recommended)

```powershell
# Setup production environment
.\manage.ps1 setup

# Start application
.\manage.ps1 start

# Check health
.\manage.ps1 health
```

### Option 2: Using Batch Scripts

```batch
# Setup
production\scripts\setup_production.bat

# Start
production\scripts\start_production.bat

# Health check
production\scripts\health_check.bat
```

### Option 3: Docker Deployment

```bash
# Build and run with Docker Compose
cd production/docker
docker-compose up -d

# With monitoring
cd production/monitoring
docker-compose -f docker-compose.monitoring.yml up -d
```

## 📋 Configuration Files

### Environment Variables (`config/.env.production`)

Template for production environment variables. Copy to project root as `.env` and configure:

- **Server settings**: Host, port, workers
- **AI provider**: Ollama/OpenAI configuration
- **Security**: Secret keys, allowed hosts
- **Logging**: Log levels and file paths
- **Performance**: Worker limits, timeouts

### Uvicorn Configuration (`config/uvicorn_config.py`)

Production ASGI server configuration:

- Dynamic worker calculation based on CPU cores
- Optimal performance scaling (2 \* cores + 1, max 4 for Windows)
- Logging to separate files
- Process management and restart policies
- Windows-compatible settings

## 🛠️ Scripts

### Windows Batch Scripts (`scripts/`)

All scripts are designed for Windows environments:

- **`setup_production.bat`**: Complete production environment setup
- **`start_production.bat`**: Start application with Uvicorn
- **`stop_production.bat`**: Gracefully stop the application
- **`health_check.bat`**: Check application health status
- **`backup_data.bat`**: Create timestamped data backups
- **`update_app.bat`**: Update dependencies and restart
- **`install_service.bat`**: Install as Windows Service

### Windows Service (`service.py`)

Optional Windows Service wrapper for running the application as a system service:

```bash
# Install service (as Administrator)
production\scripts\install_service.bat

# Or manually
python production\service.py install
python production\service.py start
```

## 🐳 Docker Deployment

### Standard Deployment (`docker/`)

- **`Dockerfile`**: Multi-stage build for production
- **`docker-compose.yml`**: Complete stack with Redis and Nginx
- **`nginx.conf`**: Reverse proxy with SSL termination

### Monitoring Stack (`monitoring/`)

Includes Prometheus, Grafana, and system monitoring:

```bash
cd production/monitoring
docker-compose -f docker-compose.monitoring.yml up -d
```

Access:

- **Application**: http://localhost:8000
- **Grafana**: http://localhost:3000 (admin/admin123)
- **Prometheus**: http://localhost:9091

## 🔧 Production Features

### Performance

- **Uvicorn ASGI server** with Windows compatibility
- **Redis caching** (optional)
- **Nginx reverse proxy** with SSL termination
- **Load balancing** ready

### Monitoring

- **Health check endpoints**
- **Prometheus metrics** collection
- **Grafana dashboards**
- **System resource monitoring**

### Security

- **Environment-based configuration**
- **SSL/TLS support**
- **Rate limiting** (Nginx)
- **Security headers**

### Reliability

- **Automated backups**
- **Graceful shutdowns**
- **Process monitoring**
- **Auto-restart policies**

## 📊 Monitoring

### Health Checks

```bash
# Manual health check
curl http://localhost:8000/health

# Using script
production\scripts\health_check.bat
```

### Metrics Collection

The application exposes Prometheus metrics at `/metrics` when `ENABLE_METRICS=true`.

### Log Files

- **Application logs**: `logs/app.log`
- **Access logs**: `logs/access.log`
- **Error logs**: `logs/error.log`

## 🔄 Maintenance

### Regular Tasks

```bash
# Create backup
production\scripts\backup_data.bat

# Update application
production\scripts\update_app.bat

# Check system status
.\manage.ps1 status
```

### Backup Management

Automated backup system:

- **Daily**: Application creates incremental backups
- **Weekly**: Use backup script for full backup
- **Retention**: Keeps last 10 backups automatically

## 🚨 Troubleshooting

### Common Issues

1. **Port conflicts**: Check if port 8000 is in use
2. **Virtual environment**: Ensure `.venv` is properly created
3. **Dependencies**: Run update script if packages are missing
4. **Permissions**: Run as Administrator for service installation

### Debug Commands

```powershell
# Check application status
.\manage.ps1 status

# View recent logs
.\manage.ps1 logs

# Test health endpoint
.\manage.ps1 health
```

## 📈 Scaling

### Horizontal Scaling

1. **Load balancer**: Use Nginx or hardware LB
2. **Multiple instances**: Deploy on multiple servers
3. **Shared storage**: Use network storage for data
4. **Redis cluster**: For distributed caching

### Vertical Scaling

1. **Increase resources**: More CPU/RAM
2. **Optimize workers**: Adjust worker count in config
3. **Database tuning**: Optimize data access patterns

## 🔐 Security Checklist

- [ ] Change default secrets in `.env`
- [ ] Configure firewall rules
- [ ] Set up HTTPS/SSL certificates
- [ ] Enable security headers in Nginx
- [ ] Restrict file upload types and sizes
- [ ] Regular security updates
- [ ] Monitor access logs
- [ ] Backup encryption (if needed)

## 📞 Support

For production deployment issues:

1. Check application logs in `logs/` directory
2. Verify configuration in `.env` file
3. Test health endpoint: `http://localhost:8000/health`
4. Review Uvicorn process status
5. Check system resources (CPU, memory, disk)

For additional help, refer to the main `DEPLOYMENT.md` in the project root.
