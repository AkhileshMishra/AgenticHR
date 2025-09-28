# Kong JWT Authentication Setup

## Overview

This document explains the JWT authentication setup between Kong API Gateway and Keycloak for AgenticHR. We have implemented **Option B** which configures Kong to verify JWT tokens at the gateway level using Keycloak's realm public key.

## Architecture

```
Client Request → Kong Gateway → JWT Verification → Backend Service
                      ↓
                 Keycloak Realm
                 (Token Issuer)
```

## Configuration Details

### Kong Configuration (`docker/kong/kong.yml`)

The Kong configuration implements centralized JWT verification with the following key components:

#### Services and Routes
- **auth-svc**: Authentication service at `/auth` path
- **employee-svc**: Employee management service at `/employee` path

#### Global Plugins

**CORS Plugin**: Enables cross-origin requests with proper headers including Authorization.

**Rate Limiting**: Protects against abuse with 100 requests/minute and 2000 requests/hour limits.

**JWT Plugin**: Global JWT authentication with the following configuration:
- `key_claim_name: "iss"` - Uses the issuer claim to identify the key
- `claims_to_verify: ["exp", "nbf"]` - Verifies expiration and not-before claims
- `maximum_expiration: 3600` - Maximum token lifetime of 1 hour
- Accepts tokens from Authorization header, URI parameter, or cookie

#### Consumer and JWT Secret

**Consumer**: `keycloak` consumer represents the Keycloak realm as a trusted issuer.

**JWT Secret**: Configured with:
- `key`: `http://keycloak:8080/realms/agentichr` (matches token issuer)
- `algorithm`: `RS256` (RSA with SHA-256)
- `rsa_public_key`: The realm's public key for signature verification

### Keycloak Configuration

The Keycloak realm is configured with:
- **Realm Name**: `agentichr`
- **Issuer URL**: `http://keycloak:8080/realms/agentichr`
- **Signing Algorithm**: RS256
- **Key Provider**: RSA-generated key pair

The private key is used by Keycloak to sign JWTs, while the corresponding public key is configured in Kong for verification.

## Token Flow

1. **Authentication**: Client authenticates with Keycloak
2. **Token Issuance**: Keycloak issues JWT with `iss: http://keycloak:8080/realms/agentichr`
3. **API Request**: Client includes JWT in Authorization header: `Bearer <token>`
4. **Gateway Verification**: Kong validates JWT signature using realm public key
5. **Service Access**: Valid requests are forwarded to backend services

## Security Features

### JWT Validation
- **Signature Verification**: Kong verifies JWT signature using Keycloak's public key
- **Expiration Check**: Tokens are validated for expiration (`exp` claim)
- **Not Before Check**: Tokens are validated for not-before time (`nbf` claim)
- **Issuer Validation**: Only tokens from the configured Keycloak realm are accepted

### Rate Limiting
- **Per-Minute Limit**: 100 requests per minute per client
- **Per-Hour Limit**: 2000 requests per hour per client
- **Fault Tolerant**: Continues operation even if rate limiting backend fails

### CORS Protection
- **Origin Control**: Configurable allowed origins
- **Method Control**: Specific HTTP methods allowed
- **Header Control**: Controlled header exposure
- **Credential Support**: Supports authenticated requests

## Development vs Production

### Development Configuration
- Origins set to `["*"]` for easy development
- Rate limits are generous for development workflow
- Keycloak accessible at `http://keycloak:8080`

### Production Considerations
- **Origins**: Restrict to specific domains
- **Rate Limits**: Adjust based on expected traffic
- **HTTPS**: Use HTTPS for Keycloak in production
- **Key Rotation**: Implement key rotation strategy
- **Monitoring**: Add logging and monitoring plugins

## Testing JWT Authentication

### 1. Obtain Token from Keycloak
```bash
curl -X POST http://localhost:8080/realms/agentichr/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=agentichr-app" \
  -d "username=admin@agentichr.local" \
  -d "password=admin123"
```

### 2. Use Token with Kong
```bash
curl -H "Authorization: Bearer <jwt_token>" \
  http://localhost:8000/employee/v1/employees
```

### 3. Expected Behavior
- **Valid Token**: Request forwarded to employee service
- **Invalid Token**: 401 Unauthorized response from Kong
- **Expired Token**: 401 Unauthorized response from Kong
- **No Token**: 401 Unauthorized response from Kong

## Troubleshooting

### Common Issues

**401 Unauthorized**: Check token validity, expiration, and issuer claim.

**CORS Errors**: Verify CORS plugin configuration and allowed origins.

**Rate Limiting**: Check if rate limits are exceeded.

**Key Mismatch**: Ensure Kong's public key matches Keycloak's private key.

### Debugging Commands

```bash
# Check Kong configuration
curl http://localhost:8001/config

# Check JWT plugin status
curl http://localhost:8001/plugins

# Check consumer configuration
curl http://localhost:8001/consumers/keycloak

# Decode JWT token (without verification)
echo "<jwt_token>" | cut -d. -f2 | base64 -d | jq
```

## Key Management

### Key Rotation Process
1. Generate new RSA key pair
2. Update Keycloak realm configuration
3. Update Kong JWT secret configuration
4. Deploy changes
5. Monitor for authentication errors

### Backup and Recovery
- Store private keys securely
- Backup Keycloak realm configuration
- Document key rotation procedures
- Test recovery procedures regularly

## References

- [Kong JWT Plugin Documentation](https://docs.konghq.com/hub/kong-inc/jwt/)
- [Keycloak JWT Token Documentation](https://www.keycloak.org/docs/latest/server_admin/#_token-exchange)
- [RFC 7519 - JSON Web Token (JWT)](https://tools.ietf.org/html/rfc7519)
- [RFC 7515 - JSON Web Signature (JWS)](https://tools.ietf.org/html/rfc7515)
