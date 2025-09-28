# ADR-002: Database Isolation Strategy

## Status

Proposed

## Context

AgenticHR needs to support multi-tenant isolation with minimal operational overhead while maintaining data security and compliance requirements. We need to decide on the database isolation strategy that balances simplicity, security, and scalability.

## Decision

Start with **schema-per-tenant** on PostgreSQL with Row Level Security (RLS) readiness, and reevaluate when we exceed 100 tenants.

### Implementation Approach

**Schema-per-tenant architecture** where each tenant gets their own database schema within a shared PostgreSQL instance. This provides logical isolation while maintaining operational simplicity.

**Row Level Security (RLS) preparation** ensures we can add fine-grained access control for high-sensitivity data without major architectural changes.

**Migration discipline** will be maintained through automated schema management and consistent deployment processes across all tenant schemas.

## Alternatives Considered

### Database-per-tenant
**Pros**: Complete isolation, easier backup/restore per tenant
**Cons**: High operational overhead, resource inefficiency, complex connection pooling

### Shared tables with tenant_id
**Pros**: Simplest implementation, single schema to manage
**Cons**: Risk of data leakage, complex queries, limited isolation

### Database-per-service
**Pros**: Service isolation, independent scaling
**Cons**: Cross-service queries become complex, transaction boundaries unclear

## Consequences

### Positive

**Operational Simplicity**: Single PostgreSQL instance to manage with multiple schemas is much simpler than managing hundreds of separate databases.

**Resource Efficiency**: Shared connection pools, buffer pools, and system resources across tenants while maintaining logical separation.

**Migration Management**: Single migration process can be applied across all tenant schemas with consistent tooling.

**Backup Strategy**: Simplified backup and disaster recovery procedures with schema-level granularity when needed.

**Development Workflow**: Developers can work with a single database instance while testing multi-tenant scenarios.

### Negative

**Scaling Limitations**: May hit PostgreSQL limits with very large numbers of tenants (>100 schemas).

**Blast Radius**: Issues with the shared PostgreSQL instance affect all tenants simultaneously.

**Schema Management**: Need robust tooling to manage schema creation, updates, and cleanup across tenants.

**Query Complexity**: Cross-tenant analytics require careful schema selection and query planning.

### Mitigation Strategies

**RLS Readiness**: Design tables with tenant identification columns and RLS policies ready for activation when needed.

**Monitoring**: Implement per-schema monitoring to identify resource usage patterns and scaling needs.

**Schema Automation**: Build robust tooling for automated schema provisioning, migration, and cleanup.

**Backup Granularity**: Implement schema-level backup and restore capabilities for tenant-specific recovery.

**Performance Optimization**: Use schema-specific indexes and partitioning strategies to maintain query performance.

## Implementation Plan

### Phase 1: Foundation (Current)
- Single schema design with tenant-aware models
- Basic multi-tenancy support in application layer
- Schema migration tooling

### Phase 2: Schema-per-tenant
- Automated tenant schema provisioning
- Schema-aware connection routing
- Tenant-specific migrations

### Phase 3: RLS Enhancement
- Row Level Security policies for sensitive data
- Fine-grained access control
- Audit logging per tenant

### Phase 4: Scale Optimization
- Schema partitioning strategies
- Cross-tenant analytics optimization
- Performance monitoring and alerting

## Monitoring and Evaluation

**Tenant Count Threshold**: Reevaluate architecture when approaching 100 active tenant schemas.

**Performance Metrics**: Monitor query performance, connection pool utilization, and schema management overhead.

**Operational Complexity**: Track time spent on schema management, backup/restore operations, and troubleshooting.

**Security Incidents**: Monitor for any cross-tenant data access issues or security breaches.

## References

- [PostgreSQL Schema Documentation](https://www.postgresql.org/docs/current/ddl-schemas.html)
- [Row Level Security in PostgreSQL](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [Multi-tenant Database Patterns](https://docs.microsoft.com/en-us/azure/sql-database/saas-tenancy-app-design-patterns)
- [Scaling Multi-tenant Applications](https://www.citusdata.com/blog/2016/10/03/designing-your-saas-database-for-high-scalability/)
