# AgenticHR

Production-grade FastAPI microservices architecture for Human Resources Management System with built-in MFA, workflows, and agent integration.

## Overview

AgenticHR is a comprehensive HR management platform built as a microservices architecture that maps 1:1 to Frappe HRMS domains. It features:

- **FastAPI-first microservices** for each HR domain (employees, attendance, leave, payroll, recruitment, etc.)
- **Built-in MFA** with TOTP + WebAuthn via Keycloak
- **Workflow orchestration** using Temporal for complex HR processes
- **Event-driven architecture** with NATS/Kafka for reliable messaging
- **Agent integration** for AI-powered HR automation
- **Production-ready infrastructure** with Kong gateway, PostgreSQL, Redis, and more

## Architecture

### Core Services

| Service | Domain | Description |
|---------|--------|-------------|
| `auth-svc` | Authentication | Login/signup, sessions, MFA (TOTP+WebAuthn) |
| `iam-gw` | Identity & Access | Organizations, roles, permissions (RBAC/ABAC) |
| `employee-svc` | Employee Management | Employee profiles, documents, lifecycle |
| `onboarding-svc` | Onboarding/Lifecycle | Joiner/mover/leaver workflows |
| `attendance-svc` | Attendance | Check-in/out, geo-fencing, device bindings |
| `leave-svc` | Leave Management | Leave types, accruals, multi-level approvals |
| `timesheet-svc` | Time Tracking | Project time tracking, approvals, exports |
| `payroll-svc` | Payroll | Payroll runs, payslips, compliance calculations |
| `recruitment-svc` | Recruitment | Jobs, candidates, interviews, workflows |
| `compliance-svc` | Compliance | Policies, audits, export packages |
| `docstore-svc` | Document Storage | File storage with S3/MinIO, virus scanning |
| `notify-svc` | Notifications | Multi-channel notifications with templates |
| `search-svc` | Search | Global search with OpenSearch/Meilisearch |
| `analytics-svc` | Analytics | Aggregates, KPIs, BI data extraction |
| `agents-gw` | Agent Gateway | AI agent integration for HR automation |

### Technology Stack

- **Framework**: FastAPI + Pydantic v2, Uvicorn
- **Database**: PostgreSQL with Alembic migrations
- **Cache/Queues**: Redis, RabbitMQ
- **Workflows**: Temporal OSS for durable workflows
- **Event Bus**: NATS JetStream or Apache Kafka
- **Search**: Meilisearch (dev) / OpenSearch (prod)
- **Storage**: MinIO (S3-compatible)
- **Auth**: Keycloak (OIDC/OAuth2) with TOTP + WebAuthn
- **Gateway**: Kong with thin routing (JWT verified in services)
- **Observability**: OpenTelemetry + Prometheus/Grafana + Loki

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Poetry (`pipx install poetry`)
- Make

> **Optional stacks (dev only)**: Temporal, NATS, OpenSearch, Observability stack are brought up by docker-compose for convenience. Services will start without them; they'll be wired in future commits.

### Development Setup

1. **Bootstrap the development environment**:
   ```bash
   make dev.bootstrap
   ```

2. **Start all services**:
   ```bash
   make dev.up
   ```

3. **Verify services are running**:
   ```bash
   make dev.health
   ```

### Service Endpoints

- **Kong Gateway**: http://localhost:8000
- **Kong Admin**: http://localhost:8001
- **Keycloak**: http://localhost:8080 (admin/admin)
- **Auth Service**: http://localhost:9001
- **Employee Service**: http://localhost:9002
- **MinIO Console**: http://localhost:9090 (minio/minio123)

### Authentication Model

**Current Implementation**: JWT verification happens inside each service via `libs/py-hrms-auth`. Kong provides thin routing, CORS, and rate limiting only.

**Routes Available**:
- `/auth/*` → auth-svc (authentication, MFA, sessions)
- `/employee/*` → employee-svc (employee CRUD operations)

**JWT Flow**:
1. Client authenticates with Keycloak via auth-svc
2. Keycloak issues JWT token
3. Client includes JWT in Authorization header
4. Kong routes request to appropriate service
5. Service validates JWT using py-hrms-auth library
6. Service processes request if JWT is valid

## Development Workflow

### Running Tests

```bash
# Run all tests
make qa.all

# Run specific service tests
make test.auth-svc
make test.employee-svc
```

### Code Quality

```bash
# Lint all code
make lint.all

# Format code
make format.all

# Type checking
make typecheck.all
```

### API Documentation

```bash
# Generate merged OpenAPI documentation
make api.bundle

# Generate Postman collection
make api.postman
```

## Security Features

### Multi-Factor Authentication (MFA)

- **Primary**: Keycloak realm with enforced TOTP + WebAuthn
- **Fallback**: Service-side TOTP using pyotp for offline scenarios
- **WebAuthn**: FIDO2 support with resident keys

### Authorization

- **RBAC**: Role-based access control with scoped permissions
- **ABAC**: Attribute-based access control for fine-grained policies
- **JWT**: Bearer token validation against JWKS endpoint
- **Tenancy**: Multi-tenant support with data isolation

### Security Baseline

- TLS everywhere with proper certificate management
- Request tracing with X-Request-ID and OpenTelemetry
- Secrets management via environment variables + SOPS/age
- Content Security Policy (CSP) and HSTS at gateway
- Data Loss Prevention (DLP) hooks in document storage
- Audit logging for all sensitive operations

## Workflows & Automation

### Temporal Workflows

Long-running orchestrations with human-in-the-loop steps:

- **Onboarding**: Employee creation → checklist tasks → device/ID issuance → approvals
- **Leave Approval**: Request → manager approval → HR approval → final update
- **Payroll Processing**: Timesheet collection → computation → approvals → payslip generation

### Background Jobs

High-throughput processing with Celery:

- Resume parsing and candidate matching
- Payslip PDF generation and distribution
- Notification delivery across multiple channels
- Search index updates and data synchronization

### Event-Driven Architecture

Domain events published over NATS/Kafka:

- `employee.created`, `employee.updated`, `employee.terminated`
- `leave.requested`, `leave.approved`, `leave.rejected`
- `timesheet.submitted`, `timesheet.approved`
- `payroll.run.started`, `payroll.run.completed`

## Agent Integration

The `agents-gw` service provides AI agent integration capabilities:

- **Task APIs**: Mirror human actions (create leave requests, approve timesheets, run payroll)
- **OAuth Integration**: Client credentials flow with scoped agent roles
- **Human-in-the-Loop**: Approval/denial endpoints with full audit trails
- **Simulation Mode**: Dry-run capabilities against sandbox tenants

## Deployment

### Local Development

```bash
# Start with hot reload
make dev.up

# View logs
make dev.logs

# Stop services
make dev.down
```

### Production Deployment

```bash
# Build production images
make build.all

# Deploy with Helm
make deploy.prod

# Monitor deployment
make deploy.status
```

## Monitoring & Observability

### Metrics

- **Application Metrics**: Request rates, response times, error rates
- **Business Metrics**: Employee counts, leave utilization, payroll processing times
- **Infrastructure Metrics**: Database performance, queue depths, cache hit rates

### Logging

- **Structured Logging**: JSON format with correlation IDs
- **Centralized Collection**: Loki for log aggregation
- **Log Levels**: Configurable per service with runtime adjustment

### Tracing

- **Distributed Tracing**: OpenTelemetry with Jaeger backend
- **Request Correlation**: End-to-end request tracking across services
- **Performance Insights**: Bottleneck identification and optimization

## Contributing

### Development Guidelines

1. **Code Style**: Follow PEP 8 with Black formatting
2. **Type Hints**: Use Pydantic models and type annotations
3. **Testing**: Maintain >90% test coverage
4. **Documentation**: Update API docs and ADRs for significant changes

### Architecture Decision Records (ADRs)

See `docs/adr/` for architectural decisions and their rationale:

- [ADR-001: Microservices Architecture](docs/adr/001-microservices-architecture.md)
- [ADR-002: Database Isolation Strategy](docs/adr/002-db-isolation.md)
- [ADR-003: Event Bus Strategy](docs/adr/003-event-bus.md)
- [ADR-004: Workflow Management Strategy](docs/adr/004-workflows.md)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For questions, issues, or contributions:

- **Issues**: [GitHub Issues](https://github.com/AkhileshMishra/AgenticHR/issues)
- **Discussions**: [GitHub Discussions](https://github.com/AkhileshMishra/AgenticHR/discussions)
- **Documentation**: [Project Wiki](https://github.com/AkhileshMishra/AgenticHR/wiki)
