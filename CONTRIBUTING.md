# Contributing to Kisukisu (கிசுகிசு)

Thank you for your interest in contributing to **Kisukisu**!  
We are excited to build an elegant, privacy-first presenter companion together with the community.

## 🤝 Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## 🚀 How to Contribute

### 1. Reporting Bugs
- Search existing issues to ensure the bug hasn't already been reported.
- If not, open a new issue using our [Bug Report Template](.github/ISSUE_TEMPLATE/bug_report.md).
- Include your OS version, Python version, steps to reproduce, and any relevant error logs.

### 2. Suggesting Features
- Open a feature request using our [Feature Request Template](.github/ISSUE_TEMPLATE/feature_request.md).
- Clearly describe the use case and how it enhances the presenter experience while respecting our local-first, privacy-first principles.

### 3. Submitting Pull Requests
1. **Fork** the repository and create your feature branch:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. **Install development dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Write clean, documented code**:
   - Follow PEP 8 guidelines.
   - Respect our UI aesthetic: minimal, rounded pill geometry, obsidian glass contrast, zero clunkiness.
   - Maintain documentation integrity and Unicode support (especially Tamil script).
4. **Run unit tests**:
   ```bash
   python -m unittest discover -s tests -p "test_*.py"
   ```
   Ensure all tests pass before committing.
5. **Commit your changes**:
   ```bash
   git commit -m "feat: add speech pace indicator"
   ```
6. **Push to your fork** and submit a Pull Request to `main`.

## 🔒 Privacy & Architecture Guidelines
- **Zero Telemetry**: Never introduce external analytical trackers, phone-home network calls, or third-party account requirements.
- **Local-First**: All user data, scripts, and preferences must reside locally on the user's filesystem (`~/.kisukisu/`).
- **Graceful Fallbacks**: Features requiring OS-specific APIs (like Windows `WDA_EXCLUDEFROMCAPTURE`) must fail silently and gracefully on unsupported platforms.
