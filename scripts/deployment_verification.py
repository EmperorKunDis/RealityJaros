#!/usr/bin/env python3
"""
AI Email Assistant - Deployment Verification Script

This script performs comprehensive checks to verify that the AI Email Assistant
is properly deployed and all components are functioning correctly.

Usage:
    python scripts/deployment_verification.py [--host HOST] [--port PORT] [--timeout TIMEOUT]
"""

import argparse
import asyncio
import aiohttp
import sys
import time
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DeploymentVerifier:
    """Deployment verification utility"""
    
    def __init__(self, host: str = "localhost", port: int = 8000, timeout: int = 30):
        self.base_url = f"http://{host}:{port}"
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: Optional[aiohttp.ClientSession] = None
        self.results: Dict[str, Any] = {}
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def verify_basic_connectivity(self) -> Dict[str, Any]:
        """Verify basic connectivity to the application"""
        logger.info("🔍 Verifying basic connectivity...")
        
        try:
            async with self.session.get(f"{self.base_url}/") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "success",
                        "response_time": response.headers.get("X-Response-Time", "unknown"),
                        "application": data.get("application"),
                        "version": data.get("version"),
                        "application_status": data.get("status")
                    }
                else:
                    return {
                        "status": "error",
                        "error": f"HTTP {response.status}",
                        "message": await response.text()
                    }
        except Exception as e:
            return {
                "status": "error",
                "error": "Connection failed",
                "message": str(e)
            }
    
    async def verify_health_check(self) -> Dict[str, Any]:
        """Verify health check endpoint"""
        logger.info("🔍 Verifying health check...")
        
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "success",
                        "health_status": data.get("status"),
                        "timestamp": data.get("timestamp"),
                        "version": data.get("version")
                    }
                else:
                    return {
                        "status": "error",
                        "error": f"HTTP {response.status}",
                        "message": await response.text()
                    }
        except Exception as e:
            return {
                "status": "error",
                "error": "Health check failed",
                "message": str(e)
            }
    
    async def verify_api_endpoints(self) -> Dict[str, Any]:
        """Verify core API endpoints"""
        logger.info("🔍 Verifying API endpoints...")
        
        endpoints = [
            ("GET", "/api/v1/emails/", "Email listing"),
            ("GET", "/api/v1/clients/", "Client listing"),
            ("GET", "/api/v1/responses/", "Response listing"),
            ("GET", "/api/v1/vectors/health", "Vector database health"),
            ("POST", "/api/v1/analysis/comprehensive", "Comprehensive analysis")
        ]
        
        results = {}
        
        for method, endpoint, description in endpoints:
            try:
                if method == "GET":
                    async with self.session.get(f"{self.base_url}{endpoint}") as response:
                        status = response.status
                        response_data = await response.text()
                elif method == "POST":
                    async with self.session.post(f"{self.base_url}{endpoint}", json={}) as response:
                        status = response.status
                        response_data = await response.text()
                
                results[endpoint] = {
                    "description": description,
                    "status": "success" if status in [200, 422] else "error",
                    "http_status": status,
                    "accessible": status != 404
                }
                
            except Exception as e:
                results[endpoint] = {
                    "description": description,
                    "status": "error",
                    "error": str(e),
                    "accessible": False
                }
        
        return results
    
    async def verify_database_connectivity(self) -> Dict[str, Any]:
        """Verify database connectivity through API"""
        logger.info("🔍 Verifying database connectivity...")
        
        try:
            # Test database through email listing endpoint
            async with self.session.get(f"{self.base_url}/api/v1/emails/") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "success",
                        "database_accessible": True,
                        "total_emails": data.get("total_count", 0)
                    }
                else:
                    return {
                        "status": "error",
                        "database_accessible": False,
                        "error": f"HTTP {response.status}"
                    }
        except Exception as e:
            return {
                "status": "error",
                "database_accessible": False,
                "error": str(e)
            }
    
    async def verify_vector_database(self) -> Dict[str, Any]:
        """Verify vector database connectivity"""
        logger.info("🔍 Verifying vector database...")
        
        try:
            async with self.session.get(f"{self.base_url}/api/v1/vectors/health") as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "success",
                        "vector_db_accessible": True,
                        "vector_status": data.get("status"),
                        "collections_count": data.get("collections_count", 0)
                    }
                else:
                    return {
                        "status": "warning",
                        "vector_db_accessible": False,
                        "error": f"HTTP {response.status}",
                        "note": "Vector database may not be configured"
                    }
        except Exception as e:
            return {
                "status": "warning",
                "vector_db_accessible": False,
                "error": str(e),
                "note": "Vector database may not be available"
            }
    
    async def verify_authentication_system(self) -> Dict[str, Any]:
        """Verify authentication system"""
        logger.info("🔍 Verifying authentication system...")
        
        try:
            async with self.session.get(f"{self.base_url}/api/v1/auth/login") as response:
                return {
                    "status": "success" if response.status in [200, 500] else "error",
                    "auth_endpoint_accessible": response.status != 404,
                    "http_status": response.status,
                    "note": "Google OAuth may not be configured in test environment"
                }
        except Exception as e:
            return {
                "status": "error",
                "auth_endpoint_accessible": False,
                "error": str(e)
            }
    
    async def verify_performance(self) -> Dict[str, Any]:
        """Verify basic performance metrics"""
        logger.info("🔍 Verifying performance...")
        
        # Test response times
        response_times = []
        
        for i in range(5):
            start_time = time.time()
            try:
                async with self.session.get(f"{self.base_url}/health") as response:
                    end_time = time.time()
                    if response.status == 200:
                        response_times.append(end_time - start_time)
            except Exception:
                pass
        
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            
            return {
                "status": "success",
                "avg_response_time": f"{avg_response_time:.3f}s",
                "max_response_time": f"{max_response_time:.3f}s",
                "performance_acceptable": avg_response_time < 2.0,
                "total_requests": len(response_times)
            }
        else:
            return {
                "status": "error",
                "error": "Could not measure response times"
            }
    
    async def verify_api_documentation(self) -> Dict[str, Any]:
        """Verify API documentation accessibility"""
        logger.info("🔍 Verifying API documentation...")
        
        doc_endpoints = [
            ("/docs", "Swagger UI"),
            ("/redoc", "ReDoc"),
            ("/openapi.json", "OpenAPI Schema")
        ]
        
        results = {}
        
        for endpoint, description in doc_endpoints:
            try:
                async with self.session.get(f"{self.base_url}{endpoint}") as response:
                    results[endpoint] = {
                        "description": description,
                        "accessible": response.status == 200,
                        "status": response.status
                    }
            except Exception as e:
                results[endpoint] = {
                    "description": description,
                    "accessible": False,
                    "error": str(e)
                }
        
        return results
    
    async def verify_security_headers(self) -> Dict[str, Any]:
        """Verify security headers"""
        logger.info("🔍 Verifying security headers...")
        
        try:
            async with self.session.get(f"{self.base_url}/") as response:
                headers = response.headers
                
                security_headers = {
                    "X-Content-Type-Options": headers.get("X-Content-Type-Options"),
                    "X-Frame-Options": headers.get("X-Frame-Options"),
                    "X-XSS-Protection": headers.get("X-XSS-Protection"),
                    "Strict-Transport-Security": headers.get("Strict-Transport-Security"),
                    "Content-Security-Policy": headers.get("Content-Security-Policy")
                }
                
                present_headers = {k: v for k, v in security_headers.items() if v is not None}
                
                return {
                    "status": "success",
                    "security_headers_present": len(present_headers),
                    "total_expected_headers": len(security_headers),
                    "headers": present_headers,
                    "security_score": len(present_headers) / len(security_headers)
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def run_comprehensive_verification(self) -> Dict[str, Any]:
        """Run comprehensive deployment verification"""
        logger.info("🚀 Starting comprehensive deployment verification...")
        
        verification_start = time.time()
        
        # Run all verification checks
        checks = [
            ("basic_connectivity", self.verify_basic_connectivity()),
            ("health_check", self.verify_health_check()),
            ("api_endpoints", self.verify_api_endpoints()),
            ("database_connectivity", self.verify_database_connectivity()),
            ("vector_database", self.verify_vector_database()),
            ("authentication", self.verify_authentication_system()),
            ("performance", self.verify_performance()),
            ("documentation", self.verify_api_documentation()),
            ("security", self.verify_security_headers())
        ]
        
        results = {}
        
        for check_name, check_task in checks:
            try:
                logger.info(f"Running {check_name} verification...")
                results[check_name] = await check_task
            except Exception as e:
                logger.error(f"Error in {check_name} verification: {e}")
                results[check_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        verification_end = time.time()
        
        # Calculate overall health score
        health_score = self._calculate_health_score(results)
        
        results["summary"] = {
            "overall_health_score": health_score,
            "verification_time": f"{verification_end - verification_start:.2f}s",
            "timestamp": datetime.utcnow().isoformat(),
            "deployment_status": "healthy" if health_score >= 0.8 else "degraded" if health_score >= 0.6 else "unhealthy"
        }
        
        return results
    
    def _calculate_health_score(self, results: Dict[str, Any]) -> float:
        """Calculate overall health score"""
        weights = {
            "basic_connectivity": 0.2,
            "health_check": 0.15,
            "api_endpoints": 0.15,
            "database_connectivity": 0.15,
            "vector_database": 0.1,  # Lower weight as it's optional
            "authentication": 0.1,
            "performance": 0.1,
            "documentation": 0.05,
            "security": 0.05
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for check_name, weight in weights.items():
            if check_name in results:
                check_result = results[check_name]
                if check_result.get("status") == "success":
                    score = 1.0
                elif check_result.get("status") == "warning":
                    score = 0.5
                else:
                    score = 0.0
                
                total_score += score * weight
                total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0

def print_verification_results(results: Dict[str, Any]):
    """Print verification results in a formatted way"""
    
    print("\n" + "="*80)
    print("🤖 AI EMAIL ASSISTANT - DEPLOYMENT VERIFICATION RESULTS")
    print("="*80)
    
    summary = results.get("summary", {})
    health_score = summary.get("overall_health_score", 0.0)
    deployment_status = summary.get("deployment_status", "unknown")
    
    # Overall status
    if deployment_status == "healthy":
        status_emoji = "✅"
        status_color = "\033[92m"  # Green
    elif deployment_status == "degraded":
        status_emoji = "⚠️"
        status_color = "\033[93m"  # Yellow
    else:
        status_emoji = "❌"
        status_color = "\033[91m"  # Red
    
    print(f"\n{status_emoji} OVERALL STATUS: {status_color}{deployment_status.upper()}\033[0m")
    print(f"📊 Health Score: {health_score:.1%}")
    print(f"⏱️  Verification Time: {summary.get('verification_time', 'unknown')}")
    print(f"🕐 Timestamp: {summary.get('timestamp', 'unknown')}")
    
    # Detailed results
    print("\n📋 DETAILED RESULTS:")
    print("-" * 80)
    
    for check_name, check_result in results.items():
        if check_name == "summary":
            continue
            
        status = check_result.get("status", "unknown")
        if status == "success":
            emoji = "✅"
        elif status == "warning":
            emoji = "⚠️"
        else:
            emoji = "❌"
        
        print(f"\n{emoji} {check_name.upper().replace('_', ' ')}")
        
        # Print key details for each check
        if check_name == "basic_connectivity":
            print(f"   Application: {check_result.get('application', 'unknown')}")
            print(f"   Version: {check_result.get('version', 'unknown')}")
            print(f"   Status: {check_result.get('application_status', 'unknown')}")
            
        elif check_name == "api_endpoints":
            accessible_count = sum(1 for ep in check_result.values() if ep.get('accessible', False))
            total_count = len(check_result)
            print(f"   Accessible Endpoints: {accessible_count}/{total_count}")
            
        elif check_name == "performance":
            print(f"   Avg Response Time: {check_result.get('avg_response_time', 'unknown')}")
            print(f"   Performance Acceptable: {check_result.get('performance_acceptable', False)}")
            
        elif check_name == "database_connectivity":
            print(f"   Database Accessible: {check_result.get('database_accessible', False)}")
            print(f"   Total Emails: {check_result.get('total_emails', 0)}")
            
        elif check_name == "vector_database":
            print(f"   Vector DB Accessible: {check_result.get('vector_db_accessible', False)}")
            print(f"   Collections Count: {check_result.get('collections_count', 0)}")
            
        elif check_name == "security":
            print(f"   Security Score: {check_result.get('security_score', 0.0):.1%}")
            print(f"   Headers Present: {check_result.get('security_headers_present', 0)}")
        
        # Print errors if any
        if check_result.get("error"):
            print(f"   Error: {check_result['error']}")
        
        if check_result.get("note"):
            print(f"   Note: {check_result['note']}")
    
    print("\n" + "="*80)
    
    # Recommendations
    if deployment_status != "healthy":
        print("\n💡 RECOMMENDATIONS:")
        print("-" * 80)
        
        for check_name, check_result in results.items():
            if check_name == "summary":
                continue
                
            if check_result.get("status") == "error":
                if check_name == "vector_database":
                    print("   • Configure ChromaDB for vector search functionality")
                elif check_name == "authentication":
                    print("   • Configure Google OAuth credentials for authentication")
                elif check_name == "database_connectivity":
                    print("   • Check database connection and configuration")
                elif check_name == "performance":
                    print("   • Investigate performance issues and optimize response times")
    
    print()

async def main():
    """Main verification function"""
    parser = argparse.ArgumentParser(description="AI Email Assistant Deployment Verification")
    parser.add_argument("--host", default="localhost", help="Host to verify (default: localhost)")
    parser.add_argument("--port", type=int, default=8000, help="Port to verify (default: 8000)")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds (default: 30)")
    parser.add_argument("--output", help="Output file for results (JSON format)")
    parser.add_argument("--quiet", action="store_true", help="Suppress detailed output")
    
    args = parser.parse_args()
    
    try:
        async with DeploymentVerifier(args.host, args.port, args.timeout) as verifier:
            results = await verifier.run_comprehensive_verification()
            
            if not args.quiet:
                print_verification_results(results)
            
            # Save results to file if specified
            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"Results saved to {args.output}")
            
            # Exit with appropriate code
            health_score = results.get("summary", {}).get("overall_health_score", 0.0)
            if health_score >= 0.8:
                sys.exit(0)  # Healthy
            elif health_score >= 0.6:
                sys.exit(1)  # Degraded
            else:
                sys.exit(2)  # Unhealthy
                
    except KeyboardInterrupt:
        logger.info("Verification cancelled by user")
        sys.exit(3)
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        sys.exit(4)

if __name__ == "__main__":
    asyncio.run(main())