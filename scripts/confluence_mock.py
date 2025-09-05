"""Mock Confluence API for development and testing."""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import random


class MockConfluenceAPI:
    """Mock Confluence API that simulates real Confluence responses."""
    
    def __init__(self):
        """Initialize mock data."""
        self.mock_spaces = ["QA", "ENG", "DOC", "API"]
        self.mock_labels = ["checklist", "guide", "api", "testing", "auth", "deployment"]
        self.mock_pages = self._generate_mock_pages()
    
    def _generate_mock_pages(self) -> List[Dict[str, Any]]:
        """Generate mock Confluence pages."""
        pages = []
        
        # QA Testing pages
        qa_pages = [
            {
                "id": "123456789",
                "title": "Authentication Testing Checklist",
                "space": "QA",
                "url": "https://example.atlassian.net/wiki/spaces/QA/pages/123456789/Auth+Testing",
                "labels": ["checklist", "auth", "testing"],
                "version": 5,
                "updated": datetime.now() - timedelta(days=2),
                "content": """
# Authentication Testing Checklist

## Login Flow Testing
- [ ] Valid credentials login
- [ ] Invalid credentials handling
- [ ] Password reset functionality
- [ ] Account lockout after failed attempts
- [ ] Session timeout testing
- [ ] Remember me functionality

## Multi-Factor Authentication
- [ ] SMS verification
- [ ] Email verification
- [ ] TOTP authenticator apps
- [ ] Backup codes usage
- [ ] MFA bypass attempts

## Security Testing
- [ ] SQL injection attempts
- [ ] XSS protection
- [ ] CSRF token validation
- [ ] Session hijacking prevention
- [ ] Brute force protection

## Edge Cases
- [ ] Concurrent login sessions
- [ ] Password change during active session
- [ ] Account deletion scenarios
"""
            },
            {
                "id": "123456790",
                "title": "API Testing Guidelines",
                "space": "QA",
                "url": "https://example.atlassian.net/wiki/spaces/QA/pages/123456790/API+Testing",
                "labels": ["api", "testing", "guide"],
                "version": 3,
                "updated": datetime.now() - timedelta(days=5),
                "content": """
# API Testing Guidelines

## REST API Testing
### GET Endpoints
- Verify response status codes
- Validate response structure
- Check data accuracy
- Test pagination
- Verify sorting and filtering

### POST/PUT Endpoints
- Valid payload testing
- Invalid payload handling
- Required field validation
- Data type validation
- Boundary value testing

### Error Handling
- 400 Bad Request scenarios
- 401 Unauthorized responses
- 403 Forbidden access
- 404 Not Found cases
- 500 Internal Server errors

## Performance Testing
- Response time benchmarks
- Concurrent user load
- Rate limiting verification
- Timeout handling
"""
            },
            {
                "id": "123456791",
                "title": "UI Testing Procedures",
                "space": "QA",
                "url": "https://example.atlassian.net/wiki/spaces/QA/pages/123456791/UI+Testing",
                "labels": ["ui", "testing", "checklist"],
                "version": 7,
                "updated": datetime.now() - timedelta(days=1),
                "content": """
# UI Testing Procedures

## Cross-Browser Testing
- Chrome latest version
- Firefox latest version
- Safari (Mac/iOS)
- Edge browser
- Mobile browsers

## Responsive Design
- Desktop resolutions (1920x1080, 1366x768)
- Tablet resolutions (768x1024)
- Mobile resolutions (375x667, 414x896)
- Orientation changes (portrait/landscape)

## Form Testing
- Input field validation
- Dropdown selections
- Checkbox/radio buttons
- File upload functionality
- Form submission
- Error message display

## Navigation Testing
- Menu functionality
- Breadcrumb navigation
- Search functionality
- Back/forward buttons
- Deep linking
"""
            }
        ]
        
        # Engineering documentation
        eng_pages = [
            {
                "id": "234567890",
                "title": "Authentication Service Architecture",
                "space": "ENG",
                "url": "https://example.atlassian.net/wiki/spaces/ENG/pages/234567890/Auth+Architecture",
                "labels": ["auth", "architecture"],
                "version": 12,
                "updated": datetime.now() - timedelta(days=7),
                "content": """
# Authentication Service Architecture

## Overview
The authentication service handles user login, session management, and authorization across all applications.

## Components
### Auth Gateway
- JWT token validation
- Rate limiting
- Request routing
- Session management

### User Service
- User profile management
- Password hashing (bcrypt)
- Account activation
- Password reset workflows

### MFA Service
- TOTP generation/validation
- SMS delivery
- Email verification
- Backup code management

## Security Measures
- Password complexity requirements
- Account lockout policies
- Session timeout configuration
- HTTPS enforcement
- CSRF protection
- XSS prevention

## Database Schema
### Users Table
- id (UUID)
- email (unique)
- password_hash
- created_at
- updated_at
- last_login
- failed_attempts
- locked_until

### Sessions Table
- session_id (UUID)
- user_id (FK)
- created_at
- expires_at
- ip_address
- user_agent
"""
            },
            {
                "id": "234567891",
                "title": "Deployment Pipeline Documentation",
                "space": "ENG",
                "url": "https://example.atlassian.net/wiki/spaces/ENG/pages/234567891/Deployment",
                "labels": ["deployment", "cicd"],
                "version": 8,
                "updated": datetime.now() - timedelta(days=3),
                "content": """
# Deployment Pipeline Documentation

## CI/CD Pipeline Stages
1. **Code Commit** - Trigger on push to main
2. **Unit Tests** - Run test suite
3. **Security Scan** - SAST/DAST analysis
4. **Build** - Create Docker images
5. **Staging Deploy** - Deploy to staging environment
6. **Integration Tests** - Run E2E tests
7. **Production Deploy** - Deploy to production
8. **Health Checks** - Verify deployment success

## Environment Configuration
### Staging
- URL: https://staging.example.com
- Database: PostgreSQL 14
- Monitoring: DataDog
- Logging: ELK stack

### Production
- URL: https://app.example.com
- Database: PostgreSQL 14 (RDS)
- Monitoring: DataDog + PagerDuty
- Logging: CloudWatch + ELK

## Rollback Procedures
1. Identify deployment issue
2. Trigger rollback via GitHub Actions
3. Verify previous version health
4. Notify stakeholders
5. Post-mortem documentation
"""
            }
        ]
        
        # Documentation pages
        doc_pages = [
            {
                "id": "345678901",
                "title": "API Documentation Standards",
                "space": "DOC",
                "url": "https://example.atlassian.net/wiki/spaces/DOC/pages/345678901/API+Docs",
                "labels": ["api", "documentation"],
                "version": 4,
                "updated": datetime.now() - timedelta(days=10),
                "content": """
# API Documentation Standards

## OpenAPI Specification
All APIs must include:
- Complete endpoint documentation
- Request/response schemas
- Authentication requirements
- Error response formats
- Example requests/responses

## Documentation Structure
### Endpoint Documentation
- HTTP method and URL
- Description and purpose
- Path parameters
- Query parameters
- Request body schema
- Response schemas
- Status codes
- Error responses

### Authentication
- Auth method (Bearer token, API key, etc.)
- Token format and validation
- Scope and permissions
- Token refresh procedures

## Code Examples
Provide examples in:
- cURL
- JavaScript
- Python
- PHP
- Java
"""
            }
        ]
        
        pages.extend(qa_pages)
        pages.extend(eng_pages)
        pages.extend(doc_pages)
        
        return pages
    
    def get_pages(
        self,
        space_keys: Optional[List[str]] = None,
        labels: Optional[List[str]] = None,
        updated_since: Optional[datetime] = None,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """Get pages with filtering."""
        filtered_pages = []
        
        for page in self.mock_pages:
            # Filter by space
            if space_keys and page["space"] not in space_keys:
                continue
            
            # Filter by labels
            if labels:
                page_labels = set(page["labels"])
                filter_labels = set(labels)
                if not page_labels.intersection(filter_labels):
                    continue
            
            # Filter by update date
            if updated_since and page["updated"] < updated_since:
                continue
            
            filtered_pages.append(page)
        
        # Apply limit
        return filtered_pages[:limit]
    
    def get_page_content(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Get full page content by ID."""
        for page in self.mock_pages:
            if page["id"] == page_id:
                return page
        return None
    
    def normalize_content(self, content: str) -> str:
        """Simulate content normalization (remove macros, format, etc.)."""
        # Remove Confluence macros (simplified)
        import re
        
        # Remove macro tags
        content = re.sub(r'\{[^}]+\}', '', content)
        
        # Normalize whitespace
        content = re.sub(r'\n\s*\n', '\n\n', content)
        content = content.strip()
        
        return content
    
    def simulate_api_delay(self):
        """Simulate API response delay."""
        import time
        time.sleep(random.uniform(0.1, 0.5))  # 100-500ms delay
