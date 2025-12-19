"""Schemas for the AI Assistant Chat functionality."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """Types of user intents the assistant can recognize."""

    QUERY = "query"  # Read-only query
    CONTEXT_QUERY = "context_query"  # Query about current entity/page
    INLINE_EDIT = "inline_edit"  # Simple edit operation
    COMPLEX_WRITE = "complex_write"  # Complex write -> redirect to Smart Query
    NAVIGATION = "navigation"  # Navigate to another page
    SUMMARIZE = "summarize"  # Summarize current entity
    HELP = "help"  # App help
    BATCH_ACTION = "batch_action"  # Bulk operation on multiple entities


class ViewMode(str, Enum):
    """Current view mode in the app."""

    DASHBOARD = "dashboard"
    LIST = "list"
    DETAIL = "detail"
    EDIT = "edit"
    UNKNOWN = "unknown"


class AssistantContext(BaseModel):
    """Context information about the current app state."""

    current_route: str = Field(..., description="Current route path")
    current_entity_id: Optional[str] = Field(None, description="ID of the current entity if on detail page")
    current_entity_type: Optional[str] = Field(None, description="Type slug of the current entity")
    current_entity_name: Optional[str] = Field(None, description="Name of the current entity")
    view_mode: ViewMode = Field(default=ViewMode.UNKNOWN, description="Current view mode")
    available_actions: List[str] = Field(default_factory=list, description="Actions available on current page")


class ConversationMessage(BaseModel):
    """A single message in the conversation history."""

    role: Literal["user", "assistant"] = Field(..., description="Who sent this message")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AttachmentInfo(BaseModel):
    """Information about an uploaded attachment."""

    attachment_id: str = Field(..., description="Unique identifier for the attachment")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type of the file")
    size: int = Field(..., description="File size in bytes")


class AttachmentUploadResponse(BaseModel):
    """Response after uploading an attachment."""

    success: bool = True
    attachment: AttachmentInfo


class AssistantChatRequest(BaseModel):
    """Request to the assistant chat endpoint."""

    message: str = Field(..., min_length=1, max_length=2000, description="User's message")
    context: AssistantContext = Field(..., description="Current app context")
    conversation_history: List[ConversationMessage] = Field(
        default_factory=list,
        max_length=20,
        description="Previous messages in the conversation"
    )
    mode: Literal["read", "write"] = Field(default="read", description="Current chat mode")
    language: Literal["de", "en"] = Field(default="de", description="Language for responses")
    attachment_ids: List[str] = Field(default_factory=list, description="IDs of uploaded attachments")


# Response Types

class QueryResultData(BaseModel):
    """Data returned from a query."""

    items: List[Dict[str, Any]] = Field(default_factory=list)
    total: int = Field(default=0)
    grouping: Optional[str] = None
    query_interpretation: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    """Response for query results."""

    type: Literal["query_result"] = "query_result"
    message: str = Field(..., description="Human-readable summary")
    data: QueryResultData = Field(..., description="Query results")
    follow_up_suggestions: List[str] = Field(default_factory=list)


class ActionChange(BaseModel):
    """A single change in an action."""

    field: str
    from_value: Any = Field(alias="from")
    to_value: Any = Field(alias="to")

    class Config:
        populate_by_name = True


class ActionDetails(BaseModel):
    """Details of an action to be executed."""

    type: str = Field(..., description="Action type: update_entity, create_facet, delete_relation, etc.")
    target_id: Optional[str] = Field(None, description="ID of the target entity")
    target_name: Optional[str] = Field(None, description="Name of the target entity")
    target_type: Optional[str] = Field(None, description="Type of the target entity")
    changes: Dict[str, ActionChange] = Field(default_factory=dict)
    create_data: Optional[Dict[str, Any]] = Field(None, description="Data for create operations")


class ActionPreviewResponse(BaseModel):
    """Response with an action preview for confirmation."""

    type: Literal["action_preview"] = "action_preview"
    message: str = Field(..., description="Description of what will happen")
    action: ActionDetails = Field(..., description="Action details")
    requires_confirmation: bool = Field(default=True)


class NavigationTarget(BaseModel):
    """Target for navigation."""

    route: str = Field(..., description="Route to navigate to")
    entity_type: Optional[str] = None
    entity_slug: Optional[str] = None
    entity_name: Optional[str] = None


class NavigationResponse(BaseModel):
    """Response suggesting navigation."""

    type: Literal["navigation"] = "navigation"
    message: str
    target: NavigationTarget


class RedirectResponse(BaseModel):
    """Response redirecting to Smart Query page."""

    type: Literal["redirect_to_smart_query"] = "redirect_to_smart_query"
    message: str
    prefilled_query: Optional[str] = Field(None, description="Query to prefill in Smart Query")
    write_mode: bool = Field(default=True)


class HelpResponse(BaseModel):
    """Response with help information."""

    type: Literal["help"] = "help"
    message: str
    help_topics: List[Dict[str, str]] = Field(default_factory=list)
    suggested_commands: List[str] = Field(default_factory=list)


class ErrorResponseData(BaseModel):
    """Error response from assistant."""

    type: Literal["error"] = "error"
    message: str
    error_code: Optional[str] = None


class SuggestedAction(BaseModel):
    """A suggested action the user can take."""

    label: str
    action: str  # 'query', 'edit', 'navigate', 'help'
    value: str  # The actual command/query


# Union type for all possible responses
AssistantResponseData = Union[
    QueryResponse,
    ActionPreviewResponse,
    NavigationResponse,
    RedirectResponse,
    HelpResponse,
    ErrorResponseData,
]


class AssistantChatResponse(BaseModel):
    """Response from the assistant chat endpoint."""

    success: bool = True
    response: AssistantResponseData
    suggested_actions: List[SuggestedAction] = Field(default_factory=list)
    conversation_id: Optional[str] = Field(None, description="ID for conversation tracking")


# Action Execution

class ActionExecuteRequest(BaseModel):
    """Request to execute a confirmed action."""

    action: ActionDetails
    context: AssistantContext


class ActionExecuteResponse(BaseModel):
    """Response after executing an action."""

    success: bool
    message: str
    affected_entity_id: Optional[str] = None
    affected_entity_name: Optional[str] = None
    refresh_required: bool = Field(default=True, description="Whether the UI should refresh")


# Slash Commands

class SlashCommand(BaseModel):
    """A slash command definition."""

    command: str = Field(..., description="Command name without slash")
    description: str
    usage: str
    examples: List[str] = Field(default_factory=list)


SLASH_COMMANDS = [
    SlashCommand(
        command="help",
        description="Zeigt Hilfe und verfuegbare Befehle",
        usage="/help [thema]",
        examples=["/help", "/help entities", "/help facets"]
    ),
    SlashCommand(
        command="search",
        description="Sucht nach Entities",
        usage="/search <suchbegriff>",
        examples=["/search Gummersbach", "/search Buergermeister"]
    ),
    SlashCommand(
        command="create",
        description="Erstellt neue Datensaetze (oeffnet Write-Mode)",
        usage="/create <typ> <details>",
        examples=["/create person Max Mueller", "/create pain_point Personalmangel"]
    ),
    SlashCommand(
        command="summary",
        description="Fasst die aktuelle Entity zusammen",
        usage="/summary",
        examples=["/summary"]
    ),
    SlashCommand(
        command="navigate",
        description="Navigiert zu einer Entity",
        usage="/navigate <entity-name>",
        examples=["/navigate Gummersbach", "/navigate Max Mueller"]
    ),
]


# ============================================================================
# Batch Operations
# ============================================================================


class BatchActionType(str, Enum):
    """Types of batch actions that can be performed."""

    ADD_FACET = "add_facet"
    UPDATE_FIELD = "update_field"
    ADD_RELATION = "add_relation"
    REMOVE_FACET = "remove_facet"


class BatchActionRequest(BaseModel):
    """Request to perform a batch action on multiple entities."""

    action_type: BatchActionType = Field(..., description="Type of batch action")
    target_filter: Dict[str, Any] = Field(
        ...,
        description="Filter to select target entities (e.g. entity_type, location)"
    )
    action_data: Dict[str, Any] = Field(
        ...,
        description="Data for the action (e.g. facet_type, value)"
    )
    dry_run: bool = Field(
        default=True,
        description="If true, only return preview without executing"
    )


class BatchActionPreview(BaseModel):
    """Preview of entities that will be affected by a batch action."""

    entity_id: str
    entity_name: str
    entity_type: str


class BatchActionResponse(BaseModel):
    """Response from a batch action request."""

    success: bool = True
    affected_count: int = Field(..., description="Number of entities affected")
    preview: List[BatchActionPreview] = Field(
        default_factory=list,
        description="Preview of first 10 affected entities"
    )
    batch_id: Optional[str] = Field(
        None,
        description="ID for tracking batch execution (empty for dry_run)"
    )
    message: str = Field(default="", description="Status message")


class BatchStatusResponse(BaseModel):
    """Status of a running or completed batch operation."""

    batch_id: str
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    processed: int = 0
    total: int = 0
    errors: List[Dict[str, str]] = Field(default_factory=list)
    message: str = ""


class BatchActionChatResponse(BaseModel):
    """Response for batch action in chat context."""

    type: Literal["batch_preview"] = "batch_preview"
    message: str
    affected_count: int
    preview: List[BatchActionPreview]
    action_type: str
    action_data: Dict[str, Any]
    target_filter: Dict[str, Any]
    requires_confirmation: bool = True


# ============================================================================
# Conversational Wizards
# ============================================================================


class WizardInputType(str, Enum):
    """Types of input fields for wizard steps."""

    TEXT = "text"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    ENTITY_SEARCH = "entity_search"
    DATE = "date"
    NUMBER = "number"
    TEXTAREA = "textarea"
    CONFIRM = "confirm"


class WizardStepOption(BaseModel):
    """An option for select/multi_select wizard steps."""

    value: str
    label: str
    description: Optional[str] = None
    icon: Optional[str] = None


class WizardStep(BaseModel):
    """Definition of a single wizard step."""

    id: str = Field(..., description="Unique step identifier")
    question: str = Field(..., description="The question to ask the user")
    input_type: WizardInputType = Field(..., description="Type of input expected")
    options: Optional[List[WizardStepOption]] = Field(None, description="Options for select types")
    placeholder: Optional[str] = Field(None, description="Placeholder text for input")
    validation: Optional[Dict[str, Any]] = Field(None, description="Validation rules")
    entity_type: Optional[str] = Field(None, description="Entity type for entity_search")
    default_value: Optional[Any] = Field(None, description="Default value")
    required: bool = Field(default=True, description="Whether this step is required")
    help_text: Optional[str] = Field(None, description="Additional help text")


class WizardState(BaseModel):
    """Current state of a wizard conversation."""

    wizard_id: str = Field(..., description="Unique wizard instance ID")
    wizard_type: str = Field(..., description="Type of wizard (e.g., 'create_entity')")
    current_step_id: str = Field(..., description="ID of the current step")
    current_step_index: int = Field(default=0, description="Index of current step")
    total_steps: int = Field(..., description="Total number of steps")
    answers: Dict[str, Any] = Field(default_factory=dict, description="Collected answers")
    completed: bool = Field(default=False, description="Whether wizard is complete")
    cancelled: bool = Field(default=False, description="Whether wizard was cancelled")


class WizardDefinition(BaseModel):
    """Definition of a complete wizard."""

    type: str = Field(..., description="Wizard type identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Description of what this wizard does")
    steps: List[WizardStep] = Field(..., description="List of wizard steps")
    icon: Optional[str] = Field(None, description="Icon for the wizard")


class WizardResponse(BaseModel):
    """Response containing wizard data for the chat."""

    type: Literal["wizard"] = "wizard"
    message: str = Field(..., description="Message to display")
    wizard_state: WizardState = Field(..., description="Current wizard state")
    current_step: WizardStep = Field(..., description="Current step definition")
    can_go_back: bool = Field(default=False, description="Whether user can go back")
    progress: float = Field(..., description="Progress 0.0 - 1.0")


# ============================================================================
# Reminders
# ============================================================================


class ReminderRepeatType(str, Enum):
    """Repeat types for reminders."""

    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ReminderCreate(BaseModel):
    """Request to create a new reminder."""

    message: str = Field(..., min_length=1, max_length=1000, description="Reminder message")
    remind_at: datetime = Field(..., description="When to send the reminder")
    title: Optional[str] = Field(None, max_length=255, description="Optional title")
    entity_id: Optional[str] = Field(None, description="Optional entity ID to link")
    entity_type: Optional[str] = Field(None, description="Entity type if entity_id is provided")
    repeat: ReminderRepeatType = Field(default=ReminderRepeatType.NONE, description="Repeat interval")


class ReminderResponse(BaseModel):
    """Response with reminder data."""

    id: str
    message: str
    title: Optional[str] = None
    remind_at: datetime
    repeat: str
    status: str
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_name: Optional[str] = None
    created_at: datetime


class ReminderListResponse(BaseModel):
    """Response with list of reminders."""

    items: List[ReminderResponse]
    total: int


class ReminderChatResponse(BaseModel):
    """Response for reminder in chat context."""

    type: Literal["reminder_created"] = "reminder_created"
    message: str
    reminder: ReminderResponse
