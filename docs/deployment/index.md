# Deployment Guide

> Deploy Zenith applications to production with Docker, cloud platforms, and best practices

## Quick Deploy

The fastest way to deploy a Zenith application:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install .

# Copy application
COPY src/ ./src/

# Run application
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.your_app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t blog-api .
docker run -p 8000:8000 -e SECRET_KEY=your-secret blog-api
```

## Production Deployment

### Docker Production Setup

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir .

# Production stage
FROM python:3.11-slim

# Install runtime dependencies  
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r app && useradd -r -g app app

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Create uploads directory
RUN mkdir -p /app/uploads && chown -R app:app /app

# Switch to app user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Run with gunicorn for production
CMD ["gunicorn", "src.blog_api.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

Create `docker-compose.yml` for local development:

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - SECRET_KEY=dev-secret-key-that-is-at-least-32-characters-long
      - DATABASE_URL=postgresql+asyncpg://postgres:password@db:5432/blog_api
      - DEBUG=false
    depends_on:
      - db
      - redis
    volumes:
      - ./uploads:/app/uploads
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=blog_api
      - POSTGRES_USER=postgres  
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80" 
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./uploads:/var/www/uploads
    depends_on:
      - api
    restart: unless-stopped

volumes:
  postgres_data:
```

## Cloud Platform Deployments

### Fly.io

Create `fly.toml`:

```toml
app = "blog-api"

[build]
  dockerfile = "Dockerfile"

[env]
  PORT = "8000"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true

[[http_service.checks]]
  grace_period = "10s"
  interval = "30s"
  method = "GET"
  path = "/health"
  timeout = "5s"

[[services]]
  internal_port = 8000
  protocol = "tcp"

  [services.concurrency]
    hard_limit = 100
    soft_limit = 80

  [[services.ports]]
    handlers = ["http"]
    port = "80"

  [[services.ports]] 
    handlers = ["tls", "http"]
    port = "443"

[mounts]
  source = "uploads"
  destination = "/app/uploads"
```

Deploy commands:

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login and create app
flyctl auth login
flyctl apps create blog-api

# Set secrets
flyctl secrets set SECRET_KEY="your-super-secret-key"
flyctl secrets set DATABASE_URL="postgresql://..."

# Deploy
flyctl deploy
```

### Railway

Create `railway.toml`:

```toml
[build]
  builder = "nixpacks"

[deploy]
  startCommand = "python -m uvicorn src.blog_api.main:app --host 0.0.0.0 --port $PORT"
  healthcheckPath = "/health"
  healthcheckTimeout = 30
  restartPolicyType = "on_failure"
```

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### Heroku

Create `Procfile`:

```
web: gunicorn src.blog_api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
release: alembic upgrade head
```

Create `runtime.txt`:

```
python-3.11.6
```

Deploy commands:

```bash
# Install Heroku CLI and login
heroku login

# Create app
heroku create blog-api

# Set config vars
heroku config:set SECRET_KEY="your-secret-key"
heroku config:set DATABASE_URL="postgresql://..."

# Add PostgreSQL addon
heroku addons:create heroku-postgresql:mini

# Deploy
git push heroku main
```

### AWS Lambda (Serverless)

Create `lambda_handler.py`:

```python
from mangum import Mangum
from src.blog_api.main import app

handler = Mangum(app, lifespan="off")
```

Create `serverless.yml`:

```yaml
service: blog-api

provider:
  name: aws
  runtime: python3.11
  region: us-east-1
  environment:
    SECRET_KEY: ${env:SECRET_KEY}
    DATABASE_URL: ${env:DATABASE_URL}

functions:
  app:
    handler: lambda_handler.handler
    events:
      - http:
          path: /{proxy+}
          method: ANY
          cors: true
      - http:
          path: /
          method: ANY  
          cors: true
    timeout: 30

plugins:
  - serverless-python-requirements

custom:
  pythonRequirements:
    dockerizePip: true
```

```bash
npm install -g serverless
serverless deploy
```

## Database Setup

### PostgreSQL Production

```sql
-- Create database and user
CREATE DATABASE blog_api_prod;
CREATE USER blog_api WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE blog_api_prod TO blog_api;

-- Enable extensions
\c blog_api_prod;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

### Migrations

Run database migrations on deploy:

```bash
# Production migration command
alembic upgrade head

# Docker setup
docker run --rm \
  -e DATABASE_URL="postgresql://..." \
  blog-api:latest \
  alembic upgrade head
```

## Security Configuration

### Environment Variables

```bash
# Production environment variables
SECRET_KEY=super-secure-random-key-at-least-32-characters-long
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/dbname
DEBUG=false

# Security settings
ALLOWED_HOSTS=api.yourdomain.com
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
CSRF_SECRET=another-secure-random-key

# File upload limits
MAX_FILE_SIZE=10485760  # 10MB
UPLOAD_DIR=/app/uploads

# Rate limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=10

# Monitoring
SENTRY_DSN=https://...
LOG_LEVEL=INFO
```

### Nginx Configuration

Create `nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream app {
        server api:8000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    server {
        listen 80;
        server_name api.yourdomain.com;

        # Security headers
        add_header X-Frame-Options "DENY" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # API routes
        location / {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Timeouts
            proxy_connect_timeout 5s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }

        # Static file serving
        location /uploads/ {
            alias /var/www/uploads/;
            expires 7d;
            add_header Cache-Control "public, immutable";
            
            # Security - prevent script execution
            location ~* \.(php|py|pl|sh)$ {
                deny all;
            }
        }
    }
}
```

## Monitoring & Observability

### Health Checks

Ensure your app has comprehensive health checks:

```python
from zenith.web.health import health_manager, add_health_routes

# Add health routes
add_health_routes(app)

# Database connectivity  
health_manager.add_database_check(database_url)

# External services
health_manager.add_redis_check(redis_url)

# Custom business logic checks
async def user_service_check():
    # Check if user service is responsive
    return await ping_user_service()

health_manager.add_simple_check(
    "user_service", 
    user_service_check,
    timeout=5.0,
    critical=True
)
```

### Logging

Configure structured logging:

```python
import logging.config

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'zenith.logging.JSONFormatter',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
    },
    'loggers': {
        'zenith': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

logging.config.dictConfig(LOGGING)
```

### Error Tracking

Add Sentry for error tracking:

```python
import sentry_sdk
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        integrations=[SqlalchemyIntegration()],
        traces_sample_rate=0.1,
        environment=os.getenv("ENVIRONMENT", "production"),
    )
```

## Performance Optimization

### Database

```python
# Connection pooling
app.setup_database(
    database_url,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Query optimization
class Post(Base):
    __tablename__ = "posts"
    
    # Add database indexes
    __table_args__ = (
        Index('ix_posts_created_at', 'created_at'),
        Index('ix_posts_published', 'is_published'),
        Index('ix_posts_author', 'author_id'),
    )
```

### Caching

Add Redis caching:

```python
from zenith.cache import configure_cache

configure_cache(app, redis_url="redis://localhost:6379")

@app.get("/posts")
@cache(expire=300)  # 5 minutes
async def list_posts():
    return await posts_context.get_all_posts()
```

### Static Files

Use CDN for static files in production:

```python
# Configure static file serving
app.mount_static("/uploads", "./uploads", max_age=86400)  # 1 day cache

# Or use cloud storage
from zenith.storage import S3Storage
storage = S3Storage(bucket="my-app-uploads")
app.configure_storage(storage)
```

## CI/CD Pipeline

### GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
          
      - name: Run tests
        run: |
          pytest --cov=src/blog_api --cov-report=xml
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/postgres
          SECRET_KEY: test-secret-key-that-is-long-enough
          
      - name: Upload coverage
        uses: codecov/codecov-action@v3

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Fly.io
        uses: superfly/flyctl-actions/setup-flyctl@master
      - run: flyctl deploy --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

## Troubleshooting

### Common Issues

**1. Database Connection Issues**
```bash
# Check connection
docker exec -it db psql -U postgres -d blog_api

# Test from app container
docker exec -it api python -c "
import asyncpg
import asyncio
asyncio.run(asyncpg.connect('postgresql://...'))
"
```

**2. Memory Issues**
```dockerfile
# Limit memory usage in Docker
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 
ENV PYTHONDONTWRITEBYTECODE=1

# Use --memory flag
docker run --memory=512m blog-api
```

**3. File Upload Issues**
```bash
# Check permissions
ls -la uploads/
chmod 755 uploads/

# Check disk space
df -h

# Check file size limits
curl -X POST -F "file=@large_file.jpg" http://localhost:8000/upload
```

---

Your Zenith application is now ready for production! For monitoring and maintenance, consider:

- Setting up log aggregation (ELK stack, Datadog)
- Database backups and monitoring
- SSL certificates (Let's Encrypt, Cloudflare)
- Load balancing for high traffic
- Auto-scaling policies

For more advanced deployment scenarios, see our [Examples](../examples/index.md) section.