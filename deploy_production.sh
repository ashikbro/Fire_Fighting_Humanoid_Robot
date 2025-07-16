#!/bin/bash

# Production Deployment Script for Fire Fighting Robot
# This script deploys the application to production environment

set -e

echo "🔥 Fire Fighting Robot - Production Deployment"
echo "=============================================="

# Configuration
PROJECT_NAME="fire-fighting-robot"
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
ENV_FILE=".env.production"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Pre-deployment checks
pre_deployment_checks() {
    print_status "Running pre-deployment checks..."
    
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        print_error "Docker is required but not installed"
        exit 1
    fi
    
    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is required but not installed"
        exit 1
    fi
    
    # Check if environment file exists
    if [ ! -f "$ENV_FILE" ]; then
        print_error "Production environment file $ENV_FILE not found"
        print_status "Creating template from .env.example..."
        if [ -f ".env.example" ]; then
            cp .env.example "$ENV_FILE"
            print_warning "Please update $ENV_FILE with production values"
            exit 1
        else
            print_error ".env.example not found"
            exit 1
        fi
    fi
    
    # Check if SSL certificates exist
    if [ ! -f "nginx/ssl/cert.pem" ] || [ ! -f "nginx/ssl/key.pem" ]; then
        print_warning "SSL certificates not found in nginx/ssl/"
        print_status "Generating self-signed certificates for testing..."
        mkdir -p nginx/ssl
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/key.pem \
            -out nginx/ssl/cert.pem \
            -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
        print_success "Self-signed certificates generated"
    fi
    
    print_success "Pre-deployment checks completed"
}

# Backup current deployment
backup_current_deployment() {
    print_status "Creating backup of current deployment..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup database
    if [ -f "app/firebot.db" ]; then
        cp app/firebot.db "$BACKUP_DIR/firebot.db"
        print_success "Database backed up"
    fi
    
    # Backup configuration
    if [ -f "$ENV_FILE" ]; then
        cp "$ENV_FILE" "$BACKUP_DIR/env.backup"
        print_success "Environment configuration backed up"
    fi
    
    # Backup logs
    if [ -d "logs" ]; then
        cp -r logs "$BACKUP_DIR/"
        print_success "Logs backed up"
    fi
    
    print_success "Backup created in $BACKUP_DIR"
}

# Build and deploy containers
deploy_containers() {
    print_status "Building and deploying containers..."
    
    # Load environment variables
    export $(cat "$ENV_FILE" | xargs)
    
    # Build images
    print_status "Building Docker images..."
    docker-compose -f docker-compose.production.yml build --no-cache
    
    # Pull updated base images
    docker-compose -f docker-compose.production.yml pull
    
    # Stop existing containers
    print_status "Stopping existing containers..."
    docker-compose -f docker-compose.production.yml down --remove-orphans
    
    # Start new containers
    print_status "Starting new containers..."
    docker-compose -f docker-compose.production.yml up -d
    
    print_success "Containers deployed successfully"
}

# Health checks
perform_health_checks() {
    print_status "Performing health checks..."
    
    # Wait for services to start
    sleep 30
    
    # Check API health
    for i in {1..30}; do
        if curl -f http://localhost:8000/health &>/dev/null; then
            print_success "API service is healthy"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "API service failed health check"
            return 1
        fi
        sleep 2
    done
    
    # Check Redis
    if docker exec fire-robot-redis redis-cli ping | grep -q PONG; then
        print_success "Redis service is healthy"
    else
        print_error "Redis service failed health check"
        return 1
    fi
    
    # Check Nginx
    if curl -f http://localhost/health &>/dev/null; then
        print_success "Nginx service is healthy"
    else
        print_error "Nginx service failed health check"
        return 1
    fi
    
    print_success "All health checks passed"
}

# Database migration
run_database_migration() {
    print_status "Running database migrations..."
    
    # Run database initialization if needed
    docker exec fire-robot-api python scripts/init_database.py
    
    print_success "Database migrations completed"
}

# Setup monitoring
setup_monitoring() {
    print_status "Setting up monitoring and alerting..."
    
    # Check Prometheus
    if curl -f http://localhost:9090/-/healthy &>/dev/null; then
        print_success "Prometheus is running"
    else
        print_warning "Prometheus health check failed"
    fi
    
    # Check Grafana
    if curl -f http://localhost:3000/api/health &>/dev/null; then
        print_success "Grafana is running"
    else
        print_warning "Grafana health check failed"
    fi
    
    print_success "Monitoring setup completed"
}

# Security hardening
apply_security_hardening() {
    print_status "Applying security hardening..."
    
    # Set proper file permissions
    chmod 600 "$ENV_FILE"
    chmod 600 nginx/ssl/*
    
    # Update firewall rules (if ufw is available)
    if command -v ufw &> /dev/null; then
        print_status "Updating firewall rules..."
        ufw allow 80/tcp
        ufw allow 443/tcp
        ufw allow 22/tcp
        # ufw enable  # Uncomment if you want to enable firewall
    fi
    
    print_success "Security hardening applied"
}

# Post-deployment verification
post_deployment_verification() {
    print_status "Running post-deployment verification..."
    
    # Test critical endpoints
    endpoints=(
        "http://localhost:8000/health"
        "http://localhost:8000/"
        "http://localhost:8000/docs"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if curl -f "$endpoint" &>/dev/null; then
            print_success "✓ $endpoint is accessible"
        else
            print_error "✗ $endpoint is not accessible"
            return 1
        fi
    done
    
    # Check container status
    print_status "Checking container status..."
    docker-compose -f docker-compose.production.yml ps
    
    print_success "Post-deployment verification completed"
}

# Cleanup old resources
cleanup_old_resources() {
    print_status "Cleaning up old resources..."
    
    # Remove old Docker images
    docker image prune -f
    
    # Remove old containers
    docker container prune -f
    
    # Remove old volumes (be careful!)
    # docker volume prune -f
    
    print_success "Cleanup completed"
}

# Rollback function
rollback_deployment() {
    print_error "Deployment failed! Rolling back..."
    
    # Stop current containers
    docker-compose -f docker-compose.production.yml down
    
    # Restore from backup if available
    if [ -d "$BACKUP_DIR" ]; then
        print_status "Restoring from backup..."
        
        # Restore database
        if [ -f "$BACKUP_DIR/firebot.db" ]; then
            cp "$BACKUP_DIR/firebot.db" app/firebot.db
        fi
        
        # Restore environment
        if [ -f "$BACKUP_DIR/env.backup" ]; then
            cp "$BACKUP_DIR/env.backup" "$ENV_FILE"
        fi
        
        print_success "Rollback completed"
    else
        print_error "No backup available for rollback"
    fi
    
    exit 1
}

# Main deployment function
main() {
    print_status "Starting production deployment..."
    
    # Set trap for cleanup on failure
    trap rollback_deployment ERR
    
    # Run deployment steps
    pre_deployment_checks
    backup_current_deployment
    deploy_containers
    run_database_migration
    perform_health_checks
    setup_monitoring
    apply_security_hardening
    post_deployment_verification
    cleanup_old_resources
    
    # Print deployment summary
    echo ""
    echo "🎉 Production Deployment Completed Successfully!"
    echo "==============================================="
    echo ""
    echo "🌐 Service URLs:"
    echo "   • Main Application: https://localhost"
    echo "   • API Documentation: https://localhost/docs"
    echo "   • Health Check: https://localhost/health"
    echo "   • Monitoring (Grafana): http://localhost:3000"
    echo "   • Metrics (Prometheus): http://localhost:9090"
    echo ""
    echo "📊 Container Status:"
    docker-compose -f docker-compose.production.yml ps
    echo ""
    echo "💾 Backup Location: $BACKUP_DIR"
    echo ""
    print_success "Deployment completed successfully! 🔥"
}

# Parse command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "rollback")
        rollback_deployment
        ;;
    "health")
        perform_health_checks
        ;;
    "logs")
        docker-compose -f docker-compose.production.yml logs -f
        ;;
    "status")
        docker-compose -f docker-compose.production.yml ps
        ;;
    *)
        echo "Usage: $0 [deploy|rollback|health|logs|status]"
        exit 1
        ;;
esac
