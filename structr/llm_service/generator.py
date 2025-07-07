import json
import time
import requests
from typing import Dict, List, Any, Optional
from models.pdp import ProductData, PDPBundle, AuditResult

# Import centralized configuration
from config import StructrConfig as CONFIG

class OllamaLLMService:
    """Service for generating and fixing PDPs using Ollama"""
    
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or CONFIG.get_llm_base_url()
        self.model = model or CONFIG.get_llm_model()
        
    def generate_pdp(self, product_data: ProductData) -> PDPBundle:
        """Generate a complete PDP from product data"""
        start_time = time.time()
        
        prompt = self._build_generation_prompt(product_data)
        html_content = self._call_ollama(prompt)
        
        # Clean up markdown artifacts
        html_content = html_content.replace('```html', '').replace('```', '').strip()
        
        # Extract metadata and schema
        metadata = self._extract_metadata(html_content)
        schema_markup = self._extract_schema(html_content)
        
        generation_time = time.time() - start_time
        
        return PDPBundle(
            product_id=product_data.handle,
            html_content=html_content,
            metadata=metadata,
            schema_markup=schema_markup,
            audit_result=AuditResult(product_id=product_data.handle, score=0),  # Will be filled by auditor
            generation_time=generation_time,
            model_used=self.model
        )
    
    def fix_pdp_issues(self, product_data: ProductData, audit_result: AuditResult, 
                      current_html: str) -> str:
        """Fix specific issues in a PDP based on audit results"""
        
        prompt = self._build_fix_prompt(product_data, audit_result, current_html)
        fixed_html = self._call_ollama(prompt)
        
        # Clean up markdown artifacts
        fixed_html = fixed_html.replace('```html', '').replace('```', '').strip()
        
        return fixed_html
    
    def _build_generation_prompt(self, product_data: ProductData) -> str:
        """Build prompt for generating a complete PDP"""
        
        return f"""Generate a complete, SEO-optimized HTML product detail page for this product. 
Focus on structure and metadata compliance.

Product Details:
- Handle: {product_data.handle}
- Title: {product_data.title}
- Description: {product_data.description or 'Not provided'}
- Price: ${product_data.price or 'Not provided'}
- Brand: {product_data.brand or 'Not provided'}
- Category: {product_data.category or 'Not provided'}
- Features: {', '.join(product_data.features) if product_data.features else 'None specified'}

Requirements:
1. Include proper HTML5 structure with head and body
2. Add complete SEO metadata (title, meta description, og tags)
3. Include JSON-LD Product schema markup
4. Create clean, semantic HTML for the product content
5. Ensure title is 30-60 characters
6. Ensure meta description is 120-160 characters
7. Include all required Product schema fields (@type, name, description, image, offers, brand)

Generate ONLY the HTML content, no explanations:"""

    def _build_fix_prompt(self, product_data: ProductData, audit_result: AuditResult, 
                         current_html: str) -> str:
        """Build prompt for fixing specific PDP issues"""
        
        issues_summary = []
        if audit_result.missing_fields:
            issues_summary.append(f"Missing fields: {', '.join(audit_result.missing_fields)}")
        if audit_result.flagged_issues:
            issues_summary.append(f"Flagged issues: {', '.join(audit_result.flagged_issues)}")
        if audit_result.schema_errors:
            issues_summary.append(f"Schema errors: {', '.join(audit_result.schema_errors)}")
        if audit_result.metadata_issues:
            issues_summary.append(f"Metadata issues: {', '.join(audit_result.metadata_issues)}")
            
        return f"""Fix the following issues in this HTML product page:

Product Details:
- Handle: {product_data.handle}
- Title: {product_data.title}
- Description: {product_data.description or 'Not provided'}
- Price: ${product_data.price or 'Not provided'}
- Brand: {product_data.brand or 'Not provided'}

Issues to Fix:
{chr(10).join(issues_summary)}

Current HTML:
{current_html}

Requirements:
1. Fix ONLY the identified issues
2. Keep existing structure and content where possible
3. Ensure title is 30-60 characters
4. Ensure meta description is 120-160 characters
5. Complete any missing JSON-LD schema fields
6. Fix any malformed HTML or metadata

Generate the corrected HTML content, no explanations:"""

    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API for text generation"""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json()["response"]
            
        except requests.RequestException as e:
            return f"<html><head><title>Error</title></head><body><h1>Generation Error</h1><p>{str(e)}</p></body></html>"
    
    def _extract_metadata(self, html_content: str) -> Dict[str, Any]:
        """Extract metadata from HTML content"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        metadata = {}
        
        # Extract title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.text.strip()
            
        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            metadata['meta_description'] = meta_desc.get('content', '')
            
        # Extract Open Graph tags
        for og_tag in soup.find_all('meta', attrs={'property': lambda x: x and x.startswith('og:')}):
            prop = og_tag.get('property')
            content = og_tag.get('content')
            if prop and content:
                metadata[prop] = content
                
        return metadata
    
    def _extract_schema(self, html_content: str) -> Dict[str, Any]:
        """Extract JSON-LD schema from HTML content"""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        schema_script = soup.find('script', attrs={'type': 'application/ld+json'})
        
        if schema_script and schema_script.string:
            try:
                return json.loads(schema_script.string)
            except json.JSONDecodeError:
                return {}
                
        return {}