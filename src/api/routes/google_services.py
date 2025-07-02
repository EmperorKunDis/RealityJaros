"""
Google Services Integration API Routes

Provides REST API endpoints for Google Workspace integration:
- Google Sheets automation
- Google Docs template management
- Google Drive file operations
- Workflow automation
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from datetime import datetime

from src.api.dependencies import get_current_user, get_database_session
from src.services.google_services_integration import google_services
from src.models.user import User
from src.models.google_services import GoogleServiceType, WorkflowTrigger

router = APIRouter()


# Pydantic schemas for request/response validation

class GoogleCredentialsSetup(BaseModel):
    service_type: str = Field(..., description="Type of Google service")
    access_token: str = Field(..., description="OAuth access token")
    refresh_token: str = Field(..., description="OAuth refresh token") 
    scopes: List[str] = Field(..., description="Authorized scopes")
    expires_at: Optional[datetime] = Field(None, description="Token expiration time")


class SheetIntegrationCreate(BaseModel):
    spreadsheet_id: str = Field(..., description="Google Sheets spreadsheet ID")
    spreadsheet_name: str = Field(..., description="Spreadsheet display name")
    sheet_name: str = Field(..., description="Sheet tab name")
    integration_type: str = Field(..., description="Type of integration: email_log, client_tracker, response_metrics")
    column_mapping: Dict[str, str] = Field(default={}, description="Mapping of data fields to sheet columns")
    auto_sync: bool = Field(default=True, description="Enable automatic synchronization")


class DocsTemplateCreate(BaseModel):
    template_name: str = Field(..., description="Template display name")
    template_type: str = Field(..., description="Template type: email_summary, client_report, meeting_notes")
    template_content: str = Field(..., description="Template content with placeholders")
    placeholder_mapping: Dict[str, str] = Field(default={}, description="Mapping of placeholders to data fields")
    auto_generate: bool = Field(default=False, description="Enable automatic document generation")


class DocumentGenerate(BaseModel):
    template_id: str = Field(..., description="Template ID to use")
    document_title: str = Field(..., description="Title for generated document")
    generation_data: Dict[str, Any] = Field(default={}, description="Data to populate template")


class WorkflowCreate(BaseModel):
    workflow_name: str = Field(..., description="Workflow display name")
    description: str = Field(default="", description="Workflow description")
    trigger_type: str = Field(..., description="Workflow trigger type")
    trigger_conditions: Dict[str, Any] = Field(default={}, description="Trigger conditions")
    workflow_steps: List[Dict[str, Any]] = Field(..., description="Workflow steps to execute")


class WorkflowExecute(BaseModel):
    trigger_data: Dict[str, Any] = Field(default={}, description="Data that triggered the workflow")


# Google Credentials Management

@router.post("/credentials/setup", summary="Setup Google service credentials")
async def setup_google_credentials(
    credentials: GoogleCredentialsSetup,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Setup Google Workspace service credentials for the user
    """
    try:
        credentials_id = await google_services.setup_user_credentials(
            user_id=str(current_user.id),
            service_type=credentials.service_type,
            access_token=credentials.access_token,
            refresh_token=credentials.refresh_token,
            scopes=credentials.scopes,
            expires_at=credentials.expires_at
        )
        
        return {
            "success": True,
            "credentials_id": credentials_id,
            "service_type": credentials.service_type,
            "message": f"Google {credentials.service_type} credentials configured",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to setup Google credentials: {str(e)}"
        )


@router.get("/credentials/status", summary="Get Google services status")
async def get_credentials_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get status of Google Workspace service integrations
    """
    try:
        # Check each service type
        services_status = {}
        
        for service_type in [GoogleServiceType.SHEETS, GoogleServiceType.DOCS, 
                           GoogleServiceType.DRIVE, GoogleServiceType.GMAIL]:
            creds = await google_services.get_user_credentials(
                str(current_user.id), 
                service_type.value
            )
            services_status[service_type.value] = {
                "enabled": creds is not None,
                "status": "active" if creds else "not_configured"
            }
        
        return {
            "success": True,
            "user_id": str(current_user.id),
            "services": services_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get credentials status: {str(e)}"
        )


# Google Sheets Integration

@router.post("/sheets/integrations", summary="Create Google Sheets integration")
async def create_sheet_integration(
    integration: SheetIntegrationCreate,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Create a new Google Sheets integration for automated data sync
    """
    try:
        integration_id = await google_services.create_sheet_integration(
            user_id=str(current_user.id),
            spreadsheet_id=integration.spreadsheet_id,
            spreadsheet_name=integration.spreadsheet_name,
            sheet_name=integration.sheet_name,
            integration_type=integration.integration_type,
            column_mapping=integration.column_mapping,
            auto_sync=integration.auto_sync
        )
        
        return {
            "success": True,
            "integration_id": integration_id,
            "spreadsheet_id": integration.spreadsheet_id,
            "message": "Google Sheets integration created",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create sheet integration: {str(e)}"
        )


@router.post("/sheets/{integration_id}/sync", summary="Sync data to Google Sheets")
async def sync_to_sheets(
    integration_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Manually trigger synchronization of email data to Google Sheets
    """
    try:
        # Execute sync in background
        background_tasks.add_task(
            google_services.sync_emails_to_sheet,
            str(current_user.id),
            integration_id
        )
        
        return {
            "success": True,
            "integration_id": integration_id,
            "message": "Sheet synchronization initiated",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync to sheets: {str(e)}"
        )


# Google Docs Integration

@router.post("/docs/templates", summary="Create Google Docs template")
async def create_docs_template(
    template: DocsTemplateCreate,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Create a new Google Docs template for automated document generation
    """
    try:
        template_id = await google_services.create_docs_template(
            user_id=str(current_user.id),
            template_name=template.template_name,
            template_type=template.template_type,
            template_content=template.template_content,
            placeholder_mapping=template.placeholder_mapping,
            auto_generate=template.auto_generate
        )
        
        return {
            "success": True,
            "template_id": template_id,
            "template_name": template.template_name,
            "message": "Google Docs template created",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create docs template: {str(e)}"
        )


@router.post("/docs/generate", summary="Generate document from template")
async def generate_document(
    generate_request: DocumentGenerate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Generate a Google Docs document from a template
    """
    try:
        result = await google_services.generate_document_from_template(
            user_id=str(current_user.id),
            template_id=generate_request.template_id,
            generation_data=generate_request.generation_data,
            document_title=generate_request.document_title
        )
        
        return {
            "success": True,
            "document_id": result["document_id"],
            "document_url": result["document_url"],
            "document_title": result["document_title"],
            "message": "Document generated successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate document: {str(e)}"
        )


# Workflow Automation

@router.post("/workflows", summary="Create automated workflow")
async def create_workflow(
    workflow: WorkflowCreate,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Create an automated workflow using Google Services
    """
    try:
        workflow_id = await google_services.create_workflow(
            user_id=str(current_user.id),
            workflow_name=workflow.workflow_name,
            description=workflow.description,
            trigger_type=workflow.trigger_type,
            trigger_conditions=workflow.trigger_conditions,
            workflow_steps=workflow.workflow_steps
        )
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "workflow_name": workflow.workflow_name,
            "message": "Workflow created successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create workflow: {str(e)}"
        )


@router.post("/workflows/{workflow_id}/execute", summary="Execute workflow")
async def execute_workflow(
    workflow_id: str,
    execute_request: WorkflowExecute,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Manually execute a workflow
    """
    try:
        # Execute workflow in background
        background_tasks.add_task(
            google_services.execute_workflow,
            workflow_id,
            execute_request.trigger_data
        )
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "message": "Workflow execution initiated",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute workflow: {str(e)}"
        )


# Pre-built Workflow Templates

@router.get("/workflows/templates", summary="Get workflow templates")
async def get_workflow_templates() -> Dict[str, Any]:
    """
    Get pre-built workflow templates for common use cases
    """
    templates = {
        "email_to_sheets": {
            "name": "Email Data to Sheets",
            "description": "Automatically sync new emails to Google Sheets",
            "trigger_type": WorkflowTrigger.NEW_EMAIL,
            "steps": [
                {
                    "type": "sheets_update",
                    "name": "Update Email Log",
                    "integration_id": "{{SHEETS_INTEGRATION_ID}}"
                }
            ]
        },
        "weekly_email_report": {
            "name": "Weekly Email Report",
            "description": "Generate weekly email summary document",
            "trigger_type": WorkflowTrigger.WEEKLY_REPORT,
            "steps": [
                {
                    "type": "docs_create",
                    "name": "Generate Report",
                    "template_id": "{{DOCS_TEMPLATE_ID}}",
                    "document_title": "Weekly Email Report - {{date}}"
                }
            ]
        },
        "client_response_tracking": {
            "name": "Client Response Tracking",
            "description": "Track AI responses in sheets and create summary docs",
            "trigger_type": WorkflowTrigger.EMAIL_RESPONSE,
            "steps": [
                {
                    "type": "sheets_update", 
                    "name": "Log Response",
                    "integration_id": "{{RESPONSE_TRACKING_SHEET}}"
                },
                {
                    "type": "docs_create",
                    "name": "Response Summary",
                    "template_id": "{{RESPONSE_SUMMARY_TEMPLATE}}"
                }
            ]
        }
    }
    
    return {
        "success": True,
        "templates": templates,
        "timestamp": datetime.utcnow().isoformat()
    }


# Integration Health and Monitoring

@router.get("/health", summary="Check Google Services integration health")
async def check_integration_health(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Check the health and status of Google Services integrations
    """
    try:
        health_status = {
            "overall_status": "healthy",
            "services": {},
            "recent_activity": {}
        }
        
        # Check each service
        for service_type in [GoogleServiceType.SHEETS, GoogleServiceType.DOCS, 
                           GoogleServiceType.DRIVE, GoogleServiceType.GMAIL]:
            creds = await google_services.get_user_credentials(
                str(current_user.id), 
                service_type.value
            )
            
            health_status["services"][service_type.value] = {
                "status": "healthy" if creds else "not_configured",
                "last_used": "N/A",  # Would be populated from actual data
                "error_count": 0
            }
        
        return {
            "success": True,
            "health": health_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check integration health: {str(e)}"
        )