"""
Google Services Integration Service

Provides comprehensive integration with Google Workspace services:
- Google Sheets automation for data tracking
- Google Docs template-based document generation
- Google Drive file management and organization
- Workflow automation and execution
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import asyncio
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

# Google API imports
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

from src.config.database import AsyncSessionLocal
from src.models.user import User
from src.models.email import EmailMessage
from src.models.client import Client
from src.models.response import GeneratedResponse
from src.models.google_services import (
    GoogleServiceCredentials, GoogleSheetIntegration, GoogleDocsTemplate,
    GoogleWorkflow, GoogleWorkflowExecution, GoogleWorkflowStepLog,
    GoogleSheetSyncLog, GoogleGeneratedDoc, GoogleDriveFileMapping,
    GoogleServiceType, WorkflowTrigger, WorkflowStatus
)

logger = logging.getLogger(__name__)


class GoogleServicesIntegration:
    """
    Main service for Google Workspace integration
    """
    
    def __init__(self):
        self.sheets_service = None
        self.docs_service = None
        self.drive_service = None
        self.gmail_service = None
    
    # Authentication and Credentials Management
    
    async def setup_user_credentials(
        self,
        user_id: str,
        service_type: str,
        access_token: str,
        refresh_token: str,
        scopes: List[str],
        expires_at: Optional[datetime] = None
    ) -> str:
        """Setup Google service credentials for a user"""
        try:
            async with AsyncSessionLocal() as session:
                # Check if credentials already exist
                stmt = select(GoogleServiceCredentials).where(
                    and_(
                        GoogleServiceCredentials.user_id == user_id,
                        GoogleServiceCredentials.service_type == service_type
                    )
                )
                result = await session.execute(stmt)
                credentials = result.scalar_one_or_none()
                
                if credentials:
                    # Update existing credentials
                    credentials.access_token = access_token  # Should be encrypted in production
                    credentials.refresh_token = refresh_token  # Should be encrypted in production
                    credentials.token_expires_at = expires_at
                    credentials.scopes = scopes
                    credentials.is_enabled = True
                    credentials.updated_at = datetime.now()
                else:
                    # Create new credentials
                    credentials = GoogleServiceCredentials(
                        user_id=user_id,
                        service_type=service_type,
                        access_token=access_token,  # Should be encrypted in production
                        refresh_token=refresh_token,  # Should be encrypted in production
                        token_expires_at=expires_at,
                        scopes=scopes,
                        is_enabled=True
                    )
                    session.add(credentials)
                
                await session.commit()
                await session.refresh(credentials)
                
                logger.info(f"Google {service_type} credentials setup for user {user_id}")
                return str(credentials.id)
                
        except Exception as e:
            logger.error(f"Failed to setup Google credentials: {str(e)}")
            raise
    
    async def get_user_credentials(self, user_id: str, service_type: str) -> Optional[Credentials]:
        """Get Google credentials for a user and service"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(GoogleServiceCredentials).where(
                    and_(
                        GoogleServiceCredentials.user_id == user_id,
                        GoogleServiceCredentials.service_type == service_type,
                        GoogleServiceCredentials.is_enabled == True
                    )
                )
                result = await session.execute(stmt)
                creds_record = result.scalar_one_or_none()
                
                if not creds_record:
                    return None
                
                # Create Google credentials object
                creds = Credentials(
                    token=creds_record.access_token,
                    refresh_token=creds_record.refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id="",  # Would be loaded from settings
                    client_secret="",  # Would be loaded from settings
                    scopes=creds_record.scopes
                )
                
                # Refresh token if needed
                if creds_record.token_expires_at and creds_record.token_expires_at <= datetime.now():
                    creds.refresh(Request())
                    
                    # Update stored credentials
                    creds_record.access_token = creds.token
                    creds_record.token_expires_at = creds.expiry
                    creds_record.last_used_at = datetime.now()
                    await session.commit()
                
                return creds
                
        except Exception as e:
            logger.error(f"Failed to get Google credentials: {str(e)}")
            return None
    
    # Google Sheets Integration
    
    async def create_sheet_integration(
        self,
        user_id: str,
        spreadsheet_id: str,
        spreadsheet_name: str,
        sheet_name: str,
        integration_type: str,
        column_mapping: Dict[str, Any],
        auto_sync: bool = True
    ) -> str:
        """Create a new Google Sheets integration"""
        try:
            async with AsyncSessionLocal() as session:
                integration = GoogleSheetIntegration(
                    user_id=user_id,
                    spreadsheet_id=spreadsheet_id,
                    spreadsheet_name=spreadsheet_name,
                    sheet_name=sheet_name,
                    integration_type=integration_type,
                    column_mapping=column_mapping,
                    auto_sync=auto_sync
                )
                
                session.add(integration)
                await session.commit()
                await session.refresh(integration)
                
                logger.info(f"Created Google Sheets integration: {integration.id}")
                return str(integration.id)
                
        except Exception as e:
            logger.error(f"Failed to create sheet integration: {str(e)}")
            raise
    
    async def sync_emails_to_sheet(self, user_id: str, integration_id: str) -> Dict[str, Any]:
        """Sync email data to Google Sheets"""
        try:
            async with AsyncSessionLocal() as session:
                # Get integration details
                integration_stmt = select(GoogleSheetIntegration).where(
                    GoogleSheetIntegration.id == integration_id
                )
                integration_result = await session.execute(integration_stmt)
                integration = integration_result.scalar_one_or_none()
                
                if not integration:
                    raise ValueError(f"Sheet integration {integration_id} not found")
                
                # Get user credentials
                creds = await self.get_user_credentials(user_id, GoogleServiceType.SHEETS)
                if not creds:
                    raise ValueError("Google Sheets credentials not found")
                
                # Build Sheets service
                service = build('sheets', 'v4', credentials=creds)
                
                # Get emails to sync
                emails_stmt = select(EmailMessage).where(
                    EmailMessage.user_id == user_id
                ).order_by(EmailMessage.timestamp.desc()).limit(100)
                
                emails_result = await session.execute(emails_stmt)
                emails = emails_result.scalars().all()
                
                # Prepare data for sheets
                rows_data = []
                for email in emails:
                    row = self._map_email_to_sheet_row(email, integration.column_mapping)
                    rows_data.append(row)
                
                # Update Google Sheet
                if rows_data:
                    range_name = f"{integration.sheet_name}!A{integration.last_sync_row + 1}"
                    
                    body = {
                        'values': rows_data
                    }
                    
                    result = service.spreadsheets().values().append(
                        spreadsheetId=integration.spreadsheet_id,
                        range=range_name,
                        valueInputOption='RAW',
                        body=body
                    ).execute()
                    
                    # Update integration record
                    integration.last_synced_at = datetime.now()
                    integration.last_sync_row += len(rows_data)
                    
                    # Log sync operation
                    sync_log = GoogleSheetSyncLog(
                        sheet_integration_id=integration_id,
                        sync_type="automatic",
                        records_processed=len(emails),
                        records_added=len(rows_data),
                        success=True,
                        completed_at=datetime.now()
                    )
                    session.add(sync_log)
                    
                    await session.commit()
                    
                    logger.info(f"Synced {len(rows_data)} emails to sheet {integration.spreadsheet_name}")
                    
                    return {
                        "success": True,
                        "records_synced": len(rows_data),
                        "sheet_id": integration.spreadsheet_id,
                        "range_updated": range_name
                    }
                
                return {
                    "success": True,
                    "records_synced": 0,
                    "message": "No new emails to sync"
                }
                
        except Exception as e:
            logger.error(f"Failed to sync emails to sheet: {str(e)}")
            raise
    
    def _map_email_to_sheet_row(self, email: EmailMessage, column_mapping: Dict[str, Any]) -> List[str]:
        """Map email data to sheet row based on column mapping"""
        try:
            row = []
            
            # Default column mapping if not provided
            default_mapping = {
                "A": "timestamp",
                "B": "sender", 
                "C": "subject",
                "D": "direction",
                "E": "priority",
                "F": "client_name"
            }
            
            mapping = column_mapping or default_mapping
            
            for column in sorted(mapping.keys()):
                field = mapping[column]
                
                if field == "timestamp":
                    value = email.timestamp.isoformat() if email.timestamp else ""
                elif field == "sender":
                    value = email.sender or ""
                elif field == "recipient":
                    value = email.recipient or ""
                elif field == "subject":
                    value = email.subject or ""
                elif field == "direction":
                    value = email.direction or ""
                elif field == "priority":
                    value = email.priority or ""
                elif field == "client_name":
                    value = email.client.name if email.client else ""
                elif field == "labels":
                    value = ", ".join(email.labels) if email.labels else ""
                else:
                    value = ""
                
                row.append(str(value))
            
            return row
            
        except Exception as e:
            logger.error(f"Error mapping email to sheet row: {str(e)}")
            return []
    
    # Google Docs Integration
    
    async def create_docs_template(
        self,
        user_id: str,
        template_name: str,
        template_type: str,
        template_content: str,
        placeholder_mapping: Dict[str, Any],
        auto_generate: bool = False
    ) -> str:
        """Create a Google Docs template"""
        try:
            async with AsyncSessionLocal() as session:
                template = GoogleDocsTemplate(
                    user_id=user_id,
                    template_name=template_name,
                    template_type=template_type,
                    template_content=template_content,
                    placeholder_mapping=placeholder_mapping,
                    auto_generate=auto_generate
                )
                
                session.add(template)
                await session.commit()
                await session.refresh(template)
                
                logger.info(f"Created Google Docs template: {template.id}")
                return str(template.id)
                
        except Exception as e:
            logger.error(f"Failed to create docs template: {str(e)}")
            raise
    
    async def generate_document_from_template(
        self,
        user_id: str,
        template_id: str,
        generation_data: Dict[str, Any],
        document_title: str
    ) -> Dict[str, Any]:
        """Generate a Google Doc from a template"""
        try:
            async with AsyncSessionLocal() as session:
                # Get template
                template_stmt = select(GoogleDocsTemplate).where(
                    GoogleDocsTemplate.id == template_id
                )
                template_result = await session.execute(template_stmt)
                template = template_result.scalar_one_or_none()
                
                if not template:
                    raise ValueError(f"Template {template_id} not found")
                
                # Get credentials
                creds = await self.get_user_credentials(user_id, GoogleServiceType.DOCS)
                if not creds:
                    raise ValueError("Google Docs credentials not found")
                
                # Build services
                docs_service = build('docs', 'v1', credentials=creds)
                drive_service = build('drive', 'v3', credentials=creds)
                
                # Create new document
                doc_body = {
                    'title': document_title
                }
                
                doc = docs_service.documents().create(body=doc_body).execute()
                doc_id = doc.get('documentId')
                
                # Replace placeholders in template content
                content = self._replace_template_placeholders(
                    template.template_content,
                    template.placeholder_mapping,
                    generation_data
                )
                
                # Insert content into document
                requests = [
                    {
                        'insertText': {
                            'location': {
                                'index': 1,
                            },
                            'text': content
                        }
                    }
                ]
                
                docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': requests}
                ).execute()
                
                # Get document URL
                doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
                
                # Store generated document record
                generated_doc = GoogleGeneratedDoc(
                    template_id=template_id,
                    user_id=user_id,
                    google_doc_id=doc_id,
                    document_title=document_title,
                    document_url=doc_url,
                    generation_data=generation_data
                )
                
                session.add(generated_doc)
                await session.commit()
                
                logger.info(f"Generated document {doc_id} from template {template_id}")
                
                return {
                    "success": True,
                    "document_id": doc_id,
                    "document_url": doc_url,
                    "document_title": document_title
                }
                
        except Exception as e:
            logger.error(f"Failed to generate document from template: {str(e)}")
            raise
    
    def _replace_template_placeholders(
        self,
        template_content: str,
        placeholder_mapping: Dict[str, Any],
        generation_data: Dict[str, Any]
    ) -> str:
        """Replace placeholders in template content with actual data"""
        try:
            content = template_content
            
            for placeholder, data_path in placeholder_mapping.items():
                # Extract value from generation_data using dot notation
                value = self._get_nested_value(generation_data, data_path)
                
                # Replace placeholder with value
                content = content.replace(f"{{{placeholder}}}", str(value or ""))
            
            return content
            
        except Exception as e:
            logger.error(f"Error replacing template placeholders: {str(e)}")
            return template_content
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested value from dictionary using dot notation"""
        try:
            keys = path.split('.')
            value = data
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            
            return value
            
        except Exception:
            return None
    
    # Workflow Automation
    
    async def create_workflow(
        self,
        user_id: str,
        workflow_name: str,
        description: str,
        trigger_type: str,
        trigger_conditions: Dict[str, Any],
        workflow_steps: List[Dict[str, Any]]
    ) -> str:
        """Create an automated workflow"""
        try:
            async with AsyncSessionLocal() as session:
                # Get credentials ID for the workflow
                creds_stmt = select(GoogleServiceCredentials).where(
                    and_(
                        GoogleServiceCredentials.user_id == user_id,
                        GoogleServiceCredentials.is_enabled == True
                    )
                ).limit(1)
                
                creds_result = await session.execute(creds_stmt)
                credentials = creds_result.scalar_one_or_none()
                
                if not credentials:
                    raise ValueError("No active Google credentials found for user")
                
                workflow = GoogleWorkflow(
                    user_id=user_id,
                    credentials_id=str(credentials.id),
                    workflow_name=workflow_name,
                    description=description,
                    trigger_type=trigger_type,
                    trigger_conditions=trigger_conditions,
                    workflow_steps=workflow_steps
                )
                
                session.add(workflow)
                await session.commit()
                await session.refresh(workflow)
                
                logger.info(f"Created workflow: {workflow.id}")
                return str(workflow.id)
                
        except Exception as e:
            logger.error(f"Failed to create workflow: {str(e)}")
            raise
    
    async def execute_workflow(self, workflow_id: str, trigger_data: Dict[str, Any] = None) -> str:
        """Execute a workflow"""
        try:
            async with AsyncSessionLocal() as session:
                # Get workflow
                workflow_stmt = select(GoogleWorkflow).where(
                    GoogleWorkflow.id == workflow_id
                )
                workflow_result = await session.execute(workflow_stmt)
                workflow = workflow_result.scalar_one_or_none()
                
                if not workflow or not workflow.is_active:
                    raise ValueError(f"Workflow {workflow_id} not found or inactive")
                
                # Create execution record
                execution = GoogleWorkflowExecution(
                    workflow_id=workflow_id,
                    execution_status=WorkflowStatus.RUNNING,
                    trigger_data=trigger_data or {}
                )
                
                session.add(execution)
                await session.commit()
                await session.refresh(execution)
                
                # Execute workflow steps
                try:
                    for i, step in enumerate(workflow.workflow_steps):
                        step_result = await self._execute_workflow_step(
                            execution.id,
                            i,
                            step,
                            workflow.user_id,
                            trigger_data or {}
                        )
                        
                        if not step_result["success"]:
                            execution.execution_status = WorkflowStatus.FAILED
                            execution.error_message = step_result.get("error")
                            break
                    
                    else:
                        execution.execution_status = WorkflowStatus.COMPLETED
                    
                    execution.completed_at = datetime.now()
                    execution.duration_seconds = int(
                        (execution.completed_at - execution.started_at).total_seconds()
                    )
                    
                    # Update workflow statistics
                    workflow.execution_count += 1
                    if execution.execution_status == WorkflowStatus.COMPLETED:
                        workflow.success_count += 1
                    else:
                        workflow.failure_count += 1
                    workflow.last_executed_at = datetime.now()
                    
                    await session.commit()
                    
                    logger.info(f"Workflow execution {execution.id} completed with status {execution.execution_status}")
                    return str(execution.id)
                    
                except Exception as e:
                    execution.execution_status = WorkflowStatus.FAILED
                    execution.error_message = str(e)
                    execution.completed_at = datetime.now()
                    workflow.failure_count += 1
                    await session.commit()
                    raise
                
        except Exception as e:
            logger.error(f"Failed to execute workflow: {str(e)}")
            raise
    
    async def _execute_workflow_step(
        self,
        execution_id: str,
        step_index: int,
        step_config: Dict[str, Any],
        user_id: str,
        trigger_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single workflow step"""
        try:
            async with AsyncSessionLocal() as session:
                # Create step log
                step_log = GoogleWorkflowStepLog(
                    execution_id=execution_id,
                    step_index=step_index,
                    step_name=step_config.get("name", f"Step {step_index + 1}"),
                    step_type=step_config.get("type"),
                    status="running",
                    input_data=step_config
                )
                
                session.add(step_log)
                await session.commit()
                await session.refresh(step_log)
                
                result = {"success": False, "output": {}}
                
                try:
                    # Execute step based on type
                    step_type = step_config.get("type")
                    
                    if step_type == "sheets_update":
                        result = await self._execute_sheets_update_step(user_id, step_config, trigger_data)
                    elif step_type == "docs_create":
                        result = await self._execute_docs_create_step(user_id, step_config, trigger_data)
                    elif step_type == "drive_upload":
                        result = await self._execute_drive_upload_step(user_id, step_config, trigger_data)
                    else:
                        raise ValueError(f"Unknown step type: {step_type}")
                    
                    step_log.status = "completed"
                    step_log.output_data = result.get("output", {})
                    
                except Exception as e:
                    step_log.status = "failed"
                    step_log.error_message = str(e)
                    result = {"success": False, "error": str(e)}
                
                step_log.completed_at = datetime.now()
                await session.commit()
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to execute workflow step: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _execute_sheets_update_step(
        self,
        user_id: str,
        step_config: Dict[str, Any],
        trigger_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a Google Sheets update step"""
        try:
            integration_id = step_config.get("integration_id")
            if not integration_id:
                raise ValueError("integration_id required for sheets_update step")
            
            # Perform the sheet sync
            result = await self.sync_emails_to_sheet(user_id, integration_id)
            
            return {
                "success": True,
                "output": result
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_docs_create_step(
        self,
        user_id: str,
        step_config: Dict[str, Any],
        trigger_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a Google Docs creation step"""
        try:
            template_id = step_config.get("template_id")
            document_title = step_config.get("document_title", "Generated Document")
            
            if not template_id:
                raise ValueError("template_id required for docs_create step")
            
            # Generate document from template
            result = await self.generate_document_from_template(
                user_id=user_id,
                template_id=template_id,
                generation_data=trigger_data,
                document_title=document_title
            )
            
            return {
                "success": True,
                "output": result
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_drive_upload_step(
        self,
        user_id: str,
        step_config: Dict[str, Any],
        trigger_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a Google Drive upload step"""
        # This would implement file upload to Google Drive
        # For now, return a placeholder
        return {
            "success": True,
            "output": {"message": "Drive upload step not yet implemented"}
        }


# Global service instance
google_services = GoogleServicesIntegration()