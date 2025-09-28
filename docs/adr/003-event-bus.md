# ADR-003: Event Bus Strategy

## Status

Proposed

## Context

AgenticHR requires an event-driven architecture to handle domain events, asynchronous tasks, and inter-service communication. We need to choose an event bus technology that provides simplicity for development while supporting the scalability and reliability requirements of an HR management system.

## Decision

Use **NATS JetStream** for domain events and async tasks, with **Kafka as optional** when needing long retention or complex stream processing.

### Primary Choice: NATS JetStream

**NATS JetStream** will serve as our primary event bus for most use cases including domain events, workflow triggers, and asynchronous task processing.

**Kafka integration** will be added later when we need advanced features like long-term event retention for analytics, complex event sourcing, or Change Data Capture (CDC) scenarios.

## Rationale

### Simplicity and Operations Fit

**NATS JetStream** provides a much simpler operational model compared to Kafka, with easier clustering, configuration, and monitoring. This aligns with our goal of minimizing operational overhead while building the platform.

**Lower latency development loop** enables faster iteration during development and testing phases, improving developer productivity.

**Built-in persistence** and delivery guarantees provide reliability without the complexity of Kafka's partition management and consumer group coordination.

## Alternatives Considered

### Apache Kafka
**Pros**: Industry standard, excellent for high-throughput scenarios, rich ecosystem
**Cons**: Complex operations, heavy resource usage, steep learning curve, overkill for initial requirements

### Redis Streams
**Pros**: Simple setup, good performance, familiar Redis operations
**Cons**: Limited durability guarantees, not designed for complex event routing

### RabbitMQ
**Pros**: Mature message broker, good routing capabilities, management UI
**Cons**: More complex than NATS, less suited for event streaming patterns

### Amazon EventBridge / Google Pub/Sub
**Pros**: Fully managed, serverless scaling, cloud-native integrations
**Cons**: Vendor lock-in, higher costs, less control over infrastructure

## Consequences

### Positive

**Faster Development Cycle**: NATS JetStream's simplicity reduces the time needed to implement and test event-driven features.

**Lower Operational Overhead**: Minimal configuration and maintenance compared to Kafka clusters, reducing DevOps burden.

**Built-in Reliability**: JetStream provides persistence, acknowledgments, and replay capabilities without additional complexity.

**Flexible Deployment**: Can run in development, testing, and production with the same configuration patterns.

**Future Flexibility**: Can add Kafka later for specific use cases without changing the overall event-driven architecture.

### Negative

**Limited Ecosystem**: Smaller ecosystem compared to Kafka, fewer third-party integrations and tools.

**Scaling Considerations**: May need to revisit for very high-throughput scenarios (>100k events/second).

**Analytics Integration**: Will need Kafka or similar for advanced analytics and long-term event storage requirements.

**Learning Curve**: Team may need to learn NATS-specific concepts and patterns.

### Mitigation Strategies

**Abstraction Layer**: Implement event publishing/consuming through abstraction interfaces to enable future technology changes.

**Monitoring**: Set up comprehensive monitoring for NATS JetStream performance and reliability metrics.

**Documentation**: Create clear guidelines for event schema design, naming conventions, and usage patterns.

**Kafka Readiness**: Design event schemas and patterns that can easily migrate to Kafka when needed.

## Implementation Plan

### Phase 1: NATS JetStream Foundation
- Set up NATS JetStream cluster in development and production
- Implement basic event publishing and consuming patterns
- Create shared libraries for event handling

### Phase 2: Domain Events
- Implement domain events for core HR entities (employees, leave requests, etc.)
- Add event-driven workflows for onboarding and offboarding
- Create event sourcing patterns for audit trails

### Phase 3: Async Processing
- Move background tasks to event-driven processing
- Implement retry and dead letter queue patterns
- Add event-based notifications and alerts

### Phase 4: Advanced Features
- Evaluate Kafka integration for analytics use cases
- Implement event replay and debugging capabilities
- Add cross-service event choreography patterns

## Event Categories

### Domain Events
- Employee lifecycle events (created, updated, terminated)
- Leave request events (submitted, approved, rejected)
- Payroll processing events (calculated, paid, failed)

### System Events
- Authentication events (login, logout, MFA)
- Integration events (external system sync)
- Audit events (data access, configuration changes)

### Workflow Events
- Onboarding process steps
- Approval workflow state changes
- Notification triggers

## Monitoring and Evaluation

**Performance Metrics**: Monitor event throughput, latency, and processing times across different event types.

**Reliability Metrics**: Track event delivery success rates, retry patterns, and dead letter queue usage.

**Operational Metrics**: Monitor NATS JetStream resource usage, cluster health, and maintenance overhead.

**Developer Experience**: Gather feedback on ease of use, debugging capabilities, and development workflow impact.

**Scaling Thresholds**: Evaluate Kafka migration when event volume exceeds 50k events/second or retention requirements exceed 30 days.

## References

- [NATS JetStream Documentation](https://docs.nats.io/jetstream)
- [Event-Driven Architecture Patterns](https://microservices.io/patterns/data/event-driven-architecture.html)
- [Choosing an Event Bus](https://blog.scottlogic.com/2018/04/17/comparing-big-data-messaging.html)
- [NATS vs Kafka Comparison](https://nats.io/blog/nats-vs-apache-kafka/)
