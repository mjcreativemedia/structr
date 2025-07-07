# 🚀 Structr Dashboard - Deployment Guide

## 📋 Overview

This guide covers deploying the Structr Dashboard to various hosting platforms. Choose the option that best fits your needs:

- **Railway** - Recommended for production (Docker support, persistent storage)
- **Render** - Good alternative to Railway (similar features)
- **Streamlit Cloud** - Easiest setup but limited features
- **DigitalOcean App Platform** - Enterprise-grade deployment
- **Self-hosted** - Maximum control and customization

---

## 🎯 Quick Deployment Options

### Option 1: Railway (Recommended)

**✅ Best for:** Production apps with file persistence and background jobs

**Features:**
- Docker support
- Persistent storage (10GB)
- Automatic SSL
- Custom domains
- Environment variables
- Built-in monitoring

**Deploy Steps:**
```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login to Railway
railway login

# 3. Navigate to your project
cd /path/to/structr

# 4. Initialize and deploy
railway init
railway up
```

**Cost:** $5/month for starter plan

---

### Option 2: Render

**✅ Best for:** Simple production deployment with good performance

**Features:**
- Docker support
- Persistent disks
- Automatic SSL
- Custom domains
- Zero-downtime deploys

**Deploy Steps:**
1. Fork/upload your code to GitHub
2. Connect Render to your repository
3. Use the included `render.yaml` configuration
4. Deploy automatically on git push

**Cost:** $7/month for starter plan

---

### Option 3: Streamlit Cloud

**✅ Best for:** Quick demos and prototypes (limited file persistence)

**Features:**
- Free tier available
- GitHub integration
- Automatic deployments
- Built for Streamlit apps

**Deploy Steps:**
1. Push code to GitHub repository
2. Visit [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Deploy with one click

**Limitations:**
- No persistent file storage
- Limited background processing
- Resource constraints

**Cost:** Free for public repos, $20/month for private

---

### Option 4: DigitalOcean App Platform

**✅ Best for:** Enterprise production deployment

**Features:**
- Scalable infrastructure
- Managed databases
- CDN integration
- Advanced monitoring

**Deploy Steps:**
```bash
# 1. Install doctl CLI
snap install doctl

# 2. Authenticate
doctl auth init

# 3. Create app
doctl apps create --spec .do/app.yaml

# 4. Monitor deployment
doctl apps list
```

**Cost:** $12/month for basic plan

---

## ⚙️ Environment Configuration

### Required Environment Variables

```bash
# Core settings
PYTHONPATH=/app
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Structr settings
STRUCTR_ENV=production
STRUCTR_OUTPUT_DIR=/app/output
STRUCTR_INPUT_DIR=/app/input
STRUCTR_LLM_MODEL=mistral

# Optional: External LLM services
# OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-...

# Optional: Database connections
# DATABASE_URL=postgresql://...
# REDIS_URL=redis://...
```

### Platform-Specific Setup

#### Railway Environment Variables
```bash
railway variables set PYTHONPATH=/app
railway variables set STREAMLIT_SERVER_PORT=8501
railway variables set STRUCTR_ENV=production
# ... add other variables
```

#### Render Environment Variables
Set in the Render dashboard under "Environment" tab, or use the `render.yaml` file.

#### Streamlit Cloud Secrets
Create `.streamlit/secrets.toml`:
```toml
STRUCTR_ENV = "production"
STRUCTR_LLM_MODEL = "mistral"
# Add other secrets here
```

---

## 🐳 Docker Deployment

### Local Docker Testing

```bash
# Build the image
docker build -t structr-dashboard .

# Run locally
docker run -p 8501:8501 \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/input:/app/input \
  structr-dashboard

# Or use docker-compose
docker-compose up
```

### Production Docker

```bash
# Build and tag for production
docker build -t your-registry/structr-dashboard:latest .

# Push to registry
docker push your-registry/structr-dashboard:latest

# Deploy on your server
docker run -d --name structr \
  -p 8501:8501 \
  -v /data/structr/output:/app/output \
  -v /data/structr/input:/app/input \
  --restart unless-stopped \
  your-registry/structr-dashboard:latest
```

---

## 📊 Monitoring & Health Checks

### Health Check Endpoint
All deployments include a health check at: `/_stcore/health`

### Monitoring Setup

1. **Application Logs**
   ```bash
   # Railway
   railway logs
   
   # Render
   # View in dashboard
   
   # Docker
   docker logs structr
   ```

2. **Performance Monitoring**
   - Enable monitoring in your hosting platform
   - Set up alerts for downtime
   - Monitor memory and CPU usage

3. **File System Monitoring**
   ```bash
   # Check disk usage
   df -h /app/output
   
   # Monitor bundle growth
   du -sh /app/output/bundles/
   ```

---

## 🔒 Security Considerations

### Production Security Checklist

- [ ] Set strong `SECRET_KEY` environment variable
- [ ] Enable HTTPS (automatic on most platforms)
- [ ] Configure API key authentication
- [ ] Set up proper CORS policies
- [ ] Enable request rate limiting
- [ ] Regular security updates

### API Keys Management

```bash
# Generate secure API key
openssl rand -hex 32

# Set in environment
export SECRET_KEY="your-secure-key"
```

---

## 🛠️ Troubleshooting

### Common Issues

1. **App Won't Start**
   ```bash
   # Check logs
   railway logs  # or platform equivalent
   
   # Verify environment variables
   railway variables  # or platform equivalent
   ```

2. **File Permission Errors**
   ```bash
   # Ensure directories exist and are writable
   mkdir -p output/bundles input temp_uploads
   chmod -R 755 output input temp_uploads
   ```

3. **Memory Issues**
   - Upgrade to higher memory plan
   - Optimize batch processing sizes
   - Clear temporary files regularly

4. **Slow Performance**
   - Enable caching
   - Optimize database queries
   - Consider CDN for static assets

### Log Locations

```
Application logs: Platform-specific
Error logs: stderr output
Access logs: Platform dashboard
Health checks: /_stcore/health
```

---

## 📈 Scaling Considerations

### Horizontal Scaling
- Use load balancer for multiple instances
- Implement session affinity for Streamlit
- Consider Redis for shared session storage

### Vertical Scaling
- Monitor memory usage patterns
- Increase CPU for heavy LLM processing
- Scale storage for large bundle volumes

### Performance Optimization
- Enable caching for repeated operations
- Optimize database queries
- Use background jobs for heavy processing
- Implement proper pagination

---

## 🚀 Next Steps After Deployment

1. **Configure Custom Domain**
   - Set up DNS records
   - Enable SSL certificate
   - Test HTTPS connectivity

2. **Set Up Monitoring**
   - Configure uptime monitoring
   - Set up error alerting
   - Monitor resource usage

3. **Backup Strategy**
   - Automated database backups
   - File system snapshots
   - Configuration backups

4. **CI/CD Pipeline**
   - Automated testing
   - Staging environment
   - Production deployment automation

---

## 💡 Platform Recommendations

| Use Case | Recommended Platform | Why |
|----------|---------------------|-----|
| **MVP/Demo** | Streamlit Cloud | Quick setup, free tier |
| **Small Business** | Railway | Good balance of features/cost |
| **Growing Startup** | Render | Robust features, good scaling |
| **Enterprise** | DigitalOcean/AWS | Full control, advanced features |
| **Self-hosted** | Docker + VPS | Maximum customization |

---

## 📞 Support

If you encounter issues during deployment:

1. Check the troubleshooting section above
2. Review platform-specific documentation
3. Check application logs for errors
4. Verify environment variable configuration
5. Test locally with Docker first

**Happy deploying! 🚀**