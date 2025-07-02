from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class SetupWizardProgressSchema(BaseModel):
    """Schema for setup wizard progress tracking"""
    user_id: str
    step_1_google_auth: bool = False
    step_2_email_preferences: bool = False
    step_3_writing_style: bool = False
    step_4_client_categories: bool = False
    step_5_response_automation: bool = False
    step_6_notifications: bool = False
    step_7_integrations: bool = False
    step_8_verification: bool = False
    current_step: int = Field(ge=1, le=8, default=1)
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class EmailPreferencesSchema(BaseModel):
    """Schema for email preferences configuration"""
    check_frequency_minutes: int = Field(ge=1, le=60, default=1)
    filter_marketing: bool = True
    filter_spam: bool = True
    filter_promotions: bool = False
    auto_respond_enabled: bool = False
    auto_respond_delay_minutes: int = Field(ge=0, le=1440, default=5)
    preferred_languages: List[str] = Field(default=["cs", "en"])
    working_hours_start: str = Field(regex=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', default="09:00")
    working_hours_end: str = Field(regex=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', default="17:00")
    working_days: List[str] = Field(default=["monday", "tuesday", "wednesday", "thursday", "friday"])
    timezone: str = Field(default="Europe/Prague")
    
    class Config:
        from_attributes = True


class WritingStyleConfigurationSchema(BaseModel):
    """Schema for writing style configuration"""
    formality_level: str = Field(regex=r'^(casual|professional|formal)$', default="professional")
    tone: str = Field(regex=r'^(friendly|neutral|authoritative)$', default="friendly")
    verbosity: str = Field(regex=r'^(brief|concise|detailed)$', default="concise")
    signature_style: str = Field(regex=r'^(minimal|standard|detailed)$', default="standard")
    greeting_style: str = Field(regex=r'^(minimal|contextual|formal)$', default="contextual")
    use_technical_terms: bool = True
    use_emojis: bool = False
    use_abbreviations: bool = True
    response_urgency_detection: bool = True
    
    class Config:
        from_attributes = True


class ClientCategoryConfigurationSchema(BaseModel):
    """Schema for client category configuration"""
    category_name: str = Field(min_length=1, max_length=100)
    category_description: Optional[str] = None
    domain_patterns: List[str] = Field(default=[])
    sender_patterns: List[str] = Field(default=[])
    subject_keywords: List[str] = Field(default=[])
    response_template: Optional[str] = None
    formality_level: str = Field(regex=r'^(casual|professional|formal)$', default="professional")
    response_delay_minutes: int = Field(ge=0, le=1440, default=5)
    auto_respond_enabled: bool = False
    priority_level: str = Field(regex=r'^(low|normal|high|urgent)$', default="normal")
    escalation_rules: List[Dict[str, Any]] = Field(default=[])
    
    class Config:
        from_attributes = True


class ClientCategoryConfigurationCreate(ClientCategoryConfigurationSchema):
    """Schema for creating client category configuration"""
    pass


class ClientCategoryConfigurationUpdate(BaseModel):
    """Schema for updating client category configuration"""
    category_name: Optional[str] = Field(None, min_length=1, max_length=100)
    category_description: Optional[str] = None
    domain_patterns: Optional[List[str]] = None
    sender_patterns: Optional[List[str]] = None
    subject_keywords: Optional[List[str]] = None
    response_template: Optional[str] = None
    formality_level: Optional[str] = Field(None, regex=r'^(casual|professional|formal)$')
    response_delay_minutes: Optional[int] = Field(None, ge=0, le=1440)
    auto_respond_enabled: Optional[bool] = None
    priority_level: Optional[str] = Field(None, regex=r'^(low|normal|high|urgent)$')
    escalation_rules: Optional[List[Dict[str, Any]]] = None


class AutomationConfigurationSchema(BaseModel):
    """Schema for automation configuration"""
    auto_respond_enabled: bool = False
    auto_respond_confidence_threshold: int = Field(ge=0, le=100, default=80)
    daily_summary_enabled: bool = True
    daily_summary_time: str = Field(regex=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', default="08:00")
    weekly_report_enabled: bool = True
    weekly_report_day: str = Field(regex=r'^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$', default="monday")
    weekly_report_time: str = Field(regex=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', default="09:00")
    google_sheets_integration: bool = False
    google_docs_integration: bool = False
    google_drive_integration: bool = False
    maximum_auto_responses_per_day: int = Field(ge=1, le=1000, default=50)
    require_confirmation_for_important: bool = True
    
    class Config:
        from_attributes = True


class NotificationConfigurationSchema(BaseModel):
    """Schema for notification configuration"""
    email_notifications_enabled: bool = True
    notification_email: Optional[str] = None
    notify_new_emails: bool = False
    notify_auto_responses: bool = True
    notify_high_priority: bool = True
    notify_errors: bool = True
    digest_frequency: str = Field(regex=r'^(realtime|hourly|daily|weekly)$', default="daily")
    quiet_hours_start: str = Field(regex=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', default="22:00")
    quiet_hours_end: str = Field(regex=r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', default="07:00")
    browser_notifications: bool = True
    mobile_notifications: bool = False
    
    class Config:
        from_attributes = True


class IntegrationConfigurationSchema(BaseModel):
    """Schema for integration configuration"""
    gmail_integration: bool = True
    google_calendar_integration: bool = False
    google_drive_integration: bool = False
    google_sheets_integration: bool = False
    google_docs_integration: bool = False
    preferred_ai_model: str = Field(regex=r'^(openai|local|hybrid)$', default="openai")
    local_model_path: Optional[str] = None
    vector_db_type: str = Field(regex=r'^(chromadb|faiss|weaviate)$', default="chromadb")
    slack_integration: bool = False
    teams_integration: bool = False
    integration_settings: Dict[str, Any] = Field(default={})
    
    class Config:
        from_attributes = True


class SetupWizardStepRequest(BaseModel):
    """Request schema for completing a setup wizard step"""
    step_number: int = Field(ge=1, le=8)
    step_data: Dict[str, Any]


class SetupWizardStepResponse(BaseModel):
    """Response schema for setup wizard step completion"""
    success: bool
    message: str
    current_step: int
    next_step: Optional[int] = None
    is_completed: bool = False
    
    
class SetupWizardCompleteResponse(BaseModel):
    """Response schema for complete setup wizard status"""
    user_id: str
    is_completed: bool
    completed_at: Optional[datetime] = None
    progress: SetupWizardProgressSchema
    email_preferences: Optional[EmailPreferencesSchema] = None
    writing_style_configuration: Optional[WritingStyleConfigurationSchema] = None
    client_categories: List[ClientCategoryConfigurationSchema] = Field(default=[])
    automation_configuration: Optional[AutomationConfigurationSchema] = None
    notification_configuration: Optional[NotificationConfigurationSchema] = None
    integration_configuration: Optional[IntegrationConfigurationSchema] = None