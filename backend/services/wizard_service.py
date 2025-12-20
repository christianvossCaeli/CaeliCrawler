"""Wizard Service - Conversational wizards for guided data entry.

This service provides step-by-step guided workflows for complex operations
like creating entities, adding facets, or configuring batch operations.

## Available Wizards

### create_entity
Creates a new entity with guided input for type, name, and location.

### add_pain_point
Adds a pain point facet to an entity with severity and description.

### bulk_facet
Adds facets to multiple entities based on filters.

## Usage
Wizards are triggered through the chat assistant by commands like:
- "Erstelle neue Entity" or "Create new entity"
- "Füge Pain Point hinzu" or "Add pain point"

The wizard state is maintained in the conversation and each user
response advances to the next step until completion.
"""

import structlog
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Entity, EntityType, FacetType, FacetValue
from app.models.facet_value import FacetValueSourceType
from app.schemas.assistant import (
    WizardDefinition,
    WizardStep,
    WizardStepOption,
    WizardState,
    WizardResponse,
    WizardInputType,
)

logger = structlog.get_logger()


# ============================================================================
# Wizard Definitions
# ============================================================================

WIZARD_DEFINITIONS: Dict[str, WizardDefinition] = {
    "create_entity": WizardDefinition(
        type="create_entity",
        name="Entity erstellen",
        description="Erstelle eine neue Entity im System",
        icon="mdi-plus-circle",
        steps=[
            WizardStep(
                id="entity_type",
                question="Welchen Entity-Typ möchtest du erstellen?",
                input_type=WizardInputType.SELECT,
                options=[],  # Dynamically populated
                placeholder="Entity-Typ auswählen",
                required=True,
            ),
            WizardStep(
                id="name",
                question="Wie soll die Entity heißen?",
                input_type=WizardInputType.TEXT,
                placeholder="Name eingeben",
                validation={"min_length": 2, "max_length": 200},
                required=True,
            ),
            WizardStep(
                id="description",
                question="Beschreibe die Entity kurz (optional):",
                input_type=WizardInputType.TEXTAREA,
                placeholder="Beschreibung eingeben",
                required=False,
            ),
            WizardStep(
                id="confirm",
                question="Soll ich diese Entity erstellen?",
                input_type=WizardInputType.CONFIRM,
                options=[
                    WizardStepOption(value="yes", label="Ja, erstellen"),
                    WizardStepOption(value="no", label="Nein, abbrechen"),
                ],
                required=True,
            ),
        ],
    ),
    "add_pain_point": WizardDefinition(
        type="add_pain_point",
        name="Pain Point hinzufügen",
        description="Füge einen Pain Point zu einer Entity hinzu",
        icon="mdi-alert-circle",
        steps=[
            WizardStep(
                id="entity",
                question="Für welche Entity möchtest du den Pain Point hinzufügen?",
                input_type=WizardInputType.ENTITY_SEARCH,
                placeholder="Entity suchen",
                required=True,
            ),
            WizardStep(
                id="severity",
                question="Wie schwerwiegend ist der Pain Point?",
                input_type=WizardInputType.SELECT,
                options=[
                    WizardStepOption(value="low", label="Niedrig", icon="mdi-chevron-down"),
                    WizardStepOption(value="medium", label="Mittel", icon="mdi-minus"),
                    WizardStepOption(value="high", label="Hoch", icon="mdi-chevron-up"),
                    WizardStepOption(value="critical", label="Kritisch", icon="mdi-alert"),
                ],
                required=True,
            ),
            WizardStep(
                id="description",
                question="Beschreibe den Pain Point:",
                input_type=WizardInputType.TEXTAREA,
                placeholder="Pain Point beschreiben",
                validation={"min_length": 10},
                required=True,
            ),
            WizardStep(
                id="confirm",
                question="Soll ich diesen Pain Point speichern?",
                input_type=WizardInputType.CONFIRM,
                options=[
                    WizardStepOption(value="yes", label="Ja, speichern"),
                    WizardStepOption(value="no", label="Nein, abbrechen"),
                ],
                required=True,
            ),
        ],
    ),
    "quick_search": WizardDefinition(
        type="quick_search",
        name="Erweiterte Suche",
        description="Suche mit erweiterten Filtern",
        icon="mdi-magnify",
        steps=[
            WizardStep(
                id="entity_type",
                question="Welchen Entity-Typ möchtest du durchsuchen?",
                input_type=WizardInputType.SELECT,
                options=[],  # Dynamically populated
                placeholder="Entity-Typ auswählen",
                required=True,
            ),
            WizardStep(
                id="search_term",
                question="Nach welchem Begriff suchst du?",
                input_type=WizardInputType.TEXT,
                placeholder="Suchbegriff eingeben",
                required=False,
            ),
            WizardStep(
                id="has_pain_points",
                question="Sollen nur Entities mit Pain Points angezeigt werden?",
                input_type=WizardInputType.SELECT,
                options=[
                    WizardStepOption(value="any", label="Egal"),
                    WizardStepOption(value="yes", label="Ja, nur mit Pain Points"),
                    WizardStepOption(value="no", label="Nein, nur ohne Pain Points"),
                ],
                default_value="any",
                required=True,
            ),
        ],
    ),
}


class WizardService:
    """Service for managing conversational wizards.

    Wizards provide guided step-by-step workflows for complex operations.
    Each wizard maintains state across multiple chat interactions.

    Attributes:
        db: Database session for data operations
        active_wizards: In-memory storage for active wizard sessions
    """

    # In-memory storage for active wizard sessions (in production, use Redis)
    _active_wizards: Dict[str, Dict[str, Any]] = {}
    _last_cleanup_time: float = 0.0

    # Wizard session expiry time (30 minutes)
    WIZARD_EXPIRY_SECONDS = 30 * 60
    # Cleanup check interval (5 minutes)
    CLEANUP_INTERVAL_SECONDS = 5 * 60

    def __init__(self, db: AsyncSession):
        """Initialize the wizard service.

        Args:
            db: SQLAlchemy async database session
        """
        self.db = db
        self._cleanup_expired_wizards()

    @classmethod
    def _cleanup_expired_wizards(cls) -> None:
        """Clean up expired wizard sessions to prevent memory leaks.

        Called periodically during service initialization.
        Removes wizard sessions older than WIZARD_EXPIRY_SECONDS.
        """
        current_time = time.time()

        # Only run cleanup every CLEANUP_INTERVAL_SECONDS
        if current_time - cls._last_cleanup_time < cls.CLEANUP_INTERVAL_SECONDS:
            return

        cls._last_cleanup_time = current_time
        expiry_threshold = current_time - cls.WIZARD_EXPIRY_SECONDS

        # Find and remove expired wizards
        expired_wizards = [
            wizard_id for wizard_id, data in cls._active_wizards.items()
            if data.get("created_at", datetime.min).timestamp() < expiry_threshold
        ]

        for wizard_id in expired_wizards:
            del cls._active_wizards[wizard_id]
            logger.info("wizard_expired_cleanup", wizard_id=wizard_id)

    async def get_available_wizards(self) -> List[Dict[str, Any]]:
        """Get list of available wizard types.

        Returns:
            List of wizard definitions with basic info
        """
        return [
            {
                "type": w.type,
                "name": w.name,
                "description": w.description,
                "icon": w.icon,
            }
            for w in WIZARD_DEFINITIONS.values()
        ]

    async def start_wizard(
        self,
        wizard_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> WizardResponse:
        """Start a new wizard session.

        Args:
            wizard_type: Type of wizard to start (e.g., 'create_entity')
            context: Optional context data (e.g., current entity)

        Returns:
            WizardResponse with first step

        Raises:
            ValueError: If wizard_type is not found
        """
        if wizard_type not in WIZARD_DEFINITIONS:
            raise ValueError(f"Unknown wizard type: {wizard_type}")

        definition = WIZARD_DEFINITIONS[wizard_type]
        wizard_id = str(uuid4())

        # Prepare steps with dynamic options
        steps = await self._prepare_steps(definition.steps, context)

        # Create initial state
        state = WizardState(
            wizard_id=wizard_id,
            wizard_type=wizard_type,
            current_step_id=steps[0].id,
            current_step_index=0,
            total_steps=len(steps),
            answers={},
            completed=False,
            cancelled=False,
        )

        # Store wizard state
        self._active_wizards[wizard_id] = {
            "state": state,
            "steps": steps,
            "definition": definition,
            "context": context or {},
            "created_at": datetime.now(timezone.utc),
        }

        return WizardResponse(
            message=f"**{definition.name}**\n\n{steps[0].question}",
            wizard_state=state,
            current_step=steps[0],
            can_go_back=False,
            progress=0.0,
        )

    async def process_wizard_response(
        self,
        wizard_id: str,
        response: Any
    ) -> Tuple[WizardResponse, Optional[Dict[str, Any]]]:
        """Process a user response for an active wizard.

        Args:
            wizard_id: The wizard session ID
            response: User's response value

        Returns:
            Tuple of (WizardResponse, result) where result is the final
            execution result if wizard completed, otherwise None

        Raises:
            ValueError: If wizard_id not found or wizard already completed
        """
        if wizard_id not in self._active_wizards:
            raise ValueError(f"Wizard session not found: {wizard_id}")

        wizard_data = self._active_wizards[wizard_id]
        state = wizard_data["state"]
        steps = wizard_data["steps"]
        definition = wizard_data["definition"]

        if state.completed or state.cancelled:
            raise ValueError("Wizard already completed or cancelled")

        current_step = steps[state.current_step_index]

        # Validate response
        validation_error = self._validate_response(current_step, response)
        if validation_error:
            return WizardResponse(
                message=f"**Ungültige Eingabe:** {validation_error}\n\n{current_step.question}",
                wizard_state=state,
                current_step=current_step,
                can_go_back=state.current_step_index > 0,
                progress=state.current_step_index / state.total_steps,
            ), None

        # Handle confirmation step
        if current_step.input_type == WizardInputType.CONFIRM:
            if response == "no":
                state.cancelled = True
                del self._active_wizards[wizard_id]
                return WizardResponse(
                    message="Wizard abgebrochen.",
                    wizard_state=state,
                    current_step=current_step,
                    can_go_back=False,
                    progress=1.0,
                ), None

        # Store answer
        state.answers[current_step.id] = response

        # Check if this was the last step
        if state.current_step_index >= len(steps) - 1:
            state.completed = True
            result = await self._execute_wizard(wizard_data)
            del self._active_wizards[wizard_id]

            return WizardResponse(
                message=result.get("message", "Wizard abgeschlossen!"),
                wizard_state=state,
                current_step=current_step,
                can_go_back=False,
                progress=1.0,
            ), result

        # Advance to next step
        state.current_step_index += 1
        state.current_step_id = steps[state.current_step_index].id
        next_step = steps[state.current_step_index]

        return WizardResponse(
            message=next_step.question,
            wizard_state=state,
            current_step=next_step,
            can_go_back=state.current_step_index > 0,
            progress=state.current_step_index / state.total_steps,
        ), None

    async def go_back(self, wizard_id: str) -> WizardResponse:
        """Go back to the previous wizard step.

        Args:
            wizard_id: The wizard session ID

        Returns:
            WizardResponse with previous step

        Raises:
            ValueError: If wizard not found or can't go back
        """
        if wizard_id not in self._active_wizards:
            raise ValueError(f"Wizard session not found: {wizard_id}")

        wizard_data = self._active_wizards[wizard_id]
        state = wizard_data["state"]
        steps = wizard_data["steps"]

        if state.current_step_index == 0:
            raise ValueError("Cannot go back from first step")

        # Go back
        state.current_step_index -= 1
        state.current_step_id = steps[state.current_step_index].id
        current_step = steps[state.current_step_index]

        # Remove the answer for this step
        if current_step.id in state.answers:
            del state.answers[current_step.id]

        return WizardResponse(
            message=current_step.question,
            wizard_state=state,
            current_step=current_step,
            can_go_back=state.current_step_index > 0,
            progress=state.current_step_index / state.total_steps,
        )

    async def cancel_wizard(self, wizard_id: str) -> None:
        """Cancel an active wizard session.

        Args:
            wizard_id: The wizard session ID
        """
        if wizard_id in self._active_wizards:
            del self._active_wizards[wizard_id]

    def get_active_wizard(self, wizard_id: str) -> Optional[Dict[str, Any]]:
        """Get an active wizard's data.

        Args:
            wizard_id: The wizard session ID

        Returns:
            Wizard data dict or None if not found
        """
        return self._active_wizards.get(wizard_id)

    async def _prepare_steps(
        self,
        steps: List[WizardStep],
        context: Optional[Dict[str, Any]]
    ) -> List[WizardStep]:
        """Prepare wizard steps with dynamic options.

        Args:
            steps: List of step definitions
            context: Optional context data

        Returns:
            List of prepared steps with populated options
        """
        prepared = []

        for step in steps:
            # Deep copy the step
            step_dict = step.model_dump()

            # Dynamically populate entity type options
            if step.id == "entity_type" and (not step.options or len(step.options) == 0):
                result = await self.db.execute(select(EntityType))
                entity_types = result.scalars().all()
                step_dict["options"] = [
                    WizardStepOption(
                        value=et.slug,
                        label=et.name,
                        description=et.description,
                        icon=et.icon or "mdi-file-document",
                    ).model_dump()
                    for et in entity_types
                ]

            # Pre-fill from context if available
            if context:
                if step.id == "entity" and context.get("current_entity_id"):
                    step_dict["default_value"] = context["current_entity_id"]

            prepared.append(WizardStep(**step_dict))

        return prepared

    def _validate_response(
        self,
        step: WizardStep,
        response: Any
    ) -> Optional[str]:
        """Validate a user response against step requirements.

        Args:
            step: The wizard step definition
            response: User's response value

        Returns:
            Error message string or None if valid
        """
        # Check required
        if step.required and (response is None or response == ""):
            return "Dieses Feld ist erforderlich."

        # Skip validation for optional empty responses
        if not step.required and (response is None or response == ""):
            return None

        # Type-specific validation
        if step.input_type == WizardInputType.SELECT:
            valid_values = [opt.value for opt in (step.options or [])]
            if response not in valid_values:
                return f"Bitte wähle eine der verfügbaren Optionen."

        if step.input_type == WizardInputType.TEXT or step.input_type == WizardInputType.TEXTAREA:
            if step.validation:
                min_len = step.validation.get("min_length", 0)
                max_len = step.validation.get("max_length", 10000)
                if len(str(response)) < min_len:
                    return f"Mindestens {min_len} Zeichen erforderlich."
                if len(str(response)) > max_len:
                    return f"Maximal {max_len} Zeichen erlaubt."

        if step.input_type == WizardInputType.NUMBER:
            try:
                num = float(response)
                if step.validation:
                    min_val = step.validation.get("min")
                    max_val = step.validation.get("max")
                    if min_val is not None and num < min_val:
                        return f"Wert muss mindestens {min_val} sein."
                    if max_val is not None and num > max_val:
                        return f"Wert darf maximal {max_val} sein."
            except (ValueError, TypeError):
                return "Bitte gib eine gültige Zahl ein."

        return None

    async def _execute_wizard(
        self,
        wizard_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the completed wizard and perform the action.

        Args:
            wizard_data: The wizard session data

        Returns:
            Result dict with success status and message
        """
        state = wizard_data["state"]
        definition = wizard_data["definition"]
        answers = state.answers

        try:
            if definition.type == "create_entity":
                return await self._execute_create_entity(answers)
            elif definition.type == "add_pain_point":
                return await self._execute_add_pain_point(answers)
            elif definition.type == "quick_search":
                return await self._execute_quick_search(answers)
            else:
                return {
                    "success": False,
                    "message": f"Unbekannter Wizard-Typ: {definition.type}",
                }
        except Exception as e:
            logger.error("wizard_execution_error", error=str(e), wizard_type=definition.type)
            return {
                "success": False,
                "message": f"Fehler bei der Ausführung: {str(e)}",
            }

    async def _execute_create_entity(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the create_entity wizard.

        Args:
            answers: Collected wizard answers

        Returns:
            Result dict
        """
        entity_type_slug = answers.get("entity_type")
        name = answers.get("name")
        description = answers.get("description")

        # Get entity type
        result = await self.db.execute(
            select(EntityType).where(EntityType.slug == entity_type_slug)
        )
        entity_type = result.scalar_one_or_none()

        if not entity_type:
            return {
                "success": False,
                "message": f"Entity-Typ nicht gefunden: {entity_type_slug}",
            }

        # Create entity
        from app.models import Entity
        from app.core.utils import generate_slug

        entity = Entity(
            type_id=entity_type.id,
            name=name,
            slug=generate_slug(name),
            description=description,
        )
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)

        return {
            "success": True,
            "message": f"Entity '{name}' erfolgreich erstellt!",
            "entity_id": str(entity.id),
            "entity_slug": entity.slug,
            "entity_type": entity_type_slug,
            "navigate_to": f"/entities/{entity_type_slug}/{entity.slug}",
        }

    async def _execute_add_pain_point(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the add_pain_point wizard.

        Args:
            answers: Collected wizard answers

        Returns:
            Result dict
        """
        entity_id = answers.get("entity")
        severity = answers.get("severity")
        description = answers.get("description")

        # Get entity
        result = await self.db.execute(
            select(Entity).where(Entity.id == entity_id)
        )
        entity = result.scalar_one_or_none()

        if not entity:
            return {
                "success": False,
                "message": "Entity nicht gefunden.",
            }

        # Get or create pain_point facet type
        result = await self.db.execute(
            select(FacetType).where(FacetType.slug == "pain_point")
        )
        facet_type = result.scalar_one_or_none()

        if not facet_type:
            return {
                "success": False,
                "message": "Pain Point Facet-Typ nicht gefunden.",
            }

        # Create facet value
        facet_value = FacetValue(
            entity_id=entity.id,
            facet_type_id=facet_type.id,
            value={
                "severity": severity,
                "description": description,
            },
            text_representation=description[:500] if description else "",
            confidence_score=1.0,
            source_type=FacetValueSourceType.MANUAL,
        )
        self.db.add(facet_value)
        await self.db.commit()

        return {
            "success": True,
            "message": f"Pain Point für '{entity.name}' hinzugefügt!",
            "entity_id": str(entity.id),
        }

    async def _execute_quick_search(self, answers: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the quick_search wizard.

        Args:
            answers: Collected wizard answers

        Returns:
            Result dict with search query
        """
        entity_type = answers.get("entity_type")
        search_term = answers.get("search_term", "")
        has_pain_points = answers.get("has_pain_points", "any")

        # Build search query string
        query_parts = []
        if search_term:
            query_parts.append(search_term)
        if entity_type:
            query_parts.append(f"type:{entity_type}")
        if has_pain_points == "yes":
            query_parts.append("has:pain_point")
        elif has_pain_points == "no":
            query_parts.append("-has:pain_point")

        query = " ".join(query_parts) if query_parts else "*"

        return {
            "success": True,
            "message": f"Suche gestartet: {query}",
            "search_query": query,
            "redirect_to": f"/smart-query?q={query}",
        }
