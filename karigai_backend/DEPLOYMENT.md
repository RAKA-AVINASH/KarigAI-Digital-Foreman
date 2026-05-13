# KarigAI Deployment Guide

## Overview

This guide covers production deployment of the KarigAI backend system using Docker containers, including monitoring, logging, and disaster recovery procedures.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB+ RAM
- 20GB+ disk space
- SSL certificates (for HTTPS)

## Quick Start

### 1. Environment Configuration

Create a `.env.production` file with required environment variables:

```bash
# Application
ENVIRONMENT=production
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Database
POSTGRES_DB=karigai_db
POSTGRES_USER=karigai_user
POSTGRES_PASSWORD=strong-password-here
DATABASE_URL=postgresql://karigai_user:strong-password-here@db:5432/karigai_db

# Redis
REDIS_URL=redis://:redis-password@redis:6379/0
REDIS_PASSWORD=redis-password-here

# AI Services
OPENAI_API_KEY=your-openai-key
ELEVENLABS_API_KEY=your-elevenlabs-key

# Monitoring
GRAFANA_PASSWORD=grafana-admin-password

# Backup
BACKUP_S3_BUCKET=your-s3-bucket-name
BACKUP_WEBHOOK_URL=https://your-webhook-url
```

### 2. Deploy Services

```bash
# Start all services
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# Check service status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f api
```

### 3. Verify Deployment

```bash
# Check API health
curl http://localhost:8000/health

# Check detailed health
curl http://localhost:8000/health/detailed

# Access Grafana dashboard
open http://localhost:3000
# Login with admin / <GRAFANA_PASSWORD>

# Access Prometheus
open http://localhost:9090
```

## Service Architecture

### Core Services

1. **API Service** (Port 8000)
   - FastAPI application
   - Handles all API requests
   - Auto-restarts on failure

2. **PostgreSQL Database** (Port 5432)
   - Primary data storage
   - Automated backups
   - Health monitoring

3. **Redis Cache** (Port 6379)
   - Session storage
   - API response caching
   - Real-time data

4. **Nginx** (Ports 80, 443)
   - Reverse proxy
   - SSL termination
   - Static file serving

### Monitoring Services

5. **Prometheus** (Port 9090)
   - Metrics collection
   - Alert evaluation
   - Time-series database

6. **Grafana** (Port 3000)
   - Visualization dashboards
   - Alert management
   - Performance monitoring

## Health Checks

### Endpoint Overview

- `/health` - Basic health check
- `/health/detailed` - Comprehensive system status
- `/health/ready` - Kubernetes readiness probe
- `/health/live` - Kubernetes liveness probe

### Health Check Response

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "environment": "production",
  "checks": {
    "api": {"status": "healthy"},
    "database": {"status": "healthy", "latency_ms": 5.2},
    "redis": {"status": "healthy", "latency_ms": 1.8},
    "disk": {"status": "healthy", "free_percent": 45.2},
    "memory": {"status": "healthy", "used_percent": 62.5}
  }
}
```

## Monitoring and Alerts

### Prometheus Metrics

Key metrics collected:
- HTTP request rate and latency
- Database connection pool usage
- Redis cache hit/miss ratio
- Voice processing duration
- Vision processing duration
- Document generation success rate
- System resource usage (CPU, memory, disk)

### Alert Rules

Critical alerts:
- API down for > 2 minutes
- Database down for > 1 minute
- Error rate > 5% for 5 minutes
- Response time > 3 seconds (95th percentile)
- Disk space < 15%
- Memory usage > 85%

### Grafana Dashboards

Pre-configured dashboards:
1. **System Overview** - Overall health and performance
2. **API Performance** - Request rates, latency, errors
3. **Database Metrics** - Connections, queries, performance
4. **Resource Usage** - CPU, memory, disk, network
5. **Business Metrics** - User activity, feature usage

## Backup and Recovery

### Automated Backups

Backups run automatically via cron:

```bash
# Add to crontab
0 2 * * * docker-compose -f /path/to/docker-compose.prod.yml run backup
```

### Manual Backup

```bash
# Create backup
docker-compose -f docker-compose.prod.yml run backup

# List backups
ls -lh backups/

# Backup location
backups/karigai_backup_YYYYMMDD_HHMMSS.sql.gz
```

### Restore from Backup

```bash
# Restore specific backup
docker-compose -f docker-compose.prod.yml run backup /backup.sh restore karigai_backup_20240115_020000.sql.gz

# Or use restore script directly
docker exec -it karigai_backup /restore.sh karigai_backup_20240115_020000.sql.gz
```

### Backup Retention

- Daily backups retained for 30 days
- Weekly backups retained for 90 days (manual)
- Monthly backups retained for 1 year (manual)

## Scaling

### Horizontal Scaling

Scale API service:

```bash
# Scale to 3 instances
docker-compose -f docker-compose.prod.yml up -d --scale api=3

# Nginx will load balance automatically
```

### Vertical Scaling

Update resource limits in `docker-compose.prod.yml`:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

## Security

### SSL/TLS Configuration

1. Obtain SSL certificates (Let's Encrypt recommended)
2. Place certificates in `./ssl/` directory
3. Update nginx configuration
4. Restart nginx service

### Firewall Rules

```bash
# Allow HTTP/HTTPS
ufw allow 80/tcp
ufw allow 443/tcp

# Allow SSH (if needed)
ufw allow 22/tcp

# Block direct access to services
ufw deny 8000/tcp
ufw deny 5432/tcp
ufw deny 6379/tcp
```

### Secret Management

- Use environment variables for secrets
- Never commit `.env.production` to version control
- Rotate secrets regularly
- Use secret management tools (Vault, AWS Secrets Manager)

## Troubleshooting

### Common Issues

**API not responding:**
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs api

# Restart service
docker-compose -f docker-compose.prod.yml restart api
```

**Database connection errors:**
```bash
# Check database status
docker-compose -f docker-compose.prod.yml ps db

# Check database logs
docker-compose -f docker-compose.prod.yml logs db

# Verify connection
docker exec -it karigai_db psql -U karigai_user -d karigai_db
```

**High memory usage:**
```bash
# Check resource usage
docker stats

# Restart services
docker-compose -f docker-compose.prod.yml restart
```

### Log Management

```bash
# View all logs
docker-compose -f docker-compose.prod.yml logs

# Follow specific service
docker-compose -f docker-compose.prod.yml logs -f api

# View last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 api

# Export logs
docker-compose -f docker-compose.prod.yml logs > karigai_logs.txt
```

## Maintenance

### Regular Tasks

**Daily:**
- Monitor health check endpoints
- Review error logs
- Check disk space

**Weekly:**
- Review performance metrics
- Verify backup integrity
- Update dependencies (if needed)

**Monthly:**
- Security updates
- Database optimization
- Log rotation
- Backup verification

### Updates and Rollbacks

**Deploy new version:**
```bash
# Pull latest code
git pull origin main

# Rebuild containers
docker-compose -f docker-compose.prod.yml build

# Deploy with zero downtime
docker-compose -f docker-compose.prod.yml up -d --no-deps --build api
```

**Rollback:**
```bash
# Revert to previous version
git checkout <previous-commit>

# Rebuild and deploy
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d
```

## Performance Optimization

### Database Optimization

```sql
-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM users WHERE phone_number = '+919876543210';

-- Create indexes
CREATE INDEX idx_users_phone ON users(phone_number);
CREATE INDEX idx_documents_user_id ON documents(user_id);

-- Vacuum database
VACUUM ANALYZE;
```

### Cache Optimization

```bash
# Monitor Redis memory
docker exec -it karigai_redis redis-cli INFO memory

# Clear cache if needed
docker exec -it karigai_redis redis-cli FLUSHDB
```

### API Optimization

- Enable response compression
- Implement request rate limiting
- Use connection pooling
- Optimize database queries
- Cache frequently accessed data

## Support and Monitoring

### Monitoring Checklist

- [ ] All services running
- [ ] Health checks passing
- [ ] No critical alerts
- [ ] Disk space > 20%
- [ ] Memory usage < 80%
- [ ] Error rate < 1%
- [ ] Response time < 2s (95th percentile)
- [ ] Backups completing successfully

### Contact and Escalation

For production issues:
1. Check health endpoints
2. Review logs and metrics
3. Consult troubleshooting guide
4. Escalate to development team if needed

## Disaster Recovery

### Recovery Time Objectives (RTO)

- Database failure: < 15 minutes
- API failure: < 5 minutes
- Complete system failure: < 1 hour

### Recovery Procedures

1. **Database Failure:**
   - Restore from latest backup
   - Verify data integrity
   - Resume API service

2. **API Failure:**
   - Restart container
   - Check logs for errors
   - Scale horizontally if needed

3. **Complete Failure:**
   - Restore infrastructure
   - Restore database from backup
   - Deploy application
   - Verify all services

## Conclusion

This deployment guide provides comprehensive instructions for running KarigAI in production. Regular monitoring, maintenance, and following best practices will ensure reliable operation.

For additional support, refer to:
- API Documentation: `/docs`
- Monitoring Dashboard: Grafana
- Metrics: Prometheus
- Logs: Docker logs
