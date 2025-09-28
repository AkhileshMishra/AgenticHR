.PHONY: help dev.bootstrap dev.up dev.down dev.logs dev.health qa.all lint.all format.all typecheck.all test.all build.all deploy.prod api.bundle

# Default target
help: ## Show this help message
	@echo "AgenticHR Development Commands"
	@echo "=============================="
	@grep -E '^[a-zA-Z_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Development Environment
dev.bootstrap: ## Bootstrap development environment
	@echo "🚀 Bootstrapping AgenticHR development environment..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "📝 Created .env from .env.example"; fi
	@docker --version >/dev/null 2>&1 || (echo "❌ Docker not found. Please install Docker first." && exit 1)
	@docker compose version >/dev/null 2>&1 || (echo "❌ Docker Compose not found. Please install Docker Compose first." && exit 1)
	@poetry --version >/dev/null 2>&1 || (echo "❌ Poetry not found. Please install Poetry first." && exit 1)
	@echo "✅ Prerequisites check passed"
	@echo "🐳 Pulling required Docker images..."
	@docker compose -f docker/compose.dev.yml pull
	@echo "📦 Installing Python dependencies..."
	@poetry install
	@echo "🎉 Bootstrap complete! Run 'make dev.up' to start services."

dev.up: ## Start all development services
	@echo "🚀 Starting AgenticHR development environment..."
	@docker compose -f docker/compose.dev.yml up -d
	@echo "⏳ Waiting for services to be ready..."
	@sleep 10
	@echo "🎉 Services started! Check 'make dev.health' for status."

dev.down: ## Stop all development services
	@echo "🛑 Stopping AgenticHR development environment..."
	@docker compose -f docker/compose.dev.yml down
	@echo "✅ Services stopped."

dev.logs: ## Show logs from all services
	@docker compose -f docker/compose.dev.yml logs -f

dev.health: ## Check health of all services
	@echo "🏥 Checking service health..."
	@echo "Kong Gateway: $$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000 || echo 'DOWN')"
	@echo "Kong Admin: $$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8001 || echo 'DOWN')"
	@echo "Keycloak: $$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080 || echo 'DOWN')"
	@echo "Auth Service: $$(curl -s -o /dev/null -w '%{http_code}' http://localhost:9001/health || echo 'DOWN')"
	@echo "Employee Service: $$(curl -s -o /dev/null -w '%{http_code}' http://localhost:9002/health || echo 'DOWN')"

# Quality Assurance
qa.all: lint.all typecheck.all test.all ## Run all quality assurance checks

lint.all: ## Run linting on all code
	@echo "🔍 Running linting checks..."
	@poetry run ruff check .
	@poetry run black --check .
	@echo "✅ Linting complete."

format.all: ## Format all code
	@echo "🎨 Formatting code..."
	@poetry run black .
	@poetry run ruff check --fix .
	@echo "✅ Code formatted."

typecheck.all: ## Run type checking on all code
	@echo "🔍 Running type checks..."
	@poetry run mypy libs/ services/
	@echo "✅ Type checking complete."

test.all: ## Run all tests
	@echo "🧪 Running all tests..."
	@poetry run pytest -v --cov=. --cov-report=html
	@echo "✅ All tests complete. Coverage report: htmlcov/index.html"

# Individual service tests
test.auth-svc: ## Run auth service tests
	@echo "🧪 Testing auth-svc..."
	@cd services/auth-svc && poetry run pytest -v

test.employee-svc: ## Run employee service tests
	@echo "🧪 Testing employee-svc..."
	@cd services/employee-svc && poetry run pytest -v

# Security
security.scan: ## Run security scans
	@echo "🔒 Running security scans..."
	@poetry run bandit -r libs/ services/
	@poetry run safety check
	@echo "✅ Security scan complete."

# API Documentation
api.bundle: ## Generate merged OpenAPI documentation
	@echo "📚 Generating API documentation..."
	@mkdir -p docs/api
	@echo "✅ API documentation generated in docs/api/"

api.postman: ## Generate Postman collection
	@echo "📮 Generating Postman collection..."
	@mkdir -p docs/api
	@echo "✅ Postman collection generated in docs/api/"

# Build
build.all: ## Build all service containers
	@echo "🏗️ Building all service containers..."
	@docker compose -f docker/compose.dev.yml build
	@echo "✅ All containers built."

build.auth-svc: ## Build auth service container
	@echo "🏗️ Building auth-svc container..."
	@cd services/auth-svc && docker build -t agentichr/auth-svc:latest .

build.employee-svc: ## Build employee service container
	@echo "🏗️ Building employee-svc container..."
	@cd services/employee-svc && docker build -t agentichr/employee-svc:latest .

# Database
db.migrate: ## Run database migrations
	@echo "🗄️ Running database migrations..."
	@poetry run alembic upgrade head
	@echo "✅ Database migrations complete."

db.seed: ## Seed database with sample data
	@echo "🌱 Seeding database with sample data..."
	@poetry run python scripts/seed_data.py
	@echo "✅ Database seeded."

db.reset: ## Reset database (WARNING: This will delete all data)
	@echo "⚠️ This will delete all data. Are you sure? [y/N]" && read ans && [ $${ans:-N} = y ]
	@echo "🗄️ Resetting database..."
	@docker compose -f docker/compose.dev.yml exec postgres psql -U hr -d hr -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
	@make db.migrate
	@echo "✅ Database reset complete."

# Deployment
deploy.prod: ## Deploy to production
	@echo "🚀 Deploying to production..."
	@helm upgrade --install agentichr deploy/helm/agentichr/ --namespace agentichr --create-namespace
	@echo "✅ Production deployment complete."

deploy.status: ## Check deployment status
	@echo "📊 Checking deployment status..."
	@kubectl get pods -n agentichr
	@kubectl get services -n agentichr

# Monitoring
logs.auth-svc: ## Show auth service logs
	@docker compose -f docker/compose.dev.yml logs -f auth-svc

logs.employee-svc: ## Show employee service logs
	@docker compose -f docker/compose.dev.yml logs -f employee-svc

logs.kong: ## Show Kong gateway logs
	@docker compose -f docker/compose.dev.yml logs -f kong

logs.keycloak: ## Show Keycloak logs
	@docker compose -f docker/compose.dev.yml logs -f keycloak

# Utilities
clean: ## Clean up development environment
	@echo "🧹 Cleaning up..."
	@docker compose -f docker/compose.dev.yml down -v
	@docker system prune -f
	@poetry env remove --all
	@echo "✅ Cleanup complete."

shell.postgres: ## Open PostgreSQL shell
	@docker compose -f docker/compose.dev.yml exec postgres psql -U hr -d hr

shell.redis: ## Open Redis shell
	@docker compose -f docker/compose.dev.yml exec redis redis-cli

# Development helpers
dev.restart: dev.down dev.up ## Restart development environment

dev.rebuild: ## Rebuild and restart development environment
	@make dev.down
	@make build.all
	@make dev.up

# Generate certificates for development
certs.generate: ## Generate development certificates
	@echo "🔐 Generating development certificates..."
	@mkdir -p certs
	@openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes -subj "/CN=localhost"
	@echo "✅ Development certificates generated in certs/"
# Additional Makefile targets for Kong JWT configuration

.PHONY: kong.validate kong.test-config kong.check-jwt

kong.validate: ## Validate Kong configuration
	@echo "Validating Kong configuration..."
	@python3 -c "import yaml; yaml.safe_load(open('docker/kong/kong.yml')); print('✅ Kong YAML is valid')"
	@echo "Checking Kong configuration completeness..."
	@python3 -c "import yaml; config = yaml.safe_load(open('docker/kong/kong.yml')); \
		services = config.get('services', []); \
		plugins = config.get('plugins', []); \
		consumers = config.get('consumers', []); \
		jwt_secrets = config.get('jwt_secrets', []); \
		print(f'Services: {len(services)}'); \
		print(f'Plugins: {len(plugins)}'); \
		print(f'Consumers: {len(consumers)}'); \
		print(f'JWT Secrets: {len(jwt_secrets)}'); \
		assert len(services) >= 2, 'At least 2 services required'; \
		assert len(plugins) >= 3, 'At least 3 plugins required (CORS, Rate Limiting, JWT)'; \
		assert len(consumers) >= 1, 'At least 1 consumer required'; \
		assert len(jwt_secrets) >= 1, 'At least 1 JWT secret required'; \
		print('✅ Kong configuration is complete')"

kong.test-config: ## Test Kong configuration with docker-compose config
	@echo "Testing Kong configuration with Docker Compose..."
	@docker compose -f docker/compose.dev.yml config kong >/dev/null 2>&1 && echo "✅ Kong service configuration is valid" || echo "❌ Kong service configuration has issues"

kong.check-jwt: ## Check JWT configuration alignment between Kong and Keycloak
	@echo "Checking JWT configuration alignment..."
	@python3 -c "import yaml, json; \
		kong_config = yaml.safe_load(open('docker/kong/kong.yml')); \
		keycloak_config = json.load(open('docker/keycloak/realm-export.json')); \
		jwt_secret = kong_config['jwt_secrets'][0]; \
		realm_name = keycloak_config['realm']; \
		expected_issuer = f'http://keycloak:8080/realms/{realm_name}'; \
		actual_key = jwt_secret['key']; \
		print(f'Expected issuer: {expected_issuer}'); \
		print(f'Kong consumer key: {actual_key}'); \
		assert actual_key == expected_issuer, f'Issuer mismatch: {actual_key} != {expected_issuer}'; \
		print('✅ JWT configuration is aligned between Kong and Keycloak')"

# Add to existing help target
help-kong: ## Show Kong-specific help
	@echo "Kong JWT Configuration Commands:"
	@echo "================================"
	@grep -E '^kong\.[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'
