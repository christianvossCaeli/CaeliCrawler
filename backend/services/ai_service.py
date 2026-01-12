"""
Azure OpenAI Service for document analysis and extraction.

Provides AI-powered capabilities:
- Document summarization
- Information extraction
- Classification and categorization
- Named entity recognition
- Custom prompt-based analysis

IMPORTANT: This service now uses database-stored credentials via LLMClientService.
Environment variables are no longer used for API access.
"""

import json
import time
import uuid
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional, TypeVar

import structlog
from openai import AsyncAzureOpenAI, AsyncOpenAI
from pydantic import BaseModel, Field

from app.models.llm_usage import LLMProvider, LLMTaskType
from app.models.user_api_credentials import LLMPurpose
from app.utils.security import (
    SecurityConstants,
    log_security_event,
    sanitize_for_prompt,
    should_block_request,
)
from services.llm_usage_tracker import record_llm_usage, track_llm_usage

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()

T = TypeVar("T", bound=BaseModel)


class AnalysisType(str, Enum):
    """Types of document analysis."""

    SUMMARIZE = "summarize"
    EXTRACT = "extract"
    CLASSIFY = "classify"
    ENTITIES = "entities"
    CUSTOM = "custom"


# === Pydantic Models for Structured Output ===


class DocumentSummary(BaseModel):
    """Structured document summary."""

    title: str = Field(description="Document title or main topic")
    summary: str = Field(description="Concise summary (2-3 sentences)")
    key_points: list[str] = Field(description="List of 3-5 key points")
    document_type: str = Field(description="Type of document (e.g., Beschluss, Antrag, Bericht)")
    date_mentioned: str | None = Field(default=None, description="Primary date mentioned in document")
    relevance_score: float = Field(ge=0, le=1, description="Relevance score 0-1")


class ExtractedInformation(BaseModel):
    """Structured information extraction result."""

    topic: str = Field(description="Main topic or subject")
    entities: dict[str, list[str]] = Field(
        description="Named entities by category (persons, organizations, locations, dates)"
    )
    facts: list[str] = Field(description="Key facts extracted from the document")
    decisions: list[str] = Field(description="Decisions or resolutions mentioned")
    references: list[str] = Field(description="References to other documents or laws")
    amounts: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Monetary amounts or quantities mentioned",
    )
    deadlines: list[dict[str, str]] = Field(
        default_factory=list,
        description="Deadlines or dates for actions",
    )


class DocumentClassification(BaseModel):
    """Document classification result."""

    primary_category: str = Field(description="Primary category")
    secondary_categories: list[str] = Field(description="Secondary categories")
    keywords: list[str] = Field(description="Relevant keywords")
    sentiment: str = Field(description="Overall sentiment (positive, negative, neutral)")
    urgency: str = Field(description="Urgency level (high, medium, low)")
    target_audience: list[str] = Field(description="Intended audience")
    confidence: float = Field(ge=0, le=1, description="Classification confidence 0-1")


class NamedEntities(BaseModel):
    """Named entity recognition result."""

    persons: list[dict[str, str]] = Field(
        description="Persons mentioned with their roles",
    )
    organizations: list[dict[str, str]] = Field(
        description="Organizations mentioned with their type",
    )
    locations: list[dict[str, str]] = Field(
        description="Locations with context",
    )
    dates: list[dict[str, str]] = Field(
        description="Dates with context",
    )
    laws_regulations: list[str] = Field(
        description="Laws, regulations, or legal references",
    )
    projects: list[str] = Field(
        description="Projects or initiatives mentioned",
    )


class WindPowerAnalysis(BaseModel):
    """Specialized analysis for wind power related documents."""

    is_relevant: bool = Field(description="Is this document relevant to wind power?")
    relevance_type: str | None = Field(
        default=None,
        description="Type of relevance (Genehmigung, Einschränkung, Förderung, Planung, etc.)",
    )
    location: str | None = Field(default=None, description="Location/region mentioned")
    restrictions: list[str] = Field(
        default_factory=list,
        description="Any restrictions or limitations mentioned",
    )
    permits: list[str] = Field(
        default_factory=list,
        description="Permits or approvals mentioned",
    )
    timeline: str | None = Field(default=None, description="Timeline or deadlines")
    stakeholders: list[str] = Field(
        default_factory=list,
        description="Stakeholders involved",
    )
    key_findings: list[str] = Field(
        default_factory=list,
        description="Key findings relevant to wind power development",
    )
    sentiment_toward_wind: str = Field(
        default="neutral",
        description="Sentiment toward wind power (positive, negative, neutral)",
    )


class CustomExtractionResult(BaseModel):
    """Generic extraction result for custom prompts."""

    success: bool = Field(description="Whether extraction was successful")
    extracted_data: dict[str, Any] = Field(description="Extracted data as key-value pairs")
    confidence: float = Field(ge=0, le=1, description="Extraction confidence")
    notes: str | None = Field(default=None, description="Additional notes or warnings")


# === AI Service ===


class TaskType(str, Enum):
    """Types of AI tasks with different model requirements."""

    CHAT = "chat"  # General chat/summarization
    EXTRACTION = "extraction"  # Information extraction from text
    PDF = "pdf"  # PDF document analysis
    WEB = "web"  # Website content extraction
    CLASSIFICATION = "classification"  # Document classification
    EMBEDDINGS = "embeddings"  # Text embeddings


class AIService:
    """
    Azure OpenAI service for document analysis.

    IMPORTANT: This service now uses database-stored credentials.
    A database session is REQUIRED for all operations.

    Example usage:
        async with async_session_factory() as session:
            service = AIService(session)

            # Summarize a document (uses chat deployment)
            summary = await service.summarize(document_text)

            # Extract structured information (uses extraction deployment)
            info = await service.extract_information(document_text)

            # Generate embeddings (uses embeddings deployment)
            embeddings = await service.generate_embeddings(["text1", "text2"])

            # Custom analysis with specific task type
            result = await service.analyze_custom(
                document_text,
                prompt="Extract deadlines",
                task_type=TaskType.PDF  # Use PDF-optimized model
            )
    """

    def __init__(
        self,
        session: "AsyncSession | None" = None,
    ):
        """
        Initialize AIService.

        Args:
            session: Database session for loading credentials.
                     Required for all API calls.
        """
        self.session = session
        self._client: AsyncAzureOpenAI | AsyncOpenAI | None = None
        self._config: dict[str, Any] | None = None
        self._llm_service = None
        self.logger = logger.bind(service="AIService")

        # Token limits (GPT-4 context window)
        self.max_input_tokens = 120000
        self.max_output_tokens = 4096

    def get_deployment(self, task_type: TaskType = TaskType.CHAT) -> str:
        """Get the appropriate deployment for a task type."""
        if not self._config:
            raise ValueError("Client not initialized - call an async method first")

        from services.llm_client_service import LLMClientService

        service = LLMClientService(self.session)
        return service.get_model_name(self._config, for_embeddings=(task_type == TaskType.EMBEDDINGS))

    async def _get_client(self) -> AsyncAzureOpenAI | AsyncOpenAI:
        """Get or create OpenAI client using database credentials."""
        if self._client is None:
            if not self.session:
                raise ValueError(
                    "Database session required for AIService. "
                    "Please configure API credentials in /admin/api-credentials."
                )

            from services.llm_client_service import LLMClientService

            self._llm_service = LLMClientService(self.session)
            self._client, self._config = await self._llm_service.get_system_client(
                LLMPurpose.DOCUMENT_ANALYSIS
            )

            if not self._client or not self._config:
                raise ValueError(
                    "No LLM credentials configured in database. "
                    "Please configure API credentials in /admin/api-credentials."
                )

        return self._client

    @property
    def embeddings_deployment(self) -> str:
        """Get embeddings deployment name."""
        if not self._config:
            raise ValueError("Client not initialized - call _get_client() first")
        from services.llm_client_service import LLMClientService

        service = LLMClientService(self.session)
        return service.get_model_name(self._config, for_embeddings=True)

    @property
    def default_deployment(self) -> str:
        """Get default deployment name."""
        if not self._config:
            raise ValueError("Client not initialized - call _get_client() first")
        from services.llm_client_service import LLMClientService

        service = LLMClientService(self.session)
        return service.get_model_name(self._config, for_embeddings=False)

    async def close(self):
        """Close the client."""
        if self._client:
            await self._client.close()
            self._client = None

    # === Embeddings ===

    async def generate_embeddings(
        self,
        texts: list[str],
        batch_size: int = 100,
        dimensions: int = 1536,
        category_id: Optional["uuid.UUID"] = None,
    ) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once
            dimensions: Number of dimensions for the embedding (default: 1536)
                        text-embedding-3-large supports up to 3072, but pgvector
                        indexes are limited to 2000 dimensions.
            category_id: Optional category ID for tracking

        Returns:
            List of embedding vectors
        """
        client = await self._get_client()
        all_embeddings = []
        total_tokens = 0

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            async with track_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=self.embeddings_deployment,
                task_type=LLMTaskType.EMBEDDING,
                task_name="generate_embeddings",
                category_id=category_id,
                metadata={"batch_size": len(batch), "dimensions": dimensions},
            ) as usage_ctx:
                try:
                    response = await client.embeddings.create(
                        model=self.embeddings_deployment,
                        input=batch,
                        dimensions=dimensions,
                    )

                    # Record token usage
                    if response.usage:
                        usage_ctx.prompt_tokens = response.usage.prompt_tokens
                        usage_ctx.total_tokens = response.usage.total_tokens
                        total_tokens += response.usage.total_tokens

                    batch_embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(batch_embeddings)

                    self.logger.debug(
                        "Generated embeddings",
                        batch_size=len(batch),
                        total=len(all_embeddings),
                        dimensions=dimensions,
                    )
                except Exception as e:
                    self.logger.error("Embeddings generation failed", error=str(e))
                    raise

        return all_embeddings

    async def generate_embedding(self, text: str, dimensions: int = 1536) -> list[float]:
        """Generate embedding for a single text."""
        embeddings = await self.generate_embeddings([text], dimensions=dimensions)
        return embeddings[0]

    def _estimate_tokens(self, text: str) -> int:
        """Rough estimate of token count."""
        # Average ~4 characters per token for German text
        return len(text) // 4

    def _truncate_text(self, text: str, max_tokens: int = 100000) -> str:
        """Truncate text to fit within token limit."""
        estimated_tokens = self._estimate_tokens(text)
        if estimated_tokens <= max_tokens:
            return text

        # Truncate to approximate token limit
        max_chars = max_tokens * 4
        return text[:max_chars] + "\n\n[... Text truncated due to length ...]"

    # === High-Level Analysis Methods ===

    async def summarize(
        self,
        text: str,
        context: str | None = None,
    ) -> DocumentSummary:
        """
        Generate a structured summary of a document.

        Args:
            text: Document text to summarize
            context: Optional context about the document source
        """
        system_prompt = """Du bist ein Experte für die Analyse deutscher Verwaltungsdokumente.
Erstelle eine strukturierte Zusammenfassung des Dokuments.
Fokussiere auf die wichtigsten Informationen und Entscheidungen.

Verwende exakt dieses JSON-Schema für deine Antwort:
{
  "title": "Titel oder Hauptthema des Dokuments",
  "summary": "Kurze Zusammenfassung (2-3 Sätze)",
  "key_points": ["Punkt 1", "Punkt 2", "Punkt 3"],
  "document_type": "Dokumenttyp (z.B. Beschluss, Antrag, Bericht)",
  "date_mentioned": "Datum falls erwähnt oder null",
  "relevance_score": 0.8
}"""

        user_prompt = f"""Analysiere das folgende Dokument und erstelle eine strukturierte Zusammenfassung:

{context if context else ""}

DOKUMENT:
{self._truncate_text(text)}"""

        return await self._analyze_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_model=DocumentSummary,
        )

    async def extract_information(
        self,
        text: str,
        focus_areas: list[str] | None = None,
    ) -> ExtractedInformation:
        """
        Extract structured information from a document.

        Args:
            text: Document text
            focus_areas: Optional list of areas to focus on
        """
        focus_instruction = ""
        if focus_areas:
            focus_instruction = f"\nFokussiere besonders auf: {', '.join(focus_areas)}"

        system_prompt = f"""Du bist ein Experte für die Informationsextraktion aus deutschen Verwaltungsdokumenten.
Extrahiere alle relevanten Informationen strukturiert.{focus_instruction}
Antworte immer auf Deutsch."""

        user_prompt = f"""Extrahiere alle relevanten Informationen aus dem folgenden Dokument:

DOKUMENT:
{self._truncate_text(text)}"""

        return await self._analyze_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_model=ExtractedInformation,
        )

    async def classify(
        self,
        text: str,
        categories: list[str] | None = None,
    ) -> DocumentClassification:
        """
        Classify a document into categories.

        Args:
            text: Document text
            categories: Optional predefined categories to choose from
        """
        category_instruction = ""
        if categories:
            category_instruction = f"\nVerfügbare Kategorien: {', '.join(categories)}"

        system_prompt = f"""Du bist ein Experte für die Klassifizierung deutscher Verwaltungsdokumente.
Analysiere das Dokument und ordne es passenden Kategorien zu.{category_instruction}
Antworte immer auf Deutsch."""

        user_prompt = f"""Klassifiziere das folgende Dokument:

DOKUMENT:
{self._truncate_text(text)}"""

        return await self._analyze_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_model=DocumentClassification,
        )

    async def extract_entities(self, text: str) -> NamedEntities:
        """
        Extract named entities from a document.

        Args:
            text: Document text
        """
        system_prompt = """Du bist ein Experte für Named Entity Recognition in deutschen Verwaltungsdokumenten.
Extrahiere alle benannten Entitäten mit ihrem Kontext.
Antworte immer auf Deutsch."""

        user_prompt = f"""Extrahiere alle benannten Entitäten aus dem folgenden Dokument:

DOKUMENT:
{self._truncate_text(text)}"""

        return await self._analyze_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_model=NamedEntities,
        )

    async def analyze_wind_power(
        self,
        text: str,
        municipality: str | None = None,
    ) -> WindPowerAnalysis:
        """
        Specialized analysis for wind power related documents.

        Args:
            text: Document text
            municipality: Optional municipality name for context
        """
        context = ""
        if municipality:
            context = f"\nKontext: Dokument aus {municipality}"

        system_prompt = f"""Du bist ein Experte für die Analyse von Dokumenten im Zusammenhang mit Windenergie in Deutschland.
Analysiere das Dokument auf Relevanz für Windkraftprojekte.{context}
Fokussiere auf:
- Genehmigungen und Einschränkungen
- Flächennutzungspläne
- Abstände und Höhenbegrenzungen
- Naturschutzauflagen
- Gemeinderatsbeschlüsse zu Windenergie

Verwende exakt dieses JSON-Schema für deine Antwort:
{{
  "is_relevant": true,
  "relevance_type": "Genehmigung|Einschränkung|Förderung|Planung|Information|null",
  "location": "Ortsangabe oder null",
  "restrictions": ["Einschränkung 1", "Einschränkung 2"],
  "permits": ["Genehmigung 1"],
  "timeline": "Zeitrahmen oder null",
  "stakeholders": ["Beteiligte 1", "Beteiligte 2"],
  "key_findings": ["Erkenntnis 1", "Erkenntnis 2"],
  "sentiment_toward_wind": "positive|negative|neutral"
}}"""

        user_prompt = f"""Analysiere das folgende Dokument hinsichtlich seiner Relevanz für Windenergie:

DOKUMENT:
{self._truncate_text(text)}"""

        return await self._analyze_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_model=WindPowerAnalysis,
        )

    async def analyze_custom(
        self,
        text: str,
        prompt: str,
        output_model: type[T] = CustomExtractionResult,
        system_context: str | None = None,
    ) -> T:
        """
        Custom analysis with user-defined prompt.

        Security: Both prompt and text are sanitized to prevent prompt injection.

        Args:
            text: Document text
            prompt: Custom extraction prompt
            output_model: Pydantic model for structured output
            system_context: Optional system context

        Raises:
            ValueError: If prompt contains high-risk injection patterns
        """
        # Sanitize the custom prompt
        prompt_result = sanitize_for_prompt(prompt, max_length=SecurityConstants.MAX_PROMPT_LENGTH)
        if should_block_request(prompt_result.risk_level):
            log_security_event(
                event_type="custom_prompt_injection_blocked",
                risk_level=prompt_result.risk_level,
                details={
                    "detected_risks": prompt_result.detected_risks,
                    "prompt_preview": prompt[:100] if prompt else "",
                },
            )
            raise ValueError("Sicherheitsprüfung fehlgeschlagen: Der Prompt enthält unzulässige Anweisungen.")

        safe_prompt = prompt_result.sanitized_text

        system_prompt = (
            system_context
            or """Du bist ein Experte für die Analyse deutscher Dokumente.
Befolge die Anweisungen des Nutzers genau.
Antworte immer auf Deutsch."""
        )

        user_prompt = f"""{safe_prompt}

DOKUMENT:
{self._truncate_text(text)}"""

        return await self._analyze_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_model=output_model,
        )

    # === Batch Processing ===

    async def analyze_batch(
        self,
        documents: list[dict[str, str]],
        analysis_type: AnalysisType = AnalysisType.SUMMARIZE,
        custom_prompt: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Analyze multiple documents in batch.

        Args:
            documents: List of dicts with 'id' and 'text' keys
            analysis_type: Type of analysis to perform
            custom_prompt: Custom prompt for CUSTOM analysis type
        """
        results = []

        for doc in documents:
            try:
                doc_id = doc.get("id", "unknown")
                text = doc.get("text", "")

                if not text:
                    results.append(
                        {
                            "id": doc_id,
                            "error": "Empty document text",
                            "success": False,
                        }
                    )
                    continue

                if analysis_type == AnalysisType.SUMMARIZE:
                    result = await self.summarize(text)
                elif analysis_type == AnalysisType.EXTRACT:
                    result = await self.extract_information(text)
                elif analysis_type == AnalysisType.CLASSIFY:
                    result = await self.classify(text)
                elif analysis_type == AnalysisType.ENTITIES:
                    result = await self.extract_entities(text)
                elif analysis_type == AnalysisType.CUSTOM and custom_prompt:
                    result = await self.analyze_custom(text, custom_prompt)
                else:
                    result = await self.summarize(text)

                results.append(
                    {
                        "id": doc_id,
                        "result": result.model_dump(),
                        "success": True,
                    }
                )

            except Exception as e:
                self.logger.error("Batch analysis failed", doc_id=doc_id, error=str(e))
                results.append(
                    {
                        "id": doc_id,
                        "error": str(e),
                        "success": False,
                    }
                )

        return results

    # === Low-Level Methods ===

    async def _analyze_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        output_model: type[T],
        task_type: TaskType = TaskType.CHAT,
        document_id: Optional["uuid.UUID"] = None,
        category_id: Optional["uuid.UUID"] = None,
    ) -> T:
        """
        Perform structured analysis with Pydantic model output.

        Uses OpenAI's structured output feature for reliable JSON responses.

        Args:
            system_prompt: System context prompt
            user_prompt: User input prompt
            output_model: Pydantic model for structured output
            task_type: Type of task (determines which deployment to use)
            document_id: Optional document ID for tracking
            category_id: Optional category ID for tracking
        """
        client = await self._get_client()
        deployment = self.get_deployment(task_type)

        # Map TaskType to LLMTaskType for tracking
        task_type_map = {
            TaskType.SUMMARIZE: LLMTaskType.SUMMARIZE,
            TaskType.EXTRACT: LLMTaskType.EXTRACT,
            TaskType.CLASSIFY: LLMTaskType.CLASSIFY,
            TaskType.CHAT: LLMTaskType.CHAT,
            TaskType.PDF: LLMTaskType.EXTRACT,
            TaskType.WEB: LLMTaskType.EXTRACT,
        }
        llm_task_type = task_type_map.get(task_type, LLMTaskType.CUSTOM)

        self.logger.debug(
            "Running structured analysis",
            task_type=task_type.value,
            deployment=deployment,
        )

        async with track_llm_usage(
            provider=LLMProvider.AZURE_OPENAI,
            model=deployment,
            task_type=llm_task_type,
            task_name=f"analyze_{output_model.__name__}",
            document_id=document_id,
            category_id=category_id,
        ) as usage_ctx:
            try:
                # Azure requires "json" in the prompt when using json_object response_format
                json_system_prompt = f"{system_prompt}\n\nAntworte ausschließlich im JSON-Format."

                # Use response_format for structured output
                response = await client.chat.completions.create(
                    model=deployment,
                    messages=[
                        {"role": "system", "content": json_system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,  # Lower temperature for more consistent extraction
                    max_tokens=self.max_output_tokens,
                )

                # Record token usage
                if response.usage:
                    usage_ctx.prompt_tokens = response.usage.prompt_tokens
                    usage_ctx.completion_tokens = response.usage.completion_tokens
                    usage_ctx.total_tokens = response.usage.total_tokens

                content = response.choices[0].message.content

                # Parse JSON response
                try:
                    data = json.loads(content)
                    return output_model.model_validate(data)
                except json.JSONDecodeError as e:
                    self.logger.error("JSON parse error", error=str(e), content=content[:500])
                    raise ValueError(f"Failed to parse AI response: {e}") from None

            except Exception as e:
                self.logger.error("AI analysis failed", error=str(e), task_type=task_type.value)
                raise

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        task_type: TaskType = TaskType.CHAT,
        document_id: Optional["uuid.UUID"] = None,
        category_id: Optional["uuid.UUID"] = None,
        user_id: Optional["uuid.UUID"] = None,
    ) -> str:
        """
        Generate unstructured text response.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Creativity level (0-1)
            max_tokens: Maximum response tokens
            task_type: Type of task (determines which deployment to use)
            document_id: Optional document ID for tracking
            category_id: Optional category ID for tracking
            user_id: Optional user ID for tracking
        """
        client = await self._get_client()
        deployment = self.get_deployment(task_type)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with track_llm_usage(
            provider=LLMProvider.AZURE_OPENAI,
            model=deployment,
            task_type=LLMTaskType.CHAT,
            task_name="generate_text",
            document_id=document_id,
            category_id=category_id,
            user_id=user_id,
        ) as usage_ctx:
            response = await client.chat.completions.create(
                model=deployment,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Record token usage
            if response.usage:
                usage_ctx.prompt_tokens = response.usage.prompt_tokens
                usage_ctx.completion_tokens = response.usage.completion_tokens
                usage_ctx.total_tokens = response.usage.total_tokens

            return response.choices[0].message.content

    async def check_relevance(
        self,
        text: str,
        topic: str,
        threshold: float = 0.5,
        task_type: TaskType = TaskType.CLASSIFICATION,
    ) -> tuple[bool, float, str]:
        """
        Quick relevance check for a topic.

        Args:
            text: Document text
            topic: Topic to check relevance for
            threshold: Minimum relevance score (0-1)
            task_type: Type of task (determines which deployment to use)

        Returns:
            Tuple of (is_relevant, score, reason)
        """
        client = await self._get_client()
        deployment = self.get_deployment(task_type)

        # Use a shorter prompt for quick checking (must include "json" for Azure)
        prompt = f"""Bewerte die Relevanz des Dokuments für das Thema "{topic}".
Antworte ausschließlich im JSON-Format mit diesem Schema: {{"relevant": true/false, "score": 0.0-1.0, "reason": "kurze Begründung"}}

DOKUMENT (erste 2000 Zeichen):
{text[:2000]}"""

        start_time = time.time()
        try:
            response = await client.chat.completions.create(
                model=deployment,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=200,
            )

            if response.usage:
                await record_llm_usage(
                    provider=LLMProvider.AZURE_OPENAI,
                    model=deployment,
                    task_type=LLMTaskType.CLASSIFY,
                    task_name="check_relevance",
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                    duration_ms=int((time.time() - start_time) * 1000),
                    is_error=False,
                )

            result = json.loads(response.choices[0].message.content)
            score = float(result.get("score", 0))
            is_relevant = result.get("relevant", False) and score >= threshold
            reason = result.get("reason", "")
            return is_relevant, score, reason

        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error("Relevance check parse error", error=str(e))
            raise RuntimeError(
                f"KI-Service Fehler: Relevanz-Antwort konnte nicht verarbeitet werden - {str(e)}"
            ) from None
        except Exception as e:
            await record_llm_usage(
                provider=LLMProvider.AZURE_OPENAI,
                model=deployment,
                task_type=LLMTaskType.CLASSIFY,
                task_name="check_relevance",
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                duration_ms=int((time.time() - start_time) * 1000),
                is_error=True,
                error_message=str(e),
            )
            raise


def get_ai_service(session: "AsyncSession") -> AIService:
    """
    Create AIService with database session.

    Note: AIService is no longer a singleton since it requires a database session.

    Args:
        session: Database session for loading credentials

    Returns:
        AIService instance
    """
    return AIService(session)
