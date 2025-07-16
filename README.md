# Fire Fighting Humanoid Robot 🔥🤖

A comprehensive AI-powered fire fighting humanoid robot system with advanced computer vision, navigation, automated fire suppression capabilities, and enterprise-grade security and monitoring.

## 🌟 Features

### Core Capabilities
- **🔥 Fire Detection**: Real-time fire detection using YOLO models with thermal simulation
- **🧭 Navigation**: SLAM-based autonomous navigation with DWA path planning
- **💧 Fire Suppression**: Automated fire extinguishing system with priority-based response
- **📊 Web Dashboard**: Real-time monitoring and control interface with analytics
- **📱 Mobile App**: Flutter-based remote monitoring and control
- **🛡️ Safety Systems**: Emergency protocols and comprehensive failsafe mechanisms

### Enterprise Features
- **🔐 JWT Authentication**: Secure user authentication with role-based access control
- **⚡ Redis Caching**: High-performance caching for improved response times
- **📈 Health Monitoring**: Real-time system health metrics and alerts
- **🔍 Audit Logging**: Comprehensive activity logging with integrity verification
- **🚀 Background Tasks**: Priority-based task queue for complex operations
- **📋 API Documentation**: Comprehensive OpenAPI/Swagger documentation
- **🐳 Docker Support**: Full containerization with production-ready deployment
- **🔧 CI/CD Pipeline**: Automated testing, security scanning, and deployment

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

**Windows:**
```cmd
setup_dev.bat
```

**Linux/Mac:**
```bash
chmod +x setup_dev.sh
./setup_dev.sh
```

### Option 2: Manual Setup

1. **Install Dependencies**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # or
   .venv\Scripts\activate     # Windows
   
   pip install -r requirements.txt
   ```

2. **Initialize Environment**:
   ```bash
   cp .env.example .env
   python scripts/init_database.py
   python scripts/generate_security_keys.py
   ```

3. **Start Development Server**:
   ```bash
   uvicorn app.api.documented_api:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Access the System**:
   - **Main Dashboard**: http://localhost:8000
   - **API Documentation**: http://localhost:8000/docs
   - **Health Check**: http://localhost:8000/health

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Mobile App    │    │  Web Dashboard  │    │   Hardware      │
│   (Flutter)     │    │   (FastAPI)     │    │  Integration    │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
          ┌─────────────────────────────────────────────┐
          │              Core API Server                │
          │  ┌─────────────┐  ┌─────────────────────────┐│
          │  │    Auth     │  │      Task Queue         ││
          │  │  Security   │  │   Background Jobs       ││
          │  └─────────────┘  └─────────────────────────┘│
          │  ┌─────────────┐  ┌─────────────────────────┐│
          │  │   Cache     │  │      Monitoring         ││
          │  │   Redis     │  │   Health & Metrics      ││
          │  └─────────────┘  └─────────────────────────┘│
          └─────────────────────────────────────────────┘
                                 │
          ┌─────────────────────────────────────────────┐
          │               AI/Vision Layer               │
          │  ┌─────────────┐  ┌─────────────────────────┐│
          │  │Fire Detect  │  │      Navigation         ││
          │  │   YOLO      │  │      SLAM/DWA          ││
          │  └─────────────┘  └─────────────────────────┘│
          └─────────────────────────────────────────────┘
```

### Module Structure
- **`app/`**: Core API server with FastAPI
  - `api/`: REST API endpoints with OpenAPI documentation
  - `core/`: Authentication, caching, monitoring, security
  - `db/`: Database models and operations
  - `schemas/`: Pydantic models for validation
  - `services/`: Business logic and service layer
- **`vision/`**: Computer vision and fire detection algorithms
- **`automation/`**: Robot control, navigation, and SLAM
- **`mobile_app/`**: Flutter mobile application
- **`hardware_integration/`**: Hardware interface modules
- **`tests/`**: Comprehensive test suite with integration and performance tests
- **`scripts/`**: Utility scripts for database, security, and deployment

## ⚙️ Configuration

### Environment Variables
```bash
# Core Configuration
ENV=development
DEBUG=true
HOST=0.0.0.0
PORT=8000

# Security
JWT_SECRET_KEY=your-jwt-secret-key
API_SECRET_KEY=your-api-secret-key
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=hashed-password

# Database
DATABASE_URL=sqlite:///app/firebot.db

# Cache
REDIS_URL=redis://localhost:6379
CACHE_TTL=300

# Hardware
HARDWARE_ENABLED=false
SIMULATION_MODE=true
```

### Feature Flags
- **REDIS_ENABLED**: Enable/disable Redis caching
- **BACKGROUND_TASKS**: Enable/disable background task processing
- **RATE_LIMITING**: Enable/disable API rate limiting
- **AUDIT_LOGGING**: Enable/disable comprehensive audit logs

## 🧪 Testing

### Run All Tests
```bash
# Comprehensive test suite
./run_tests.sh

# Or manually
pytest tests/ -v --cov=app --cov-report=html
```

### Performance Testing
```bash
# Performance benchmarks
./run_performance.sh

# Or manually
python tests/test_performance.py
```

### Test Categories
- **Unit Tests**: Individual component testing
- **Integration Tests**: API endpoint testing with authentication
- **Performance Tests**: Load testing and benchmarking
- **Security Tests**: Authentication, validation, and input sanitization

## 🚀 Deployment

### Development
```bash
# Start all services
docker-compose up -d

# Development server with hot reload
./start_dev.sh
```

### Production
```bash
# Full production deployment
chmod +x deploy_production.sh
./deploy_production.sh

# Or with Docker Compose
docker-compose -f docker-compose.production.yml up -d
```

### Production Features
- **🌐 Nginx Reverse Proxy**: Load balancing, SSL termination, rate limiting
- **🔒 SSL/TLS Encryption**: Automatic HTTPS with certificate management
- **📊 Monitoring Stack**: Prometheus metrics, Grafana dashboards
- **📝 Centralized Logging**: Structured logging with Fluentd
- **💾 Database Backups**: Automated backup and retention policies
- **🔄 Health Checks**: Comprehensive service health monitoring
- **🛡️ Security Hardening**: Rate limiting, security headers, firewall rules

## 📊 Monitoring & Analytics

### Health Monitoring
- **System Metrics**: CPU, memory, disk usage
- **Application Metrics**: Request rates, response times, error rates
- **Custom Metrics**: Fire detection accuracy, robot status, sensor readings

### Dashboards
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **API Metrics**: http://localhost:8000/health

### Alerting
- **Critical Alerts**: System failures, security breaches
- **Warning Alerts**: Performance degradation, high error rates
- **Info Alerts**: Successful deployments, routine maintenance

## 🔐 Security Features

### Authentication & Authorization
- **JWT Tokens**: Secure stateless authentication
- **Role-Based Access**: Admin, operator, viewer roles
- **Session Management**: Secure token handling and expiration

### Security Hardening
- **Input Validation**: Comprehensive Pydantic validation
- **Rate Limiting**: Per-endpoint request rate controls
- **Security Headers**: CORS, CSRF, XSS protection
- **Audit Logging**: Complete activity audit trail
- **Data Encryption**: Sensitive data encryption at rest

### Compliance
- **Security Scanning**: Automated vulnerability detection
- **Code Quality**: Comprehensive linting and type checking
- **Dependencies**: Regular security updates and scanning

## 🛠️ Development

### Code Quality Tools
```bash
# Format code
black app/ automation/ vision/ scripts/

# Sort imports
isort app/ automation/ vision/ scripts/

# Lint code
flake8 app/ automation/ vision/

# Type checking
mypy app/

# Security scan
bandit -r app/ automation/ vision/
```

### Pre-commit Hooks
Automatically run quality checks before commits:
```bash
pip install pre-commit
pre-commit install
```

### API Development
- **OpenAPI/Swagger**: Automatic API documentation at `/docs`
- **Pydantic Models**: Type-safe request/response validation
- **Async Support**: Full asynchronous request handling
- **Error Handling**: Comprehensive error responses with logging

## 📚 API Documentation

### Core Endpoints
- **`GET /`**: Main dashboard interface
- **`GET /health`**: System health check
- **`POST /auth/login`**: User authentication
- **`POST /api/v2/sensors/reading`**: Submit sensor data
- **`POST /api/v2/robot/move`**: Control robot movement
- **`GET /api/v2/robot/status`**: Get robot status
- **`GET /api/v2/incidents`**: Retrieve incident history (admin only)

### Authentication
```bash
# Login
curl -X POST "http://localhost:8000/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "your_password"}'

# Use token
curl -X GET "http://localhost:8000/api/v2/robot/status" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 🤝 Contributing

1. **Fork the Repository**
2. **Create Feature Branch**: `git checkout -b feature/amazing-feature`
3. **Run Tests**: `pytest tests/`
4. **Format Code**: `black app/ && isort app/`
5. **Commit Changes**: `git commit -m 'Add amazing feature'`
6. **Push to Branch**: `git push origin feature/amazing-feature`
7. **Open Pull Request**

Please read `CONTRIBUTING.md` for detailed guidelines.

## 📄 Documentation

- **`PROJECT_REPORT.md`**: Comprehensive project documentation
- **`DEPLOYMENT_CHECKLIST.md`**: Production deployment guide
- **`RASPBERRY_PI_DEPLOYMENT.md`**: Hardware deployment instructions
- **`MOBILE_APP_COMPLETION.md`**: Mobile app development guide
- **`WINDOWS_PYTHON_FIX.md`**: Windows-specific setup instructions

## 🚧 Performance Metrics

### Benchmarks (Typical Performance)
- **API Response Time**: ~50ms average, ~200ms 95th percentile
- **Fire Detection**: ~100ms per frame at 640x480
- **Database Operations**: 1000+ ops/second
- **Concurrent Users**: 50+ simultaneous connections
- **Memory Usage**: ~200MB baseline, ~500MB under load

## 🆕 Recent Updates

### Version 2.0 Features
- ✅ Enterprise-grade authentication system
- ✅ Redis caching for improved performance
- ✅ Comprehensive health monitoring
- ✅ Background task processing
- ✅ Security hardening and audit logging
- ✅ Production deployment automation
- ✅ CI/CD pipeline with automated testing
- ✅ Performance monitoring and alerting

## 📞 Support

For support, questions, or contributions:
- **Issues**: GitHub Issues for bug reports and feature requests
- **Discussions**: GitHub Discussions for questions and community support
- **Security**: Security issues should be reported privately

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ for fire safety and emergency response automation** 🔥🚀
