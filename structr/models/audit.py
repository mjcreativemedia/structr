import json
import re
from typing import Dict, List, Any
from bs4 import BeautifulSoup
from models.pdp import AuditResult, PDPBundle

class PDPAuditor:
    """Audits PDPs for SEO and structure compliance"""
    
    REQUIRED_META_FIELDS = [
        'title',
        'meta_description', 
        'og:title',
        'og:description',
        'og:image'
    ]
    
    REQUIRED_SCHEMA_FIELDS = [
        '@type',
        'name', 
        'description',
        'image',
        'offers',
        'brand'
    ]
    
    def audit_pdp_bundle(self, bundle_path: str, product_id: str) -> AuditResult:
        """Audit a complete PDP bundle"""
        try:
            # Load audit.json if exists
            audit_file = f"{bundle_path}/audit.json"
            sync_file = f"{bundle_path}/sync.json"
            html_file = f"{bundle_path}/index.html"
            
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
                
            audit_result = self._analyze_html(html_content, product_id)
            return audit_result
            
        except Exception as e:
            return AuditResult(
                product_id=product_id,
                score=0.0,
                flagged_issues=[f"Failed to audit: {str(e)}"]
            )
    
    def _analyze_html(self, html_content: str, product_id: str) -> AuditResult:
        """Analyze HTML content for SEO compliance"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        missing_fields = []
        flagged_issues = []
        schema_errors = []
        metadata_issues = []
        
        # Check title
        title_tag = soup.find('title')
        if not title_tag or not title_tag.text.strip():
            missing_fields.append('title')
            metadata_issues.append('Missing or empty title tag')
        elif len(title_tag.text.strip()) < 30:
            flagged_issues.append('Title too short (< 30 chars)')
        elif len(title_tag.text.strip()) > 60:
            flagged_issues.append('Title too long (> 60 chars)')
            
        # Check meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if not meta_desc or not meta_desc.get('content', '').strip():
            missing_fields.append('meta_description')
            metadata_issues.append('Missing meta description')
        elif len(meta_desc.get('content', '')) < 120:
            flagged_issues.append('Meta description too short (< 120 chars)')
        elif len(meta_desc.get('content', '')) > 160:
            flagged_issues.append('Meta description too long (> 160 chars)')
            
        # Check Open Graph tags
        og_title = soup.find('meta', attrs={'property': 'og:title'})
        if not og_title or not og_title.get('content', '').strip():
            missing_fields.append('og:title')
            metadata_issues.append('Missing og:title')
            
        og_desc = soup.find('meta', attrs={'property': 'og:description'})
        if not og_desc or not og_desc.get('content', '').strip():
            missing_fields.append('og:description')
            metadata_issues.append('Missing og:description')
            
        og_image = soup.find('meta', attrs={'property': 'og:image'})
        if not og_image or not og_image.get('content', '').strip():
            missing_fields.append('og:image')
            metadata_issues.append('Missing og:image')
            
        # Check JSON-LD schema
        schema_script = soup.find('script', attrs={'type': 'application/ld+json'})
        if not schema_script:
            missing_fields.append('json_ld_schema')
            schema_errors.append('Missing JSON-LD schema markup')
        else:
            try:
                schema_data = json.loads(schema_script.string)
                schema_errors.extend(self._validate_product_schema(schema_data))
            except json.JSONDecodeError:
                schema_errors.append('Invalid JSON-LD schema format')
                
        # Calculate score
        total_checks = len(self.REQUIRED_META_FIELDS) + len(self.REQUIRED_SCHEMA_FIELDS)
        issues_count = len(missing_fields) + len(flagged_issues) + len(schema_errors)
        score = max(0, 100 - (issues_count / total_checks * 100))
        
        return AuditResult(
            product_id=product_id,
            score=round(score, 2),
            missing_fields=missing_fields,
            flagged_issues=flagged_issues,
            schema_errors=schema_errors,
            metadata_issues=metadata_issues
        )
    
    def _validate_product_schema(self, schema_data: Dict) -> List[str]:
        """Validate Product schema against Google requirements"""
        errors = []
        
        if schema_data.get('@type') != 'Product':
            errors.append('Schema @type must be "Product"')
            
        for field in self.REQUIRED_SCHEMA_FIELDS:
            if field not in schema_data:
                errors.append(f'Missing required schema field: {field}')
                
        # Check offers structure
        offers = schema_data.get('offers')
        if offers:
            if isinstance(offers, dict):
                if offers.get('@type') != 'Offer':
                    errors.append('Offers @type must be "Offer"')
                if not offers.get('price'):
                    errors.append('Offer missing price')
                if not offers.get('priceCurrency'):
                    errors.append('Offer missing priceCurrency')
                    
        return errors