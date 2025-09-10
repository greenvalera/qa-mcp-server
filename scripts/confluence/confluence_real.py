"""Real Confluence API client."""

import re
import html
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from atlassian import Confluence
from app.config import settings


class RealConfluenceAPI:
    """Real Confluence API client using atlassian-python-api."""
    
    def __init__(self):
        """Initialize Confluence API client."""
        if not settings.confluence_base_url or not settings.confluence_auth_token:
            raise ValueError(
                "CONFLUENCE_BASE_URL and CONFLUENCE_AUTH_TOKEN must be set in environment"
            )
        
        # Try different authentication methods
        if '@' in settings.confluence_auth_token:
            # If token contains @, assume it's email:token format
            email, token = settings.confluence_auth_token.split(':', 1)
            self.confluence = Confluence(
                url=settings.confluence_base_url,
                username=email,
                password=token
            )
        else:
            # Use token authentication
            self.confluence = Confluence(
                url=settings.confluence_base_url,
                token=settings.confluence_auth_token
            )
    
    def get_pages_by_ids(
        self,
        page_ids: List[str],
        include_children: bool = True
    ) -> List[Dict[str, Any]]:
        """Get specific pages by IDs and optionally their children."""
        all_pages = []
        
        for page_id in page_ids:
            try:
                print(f"Fetching page {page_id}...")
                # Get the root page
                page = self.confluence.get_page_by_id(
                    page_id,
                    expand='body.storage,version,metadata.labels,space'
                )
                print(f"Page response type: {type(page)}")
                if isinstance(page, dict):
                    print(f"Page keys: {list(page.keys())}")
                else:
                    print(f"Page content: {str(page)[:200]}")
                
                page_data = self._extract_page_data(page)
                all_pages.append(page_data)
                print(f"Successfully processed page: {page_data['title']}")
                
                # Get child pages recursively if requested
                if include_children:
                    children = self._get_child_pages_recursive(page_id)
                    all_pages.extend(children)
                    print(f"Found {len(children)} child pages")
                    
            except Exception as e:
                print(f"Error processing page {page_id}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        return all_pages
    
    def _get_child_pages_recursive(self, parent_page_id: str) -> List[Dict[str, Any]]:
        """Recursively get all child pages."""
        children = []
        
        try:
            # Get direct children
            child_pages = self.confluence.get_page_child_by_type(
                parent_page_id,
                type='page',
                expand='body.storage,version,metadata.labels,space'
            )
            
            for child in child_pages:
                try:
                    child_data = self._extract_page_data(child)
                    children.append(child_data)
                    
                    # Recursively get children of this child
                    grandchildren = self._get_child_pages_recursive(child['id'])
                    children.extend(grandchildren)
                    
                except Exception as e:
                    print(f"Error processing child page {child.get('id', 'unknown')}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error getting children of page {parent_page_id}: {e}")
        
        return children

    def get_pages(
        self,
        space_keys: Optional[List[str]] = None,
        labels: Optional[List[str]] = None,
        updated_since: Optional[datetime] = None,
        limit: int = 25
    ) -> List[Dict[str, Any]]:
        """Get pages with filtering."""
        all_pages = []
        
        # If specific spaces are requested, get pages from those spaces
        if space_keys:
            spaces_to_search = space_keys
        else:
            # Get all spaces
            spaces = self.confluence.get_all_spaces(start=0, limit=500)
            spaces_to_search = [space['key'] for space in spaces['results']]
        
        for space_key in spaces_to_search:
            try:
                # Get pages from space
                pages = self.confluence.get_all_pages_from_space(
                    space=space_key,
                    start=0,
                    limit=100,
                    expand='version,metadata.labels'
                )
                
                for page in pages:
                    try:
                        # Get full page content
                        page_content = self.confluence.get_page_by_id(
                            page['id'],
                            expand='body.storage,version,metadata.labels,space'
                        )
                        
                        # Extract page data
                        page_data = self._extract_page_data(page_content)
                        
                        # Apply filters
                        if self._should_include_page(page_data, labels, updated_since):
                            all_pages.append(page_data)
                            
                    except Exception as e:
                        print(f"Error processing page {page['id']}: {e}")
                        continue
                        
            except Exception as e:
                print(f"Error accessing space {space_key}: {e}")
                continue
        
        # Sort by update date (newest first) and apply limit
        all_pages.sort(key=lambda x: x['updated'], reverse=True)
        return all_pages[:limit]
    
    def _extract_page_data(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Extract standardized page data from Confluence API response."""
        # Handle case where page might be a string (error response)
        if not isinstance(page, dict):
            raise ValueError(f"Invalid page data: {type(page)}")
        
        # Get labels
        labels = []
        if 'metadata' in page and 'labels' in page['metadata']:
            if 'results' in page['metadata']['labels']:
                labels = [label['name'] for label in page['metadata']['labels']['results']]
            else:
                labels = [label['name'] for label in page['metadata']['labels']]
        
        # Get content
        content = ""
        if 'body' in page and 'storage' in page['body']:
            content = page['body']['storage']['value']
        
        # Get space key
        space_key = 'UNKNOWN'
        if 'space' in page:
            if isinstance(page['space'], dict):
                space_key = page['space'].get('key', 'UNKNOWN')
            else:
                space_key = str(page['space'])
        
        # Build page URL
        base_url = settings.confluence_base_url.rstrip('/')
        page_url = f"{base_url}/pages/{page['id']}"
        
        # Get version info
        version_number = 1
        updated_time = datetime.now()
        
        if 'version' in page:
            if isinstance(page['version'], dict):
                version_number = page['version'].get('number', 1)
                if 'when' in page['version']:
                    updated_time = datetime.fromisoformat(
                        page['version']['when'].replace('Z', '+00:00')
                    )
        
        return {
            "id": str(page['id']),
            "title": page.get('title', 'Untitled'),
            "space": space_key,
            "url": page_url,
            "labels": labels,
            "version": version_number,
            "updated": updated_time,
            "content": content
        }
    
    def _should_include_page(
        self, 
        page: Dict[str, Any], 
        labels: Optional[List[str]], 
        updated_since: Optional[datetime]
    ) -> bool:
        """Check if page should be included based on filters."""
        # Filter by labels
        if labels:
            page_labels = set(page["labels"])
            filter_labels = set(labels)
            if not page_labels.intersection(filter_labels):
                return False
        
        # Filter by update date
        if updated_since and page["updated"] < updated_since:
            return False
        
        return True
    
    def get_page_content(self, page_id: str) -> Optional[Dict[str, Any]]:
        """Get full page content by ID."""
        try:
            page = self.confluence.get_page_by_id(
                page_id,
                expand='body.storage,version,metadata.labels,space'
            )
            return self._extract_page_data(page)
        except Exception as e:
            print(f"Error getting page {page_id}: {e}")
            return None
    
    def normalize_content(self, content: str) -> str:
        """Normalize Confluence storage format content to plain text."""
        if not content:
            return ""
        
        # Remove CDATA sections
        content = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', content, flags=re.DOTALL)
        
        # Convert common Confluence macros to readable text
        content = self._convert_macros(content)
        
        # Remove HTML tags but preserve structure
        content = self._html_to_text(content)
        
        # Normalize whitespace
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        content = content.strip()
        
        return content
    
    def _convert_macros(self, content: str) -> str:
        """Convert Confluence macros to readable text."""
        # Code macro
        content = re.sub(
            r'<ac:structured-macro ac:name="code"[^>]*>.*?<ac:plain-text-body><!\[CDATA\[(.*?)\]\]></ac:plain-text-body>.*?</ac:structured-macro>',
            r'```\n\1\n```',
            content,
            flags=re.DOTALL
        )
        
        # Info macro
        content = re.sub(
            r'<ac:structured-macro ac:name="info"[^>]*>(.*?)</ac:structured-macro>',
            r'ℹ️ \1',
            content,
            flags=re.DOTALL
        )
        
        # Warning macro
        content = re.sub(
            r'<ac:structured-macro ac:name="warning"[^>]*>(.*?)</ac:structured-macro>',
            r'⚠️ \1',
            content,
            flags=re.DOTALL
        )
        
        # Note macro
        content = re.sub(
            r'<ac:structured-macro ac:name="note"[^>]*>(.*?)</ac:structured-macro>',
            r'📝 \1',
            content,
            flags=re.DOTALL
        )
        
        # Table of contents
        content = re.sub(
            r'<ac:structured-macro ac:name="toc"[^>]*>.*?</ac:structured-macro>',
            '[Table of Contents]',
            content,
            flags=re.DOTALL
        )
        
        # Remove other macros (keep content if available)
        content = re.sub(
            r'<ac:structured-macro[^>]*>(.*?)</ac:structured-macro>',
            r'\1',
            content,
            flags=re.DOTALL
        )
        
        return content
    
    def _html_to_text(self, content: str) -> str:
        """Convert HTML to plain text while preserving structure."""
        # Headers
        content = re.sub(r'<h([1-6])[^>]*>(.*?)</h[1-6]>', r'\n\n' + r'#' * 1 + r' \2\n\n', content)
        
        # Paragraphs
        content = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', content, flags=re.DOTALL)
        
        # Line breaks
        content = re.sub(r'<br[^>]*/?>', '\n', content)
        
        # Lists
        content = re.sub(r'<ul[^>]*>', '\n', content)
        content = re.sub(r'</ul>', '\n', content)
        content = re.sub(r'<ol[^>]*>', '\n', content)
        content = re.sub(r'</ol>', '\n', content)
        content = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', content, flags=re.DOTALL)
        
        # Tables (simple conversion)
        content = re.sub(r'<table[^>]*>', '\n\n', content)
        content = re.sub(r'</table>', '\n\n', content)
        content = re.sub(r'<tr[^>]*>', '\n', content)
        content = re.sub(r'</tr>', '', content)
        content = re.sub(r'<t[hd][^>]*>(.*?)</t[hd]>', r'\1 | ', content, flags=re.DOTALL)
        
        # Strong/bold
        content = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', content, flags=re.DOTALL)
        content = re.sub(r'<b[^>]*>(.*?)</b>', r'**\1**', content, flags=re.DOTALL)
        
        # Emphasis/italic
        content = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', content, flags=re.DOTALL)
        content = re.sub(r'<i[^>]*>(.*?)</i>', r'*\1*', content, flags=re.DOTALL)
        
        # Links
        content = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'\2 (\1)', content, flags=re.DOTALL)
        
        # Remove remaining HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        # Decode HTML entities
        content = html.unescape(content)
        
        return content
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Confluence."""
        try:
            # Get current user info
            try:
                # Try different methods to get user info
                if hasattr(self.confluence, 'myself'):
                    user = self.confluence.myself()
                    if isinstance(user, dict):
                        user_name = user.get('displayName', user.get('username', 'Unknown'))
                    else:
                        user_name = str(user)
                else:
                    user_name = "API User"
            except Exception as e:
                user_name = f"API User"
            
            # Get a few spaces to verify access
            spaces = self.confluence.get_all_spaces(start=0, limit=5)
            
            return {
                "success": True,
                "user": user_name,
                "spaces_count": len(spaces.get('results', [])),
                "spaces": [s['name'] for s in spaces.get('results', [])]
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
