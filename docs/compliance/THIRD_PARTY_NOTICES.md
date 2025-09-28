# Third-Party Notices

This project includes open-source components. The following table summarizes licenses (see sbom.spdx.json for full list).

## Software Bill of Materials (SBOM)

For a complete and up-to-date list of all dependencies, see the automatically generated SBOM file: [`sbom.spdx.json`](./sbom.spdx.json)

To regenerate the SBOM, run:
```bash
make security.scan
```

## Key Dependencies

| Component        | Version | License | Source URL |
|------------------|---------|---------|-----------|
| fastapi          | 0.104.1 | MIT     | https://pypi.org/project/fastapi/ |
| pydantic         | 2.5.0   | MIT     | https://pypi.org/project/pydantic/ |
| uvicorn          | 0.24.0  | BSD-3   | https://pypi.org/project/uvicorn/ |
| SQLAlchemy       | 2.0.23  | MIT     | https://pypi.org/project/SQLAlchemy/ |
| jose[cryptography]| 3.3.0  | MIT     | https://pypi.org/project/python-jose/ |
| alembic          | 1.12.1  | MIT     | https://pypi.org/project/alembic/ |
| asyncpg          | 0.29.0  | Apache-2.0 | https://pypi.org/project/asyncpg/ |
| redis            | 5.0.1   | MIT     | https://pypi.org/project/redis/ |
| httpx            | 0.25.2  | BSD-3   | https://pypi.org/project/httpx/ |
| pydantic-settings| 2.1.0   | MIT     | https://pypi.org/project/pydantic-settings/ |

## Container Images

| Image            | Version | License | Source URL |
|------------------|---------|---------|-----------|
| python           | 3.12-slim | PSF + Debian | https://hub.docker.com/_/python |
| postgres         | 15-alpine | PostgreSQL + Alpine | https://hub.docker.com/_/postgres |
| redis            | 7-alpine | BSD-3 + Alpine | https://hub.docker.com/_/redis |
| kong             | 3.4     | Apache-2.0 | https://hub.docker.com/_/kong |
| keycloak/keycloak| 22.0    | Apache-2.0 | https://hub.docker.com/r/keycloak/keycloak |

## Infrastructure Dependencies

| Component        | License | Description |
|------------------|---------|-------------|
| Docker           | Apache-2.0 | Container runtime |
| Docker Compose   | Apache-2.0 | Container orchestration |
| Kong Gateway     | Apache-2.0 | API Gateway |
| Keycloak         | Apache-2.0 | Identity and Access Management |
| PostgreSQL       | PostgreSQL License | Database |
| Redis            | BSD-3-Clause | Cache and message broker |

## Development Dependencies

| Component        | Version | License | Source URL |
|------------------|---------|---------|-----------|
| pytest           | 7.4.3   | MIT     | https://pypi.org/project/pytest/ |
| pytest-asyncio  | 0.21.1  | Apache-2.0 | https://pypi.org/project/pytest-asyncio/ |
| black            | 23.11.0 | MIT     | https://pypi.org/project/black/ |
| ruff             | 0.1.6   | MIT     | https://pypi.org/project/ruff/ |
| mypy             | 1.7.1   | MIT     | https://pypi.org/project/mypy/ |

## License Compliance

### MIT License Components
The majority of Python dependencies use the MIT License, which allows:
- Commercial use
- Modification
- Distribution
- Private use

Requirements:
- Include copyright notice
- Include license text

### BSD-3-Clause Components
Some components use BSD-3-Clause license, which allows:
- Commercial use
- Modification
- Distribution
- Private use

Requirements:
- Include copyright notice
- Include license text
- Cannot use contributor names for endorsement

### Apache-2.0 Components
Infrastructure components primarily use Apache-2.0 license, which allows:
- Commercial use
- Modification
- Distribution
- Patent use
- Private use

Requirements:
- Include copyright notice
- Include license text
- State changes
- Include NOTICE file if present

### PostgreSQL License
PostgreSQL uses its own license similar to MIT/BSD, allowing:
- Commercial use
- Modification
- Distribution
- Private use

Requirements:
- Include copyright notice

## Compliance Procedures

### Dependency Updates
1. **Automated Scanning**: Dependencies are scanned automatically via `make security.scan`
2. **License Review**: New dependencies require license compatibility review
3. **SBOM Generation**: Software Bill of Materials is updated with each release
4. **Vulnerability Monitoring**: Security vulnerabilities are tracked and addressed

### License Compatibility
All included dependencies have been reviewed for compatibility with commercial use and distribution. The project maintains compatibility with:
- MIT License (primary project license)
- Commercial deployment requirements
- Open source distribution requirements

### Attribution Requirements
This document serves as the primary attribution for all third-party components. Additional attribution files are maintained in:
- `LICENSE` - Primary project license
- `sbom.spdx.json` - Complete dependency list with versions and licenses
- Individual service `requirements.txt` files

## Security and Vulnerability Management

### Vulnerability Scanning
Regular security scans are performed using:
- **Trivy**: Container and filesystem vulnerability scanning
- **Safety**: Python dependency vulnerability checking
- **Dependabot**: Automated dependency updates (GitHub)

### Update Policy
- **Critical vulnerabilities**: Patched within 24 hours
- **High vulnerabilities**: Patched within 1 week
- **Medium/Low vulnerabilities**: Addressed in next scheduled release

### Reporting
Security vulnerabilities in dependencies are tracked in:
- GitHub Security Advisories
- Internal security tracking system
- SBOM vulnerability annotations

## Contact

For questions about third-party licenses or compliance:
- **Security Issues**: Report via GitHub Security Advisories
- **License Questions**: Create an issue in the project repository
- **Compliance Inquiries**: Contact the project maintainers

---

> **Note**: This document is automatically updated when dependencies change. 
> Generate SBOM: `make security.scan` → `docs/compliance/sbom.spdx.json`. 
> Keep this file committed for releases.
