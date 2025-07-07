#!/usr/bin/env python3
"""
fix_broken_pdp.py - Self-healing module for flagged PDPs

This module reads audit.json files, identifies issues, and regenerates
only the problematic content using LLM prompts.
"""

import os
import json
import time
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any

# Import centralized configuration
from config import StructrConfig as CONFIG

from models.pdp import ProductData, AuditResult, FixRequest
from models.audit import PDPAuditor
from llm_service.generator import OllamaLLMService


class PDPFixer:
    """Handles fixing broken PDPs based on audit results"""
    
    def __init__(self, output_dir: str = None, llm_service: Optional[OllamaLLMService] = None):
        self.output_dir = Path(output_dir) if output_dir else CONFIG.get_output_dir()
        self.auditor = PDPAuditor()
        self.llm_service = llm_service or OllamaLLMService()
    
    def fix_product(self, product_id: str, target_issues: Optional[List[str]] = None, 
                   dry_run: bool = False) -> Dict[str, Any]:
        """Fix a specific product by regenerating flagged content"""
        
        bundle_path = CONFIG.get_bundle_path(product_id)
        
        if not bundle_path.exists():
            return {
                "success": False,
                "error": f"Bundle not found for product {product_id}",
                "path": str(bundle_path)
            }
        
        # Load existing files
        try:
            audit_result = self._load_audit_result(bundle_path)
            product_data = self._load_product_data(bundle_path)
            current_html = self._load_current_html(bundle_path)
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to load bundle files: {str(e)}",
                "product_id": product_id
            }
        
        # Determine which issues to fix
        if target_issues:
            # Filter audit result to only include specified issues
            filtered_audit = self._filter_audit_issues(audit_result, target_issues)
        else:
            filtered_audit = audit_result
        
        if not self._has_fixable_issues(filtered_audit):
            return {
                "success": True,
                "message": f"No fixable issues found for {product_id}",
                "product_id": product_id,
                "issues_checked": target_issues or "all"
            }
        
        # Generate fix
        start_time = time.time()
        
        try:
            fixed_html = self.llm_service.fix_pdp_issues(
                product_data=product_data,
                audit_result=filtered_audit,
                current_html=current_html
            )
            
            fix_time = time.time() - start_time
            
            if dry_run:
                return {
                    "success": True,
                    "dry_run": True,
                    "product_id": product_id,
                    "issues_to_fix": self._get_issue_summary(filtered_audit),
                    "fix_time": fix_time,
                    "preview": fixed_html[:500] + "..." if len(fixed_html) > 500 else fixed_html
                }
            
            # Save fixed HTML
            self._save_fixed_html(bundle_path, fixed_html)
            
            # Re-audit to verify fixes
            new_audit = self.auditor.audit_pdp_bundle(str(bundle_path), product_id)
            self._save_audit_result(bundle_path, new_audit)
            
            # Create fix log
            fix_log = {
                "timestamp": time.time(),
                "product_id": product_id,
                "issues_fixed": self._get_issue_summary(filtered_audit),
                "original_score": audit_result.score,
                "new_score": new_audit.score,
                "fix_time": fix_time,
                "model_used": self.llm_service.model
            }
            
            self._save_fix_log(bundle_path, fix_log)
            
            return {
                "success": True,
                "product_id": product_id,
                "original_score": audit_result.score,
                "new_score": new_audit.score,
                "improvement": new_audit.score - audit_result.score,
                "issues_fixed": self._get_issue_summary(filtered_audit),
                "fix_time": fix_time,
                "bundle_path": str(bundle_path)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to fix PDP: {str(e)}",
                "product_id": product_id,
                "fix_time": time.time() - start_time
            }
    
    def fix_all_flagged(self, min_score: float = 80.0, dry_run: bool = False) -> List[Dict[str, Any]]:
        """Fix all products with audit scores below threshold"""
        
        results = []
        bundles_dir = self.output_dir / "bundles"
        
        if not bundles_dir.exists():
            return [{"error": "No bundles directory found"}]
        
        for product_dir in bundles_dir.iterdir():
            if product_dir.is_dir():
                audit_file = product_dir / "audit.json"
                if audit_file.exists():
                    try:
                        with open(audit_file, 'r') as f:
                            audit_data = json.load(f)
                            
                        if audit_data.get('score', 100) < min_score:
                            print(f"Fixing {product_dir.name} (score: {audit_data.get('score')})")
                            result = self.fix_product(product_dir.name, dry_run=dry_run)
                            results.append(result)
                            
                    except Exception as e:
                        results.append({
                            "success": False,
                            "product_id": product_dir.name,
                            "error": f"Failed to process: {str(e)}"
                        })
        
        return results
    
    def _load_audit_result(self, bundle_path: Path) -> AuditResult:
        """Load audit.json and convert to AuditResult object"""
        audit_file = bundle_path / "audit.json"
        
        with open(audit_file, 'r') as f:
            audit_data = json.load(f)
            
        return AuditResult(**audit_data)
    
    def _load_product_data(self, bundle_path: Path) -> ProductData:
        """Load product data from sync.json"""
        sync_file = bundle_path / "sync.json"
        
        with open(sync_file, 'r') as f:
            sync_data = json.load(f)
            
        # Extract product data from sync data
        product_input = sync_data.get('input', {})
        
        return ProductData(
            handle=product_input.get('handle', 'unknown'),
            title=product_input.get('title', 'Unknown Product'),
            description=product_input.get('description'),
            price=product_input.get('price'),
            brand=product_input.get('brand'),
            category=product_input.get('category'),
            images=product_input.get('images', []),
            features=product_input.get('features', []),
            metafields=product_input.get('metafields', {})
        )
    
    def _load_current_html(self, bundle_path: Path) -> str:
        """Load current HTML content"""
        html_file = bundle_path / "index.html"
        
        with open(html_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _filter_audit_issues(self, audit_result: AuditResult, target_issues: List[str]) -> AuditResult:
        """Filter audit result to only include specified issues"""
        
        filtered_missing = [f for f in audit_result.missing_fields if f in target_issues]
        filtered_flagged = [f for f in audit_result.flagged_issues if any(issue in f for issue in target_issues)]
        filtered_schema = [f for f in audit_result.schema_errors if any(issue in f for issue in target_issues)]
        filtered_metadata = [f for f in audit_result.metadata_issues if any(issue in f for issue in target_issues)]
        
        return AuditResult(
            product_id=audit_result.product_id,
            score=audit_result.score,
            missing_fields=filtered_missing,
            flagged_issues=filtered_flagged,
            schema_errors=filtered_schema,
            metadata_issues=filtered_metadata,
            timestamp=audit_result.timestamp
        )
    
    def _has_fixable_issues(self, audit_result: AuditResult) -> bool:
        """Check if audit result has any fixable issues"""
        return bool(
            audit_result.missing_fields or 
            audit_result.flagged_issues or 
            audit_result.schema_errors or 
            audit_result.metadata_issues
        )
    
    def _get_issue_summary(self, audit_result: AuditResult) -> Dict[str, List[str]]:
        """Get summary of issues from audit result"""
        return {
            "missing_fields": audit_result.missing_fields,
            "flagged_issues": audit_result.flagged_issues,
            "schema_errors": audit_result.schema_errors,
            "metadata_issues": audit_result.metadata_issues
        }
    
    def _save_fixed_html(self, bundle_path: Path, html_content: str):
        """Save fixed HTML content"""
        html_file = bundle_path / "index.html"
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _save_audit_result(self, bundle_path: Path, audit_result: AuditResult):
        """Save updated audit result"""
        audit_file = bundle_path / "audit.json"
        
        with open(audit_file, 'w') as f:
            json.dump(audit_result.model_dump(), f, indent=2, default=str)
    
    def _save_fix_log(self, bundle_path: Path, fix_log: Dict[str, Any]):
        """Save fix log for tracking"""
        log_file = bundle_path / "fix_log.json"
        
        # Load existing logs or create new list
        logs = []
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    logs = json.load(f)
            except:
                logs = []
        
        logs.append(fix_log)
        
        with open(log_file, 'w') as f:
            json.dump(logs, f, indent=2, default=str)


def main():
    """CLI interface for fixing broken PDPs"""
    parser = argparse.ArgumentParser(description="Fix broken PDPs based on audit results")
    
    parser.add_argument("--product-id", "--only", type=str, 
                       help="Fix specific product by ID")
    parser.add_argument("--all", action="store_true",
                       help="Fix all products with low scores")
    parser.add_argument("--min-score", type=float, default=80.0,
                       help="Minimum score threshold for --all (default: 80.0)")
    parser.add_argument("--issues", nargs="+", 
                       help="Target specific issues to fix")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be fixed without making changes")
    parser.add_argument("--output-dir", type=str, default="output",
                       help="Output directory (default: output)")
    parser.add_argument("--model", type=str, default="mistral",
                       help="LLM model to use (default: mistral)")
    
    args = parser.parse_args()
    
    if not args.product_id and not args.all:
        parser.error("Must specify either --product-id or --all")
    
    # Initialize fixer
    llm_service = OllamaLLMService(model=args.model)
    fixer = PDPFixer(output_dir=args.output_dir, llm_service=llm_service)
    
    if args.product_id:
        # Fix specific product
        print(f"Fixing product: {args.product_id}")
        if args.dry_run:
            print("DRY RUN - No changes will be made")
        
        result = fixer.fix_product(
            product_id=args.product_id,
            target_issues=args.issues,
            dry_run=args.dry_run
        )
        
        print(json.dumps(result, indent=2, default=str))
        
    elif args.all:
        # Fix all flagged products
        print(f"Fixing all products with score < {args.min_score}")
        if args.dry_run:
            print("DRY RUN - No changes will be made")
        
        results = fixer.fix_all_flagged(min_score=args.min_score, dry_run=args.dry_run)
        
        print(f"Processed {len(results)} products:")
        for result in results:
            if result.get('success'):
                improvement = result.get('improvement', 0)
                print(f"✅ {result.get('product_id')}: {result.get('original_score'):.1f} → {result.get('new_score'):.1f} (+{improvement:.1f})")
            else:
                print(f"❌ {result.get('product_id', 'unknown')}: {result.get('error')}")


if __name__ == "__main__":
    main()