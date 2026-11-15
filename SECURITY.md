# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Privacy and Threat Model

**Kisukisu is designed from the ground up as a zero-trust, local-first application.**
- **No Network Ingress/Egress**: Kisukisu does not connect to external servers, cloud databases, or remote telemetry endpoints.
- **Local File Security**: Scripts and configurations are stored in the user's home folder (`~/.kisukisu/`). Storage is bounded by standard operating system access controls.
- **No Covert Surveillance**: Kisukisu does not capture camera feeds, microphones, or keystrokes outside of its own window.

## Reporting a Vulnerability

If you discover a security vulnerability within Kisukisu, please report it privately:
- **Email**: `kishoredxd@gmail.com`
- Please do not disclose vulnerabilities publicly via GitHub Issues until a fix has been verified and released.
- You will receive an acknowledgment within 48 hours and regular updates on the resolution timeline.
