"""Summary Export Service.

Handles export of custom summaries to PDF and Excel formats.
Uses WeasyPrint for PDF generation and openpyxl for Excel.
"""

import io
import re
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from jinja2 import Environment, BaseLoader


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """
    Sanitize a filename to prevent path traversal and injection attacks.

    Args:
        filename: The original filename (without extension)
        max_length: Maximum length of the sanitized filename

    Returns:
        A safe filename string
    """
    if not filename:
        return "export"

    # Normalize unicode characters
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("ascii", "ignore").decode("ascii")

    # Remove path traversal attempts
    filename = filename.replace("..", "")
    filename = filename.replace("/", "_")
    filename = filename.replace("\\", "_")

    # Remove header injection characters
    filename = filename.replace("\n", "")
    filename = filename.replace("\r", "")
    filename = filename.replace("\x00", "")

    # Remove other potentially dangerous characters
    # Keep only alphanumeric, spaces, hyphens, underscores
    filename = re.sub(r'[^\w\s\-]', '', filename)

    # Replace multiple spaces/underscores with single
    filename = re.sub(r'[\s_]+', '_', filename)

    # Strip leading/trailing underscores
    filename = filename.strip('_')

    # Truncate to max length
    if len(filename) > max_length:
        filename = filename[:max_length].rstrip('_')

    return filename or "export"


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import CustomSummary, SummaryExecution, SummaryWidget
from app.models.summary_execution import ExecutionStatus

logger = structlog.get_logger(__name__)

# PDF Template using HTML/CSS (rendered by WeasyPrint)
PDF_TEMPLATE = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>{{ summary.name }}</title>
    <style>
        @page {
            size: A4;
            margin: 2cm;
            @bottom-center {
                content: "Seite " counter(page) " von " counter(pages);
                font-size: 10px;
                color: #666;
            }
        }

        * {
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            font-size: 11pt;
            line-height: 1.5;
            color: #333;
            margin: 0;
            padding: 0;
        }

        .header {
            border-bottom: 2px solid #113534;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }

        .header h1 {
            color: #113534;
            font-size: 24pt;
            margin: 0 0 8px 0;
        }

        .header .subtitle {
            color: #666;
            font-size: 12pt;
        }

        .meta {
            background: #f5f5f5;
            padding: 10px 15px;
            border-radius: 4px;
            margin-bottom: 20px;
            font-size: 10pt;
            color: #666;
        }

        .meta span {
            margin-right: 20px;
        }

        .widget {
            page-break-inside: avoid;
            margin-bottom: 25px;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
        }

        .widget-header {
            background: #113534;
            color: white;
            padding: 10px 15px;
        }

        .widget-header h2 {
            margin: 0;
            font-size: 14pt;
        }

        .widget-header .subtitle {
            font-size: 10pt;
            opacity: 0.8;
            margin-top: 3px;
        }

        .widget-content {
            padding: 15px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 10pt;
        }

        th {
            background: #f0f0f0;
            text-align: left;
            padding: 8px;
            border-bottom: 2px solid #ddd;
            font-weight: 600;
        }

        td {
            padding: 8px;
            border-bottom: 1px solid #eee;
        }

        tr:nth-child(even) {
            background: #fafafa;
        }

        .stat-card {
            text-align: center;
            padding: 20px;
        }

        .stat-value {
            font-size: 36pt;
            font-weight: bold;
            color: #113534;
        }

        .stat-label {
            font-size: 12pt;
            color: #666;
            margin-top: 5px;
        }

        .text-widget {
            white-space: pre-wrap;
        }

        .footer {
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid #ddd;
            font-size: 9pt;
            color: #999;
            text-align: center;
        }

        .no-data {
            color: #999;
            font-style: italic;
            text-align: center;
            padding: 20px;
        }

        .chart-placeholder {
            background: #f0f0f0;
            padding: 40px;
            text-align: center;
            color: #666;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ summary.name }}</h1>
        {% if summary.description %}
        <div class="subtitle">{{ summary.description }}</div>
        {% endif %}
    </div>

    <div class="meta">
        <span><strong>Erstellt:</strong> {{ export_date }}</span>
        {% if last_executed %}
        <span><strong>Letzte Aktualisierung:</strong> {{ last_executed }}</span>
        {% endif %}
        <span><strong>Widgets:</strong> {{ widgets|length }}</span>
    </div>

    {% for widget in widgets %}
    <div class="widget">
        <div class="widget-header">
            <h2>{{ widget.title }}</h2>
            {% if widget.subtitle %}
            <div class="subtitle">{{ widget.subtitle }}</div>
            {% endif %}
        </div>
        <div class="widget-content">
            {% set widget_data = cached_data.get('widget_' ~ widget.id) %}

            {% if widget.widget_type == 'stat_card' %}
                {% if widget_data and widget_data.data %}
                <div class="stat-card">
                    <div class="stat-value">{{ widget_data.data[0].value if widget_data.data else '-' }}</div>
                    <div class="stat-label">{{ widget.title }}</div>
                </div>
                {% else %}
                <div class="no-data">Keine Daten verfuegbar</div>
                {% endif %}

            {% elif widget.widget_type == 'text' %}
                <div class="text-widget">{{ widget_data.data[0].text if widget_data and widget_data.data else 'Kein Text' }}</div>

            {% elif widget.widget_type in ['bar_chart', 'line_chart', 'pie_chart'] %}
                <div class="chart-placeholder">
                    Diagramm-Visualisierung ({{ widget.widget_type }})
                    <br>
                    <small>Bitte verwenden Sie die interaktive Ansicht fuer Diagramme</small>
                </div>
                {% if widget_data and widget_data.data %}
                <table style="margin-top: 15px;">
                    <thead>
                        <tr>
                            <th>Name</th>
                            {% for key in widget_data.data[0].facets.keys() if widget_data.data[0].facets %}
                            <th>{{ key }}</th>
                            {% endfor %}
                        </tr>
                    </thead>
                    <tbody>
                        {% for row in widget_data.data[:20] %}
                        <tr>
                            <td>{{ row.name }}</td>
                            {% for key, val in row.facets.items() %}
                            <td>{{ val.value if val else '-' }}</td>
                            {% endfor %}
                        </tr>
                        {% endfor %}
                        {% if widget_data.total > 20 %}
                        <tr>
                            <td colspan="10" style="text-align: center; font-style: italic; color: #666;">
                                ... und {{ widget_data.total - 20 }} weitere Eintraege
                            </td>
                        </tr>
                        {% endif %}
                    </tbody>
                </table>
                {% endif %}

            {% elif widget.widget_type == 'table' %}
                {% if widget_data and widget_data.data %}
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            {% if widget_data.data[0].facets %}
                            {% for key in widget_data.data[0].facets.keys() %}
                            <th>{{ key }}</th>
                            {% endfor %}
                            {% endif %}
                        </tr>
                    </thead>
                    <tbody>
                        {% for row in widget_data.data[:50] %}
                        <tr>
                            <td>{{ row.name }}</td>
                            {% if row.facets %}
                            {% for key, val in row.facets.items() %}
                            <td>{{ val.value if val else '-' }}</td>
                            {% endfor %}
                            {% endif %}
                        </tr>
                        {% endfor %}
                        {% if widget_data.total > 50 %}
                        <tr>
                            <td colspan="10" style="text-align: center; font-style: italic; color: #666;">
                                ... und {{ widget_data.total - 50 }} weitere Eintraege
                            </td>
                        </tr>
                        {% endif %}
                    </tbody>
                </table>
                {% else %}
                <div class="no-data">Keine Daten verfuegbar</div>
                {% endif %}

            {% elif widget.widget_type == 'comparison' %}
                {% if widget_data and widget_data.data %}
                <table>
                    <thead>
                        <tr>
                            <th>Vergleichsmerkmal</th>
                            {% for item in widget_data.data[:5] %}
                            <th>{{ item.name }}</th>
                            {% endfor %}
                        </tr>
                    </thead>
                    <tbody>
                        {% if widget_data.data[0].facets %}
                        {% for facet_key in widget_data.data[0].facets.keys() %}
                        <tr>
                            <td><strong>{{ facet_key }}</strong></td>
                            {% for item in widget_data.data[:5] %}
                            <td>{{ item.facets[facet_key].value if item.facets.get(facet_key) else '-' }}</td>
                            {% endfor %}
                        </tr>
                        {% endfor %}
                        {% endif %}
                    </tbody>
                </table>
                {% else %}
                <div class="no-data">Keine Vergleichsdaten verfuegbar</div>
                {% endif %}

            {% elif widget.widget_type == 'map' %}
                <div class="chart-placeholder">
                    Karten-Visualisierung
                    <br>
                    <small>Bitte verwenden Sie die interaktive Ansicht fuer Karten</small>
                </div>

            {% else %}
                {% if widget_data and widget_data.data %}
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Daten</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for row in widget_data.data[:20] %}
                        <tr>
                            <td>{{ row.name }}</td>
                            <td>{{ row.facets | tojson if row.facets else '-' }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <div class="no-data">Keine Daten verfuegbar</div>
                {% endif %}
            {% endif %}
        </div>
    </div>
    {% endfor %}

    <div class="footer">
        Generiert von CaeliCrawler am {{ export_date }}
    </div>
</body>
</html>
"""


class SummaryExportService:
    """
    Handles export of custom summaries to various formats.

    Supports:
    - PDF export using WeasyPrint
    - Excel export using openpyxl
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.jinja_env = Environment(loader=BaseLoader())

    async def export_to_pdf(
        self,
        summary_id: UUID,
        execution_id: Optional[UUID] = None,
    ) -> bytes:
        """
        Export summary to PDF format.

        Args:
            summary_id: ID of the summary to export
            execution_id: Optional specific execution to export
                         (defaults to latest completed)

        Returns:
            PDF file as bytes

        Raises:
            ValueError: If summary not found
            ImportError: If WeasyPrint is not installed
        """
        logger.info(
            "pdf_export_started",
            summary_id=str(summary_id),
            execution_id=str(execution_id) if execution_id else None,
        )

        try:
            from weasyprint import HTML
        except ImportError:
            logger.error("WeasyPrint not installed")
            raise ImportError(
                "WeasyPrint is required for PDF export. "
                "Install it with: pip install weasyprint"
            )

        # Load summary with widgets
        result = await self.session.execute(
            select(CustomSummary)
            .options(selectinload(CustomSummary.widgets))
            .where(CustomSummary.id == summary_id)
        )
        summary = result.scalar_one_or_none()

        if not summary:
            raise ValueError(f"Summary {summary_id} not found")

        # Get execution data
        execution = await self._get_execution(summary_id, execution_id)
        cached_data = execution.cached_data if execution else {}

        # Sort widgets by position
        widgets = sorted(
            summary.widgets,
            key=lambda w: (w.position_y or 0, w.position_x or 0)
        )

        # Render template
        template = self.jinja_env.from_string(PDF_TEMPLATE)
        html_content = template.render(
            summary=summary,
            widgets=widgets,
            cached_data=cached_data,
            export_date=datetime.now().strftime("%d.%m.%Y %H:%M"),
            last_executed=execution.completed_at.strftime("%d.%m.%Y %H:%M") if execution and execution.completed_at else None,
        )

        # Generate PDF
        html = HTML(string=html_content)
        pdf_bytes = html.write_pdf()

        logger.info(
            "summary_exported_pdf",
            summary_id=str(summary_id),
            size_bytes=len(pdf_bytes),
        )

        return pdf_bytes

    async def export_to_excel(
        self,
        summary_id: UUID,
        execution_id: Optional[UUID] = None,
    ) -> bytes:
        """
        Export summary to Excel format.

        Each widget becomes a separate sheet in the workbook.

        Args:
            summary_id: ID of the summary to export
            execution_id: Optional specific execution to export

        Returns:
            Excel file (.xlsx) as bytes

        Raises:
            ValueError: If summary not found
            ImportError: If openpyxl is not installed
        """
        logger.info(
            "excel_export_started",
            summary_id=str(summary_id),
            execution_id=str(execution_id) if execution_id else None,
        )

        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
        except ImportError:
            logger.error("openpyxl not installed")
            raise ImportError(
                "openpyxl is required for Excel export. "
                "Install it with: pip install openpyxl"
            )

        # Load summary with widgets
        result = await self.session.execute(
            select(CustomSummary)
            .options(selectinload(CustomSummary.widgets))
            .where(CustomSummary.id == summary_id)
        )
        summary = result.scalar_one_or_none()

        if not summary:
            raise ValueError(f"Summary {summary_id} not found")

        # Get execution data
        execution = await self._get_execution(summary_id, execution_id)
        cached_data = execution.cached_data if execution else {}

        # Create workbook
        wb = Workbook()

        # Style definitions
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="113534", end_color="113534", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # Create overview sheet
        overview_sheet = wb.active
        overview_sheet.title = "Uebersicht"

        overview_data = [
            ["Zusammenfassung", summary.name],
            ["Beschreibung", summary.description or "-"],
            ["Exportiert am", datetime.now().strftime("%d.%m.%Y %H:%M")],
            ["Letzte Aktualisierung", execution.completed_at.strftime("%d.%m.%Y %H:%M") if execution and execution.completed_at else "-"],
            ["Anzahl Widgets", len(summary.widgets)],
            ["Status", summary.status.value],
        ]

        for row_idx, (label, value) in enumerate(overview_data, start=1):
            overview_sheet.cell(row=row_idx, column=1, value=label).font = Font(bold=True)
            overview_sheet.cell(row=row_idx, column=2, value=value)

        overview_sheet.column_dimensions['A'].width = 25
        overview_sheet.column_dimensions['B'].width = 50

        # Sort widgets by position
        widgets = sorted(
            summary.widgets,
            key=lambda w: (w.position_y or 0, w.position_x or 0)
        )

        # Create sheet for each widget
        for idx, widget in enumerate(widgets):
            widget_key = f"widget_{widget.id}"
            widget_data = cached_data.get(widget_key, {})
            data = widget_data.get("data", [])

            # Create sheet with sanitized name
            sheet_name = self._sanitize_sheet_name(f"{idx + 1}. {widget.title}")
            ws = wb.create_sheet(title=sheet_name)

            # Widget title
            ws.cell(row=1, column=1, value=widget.title).font = Font(bold=True, size=14)
            if widget.subtitle:
                ws.cell(row=2, column=1, value=widget.subtitle).font = Font(italic=True, color="666666")

            start_row = 4

            if not data:
                ws.cell(row=start_row, column=1, value="Keine Daten verfuegbar")
                continue

            # Determine columns based on widget type
            if widget.widget_type == "stat_card":
                ws.cell(row=start_row, column=1, value="Wert")
                ws.cell(row=start_row, column=2, value=data[0].get("value", "-"))
                ws.cell(row=start_row, column=1).font = Font(bold=True)
                continue

            if widget.widget_type == "text":
                ws.cell(row=start_row, column=1, value=data[0].get("text", ""))
                continue

            # Table-like widgets
            # Get all facet keys from first row
            facet_keys = []
            if data and data[0].get("facets"):
                facet_keys = list(data[0]["facets"].keys())

            # Headers
            headers = ["Name"] + facet_keys
            for col_idx, header in enumerate(headers, start=1):
                cell = ws.cell(row=start_row, column=col_idx, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = header_alignment
                cell.border = thin_border

            # Data rows
            for row_idx, row_data in enumerate(data, start=start_row + 1):
                ws.cell(row=row_idx, column=1, value=row_data.get("name", "-")).border = thin_border

                facets = row_data.get("facets", {})
                for col_idx, facet_key in enumerate(facet_keys, start=2):
                    facet_val = facets.get(facet_key, {})
                    value = facet_val.get("value", "-") if isinstance(facet_val, dict) else "-"
                    cell = ws.cell(row=row_idx, column=col_idx, value=value)
                    cell.border = thin_border

            # Auto-size columns
            for col_idx in range(1, len(headers) + 1):
                col_letter = get_column_letter(col_idx)
                ws.column_dimensions[col_letter].width = 20

        # Save to bytes
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        excel_bytes = output.getvalue()

        logger.info(
            "summary_exported_excel",
            summary_id=str(summary_id),
            size_bytes=len(excel_bytes),
            widgets=len(widgets),
        )

        return excel_bytes

    async def _get_execution(
        self,
        summary_id: UUID,
        execution_id: Optional[UUID] = None,
    ) -> Optional[SummaryExecution]:
        """Get execution data for export."""
        if execution_id:
            result = await self.session.execute(
                select(SummaryExecution).where(
                    SummaryExecution.id == execution_id,
                    SummaryExecution.summary_id == summary_id,
                )
            )
            return result.scalar_one_or_none()

        # Get latest completed execution
        result = await self.session.execute(
            select(SummaryExecution)
            .where(
                SummaryExecution.summary_id == summary_id,
                SummaryExecution.status == ExecutionStatus.COMPLETED,
            )
            .order_by(SummaryExecution.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    def _sanitize_sheet_name(self, name: str) -> str:
        """Sanitize sheet name for Excel (max 31 chars, no special chars)."""
        # Remove invalid characters
        invalid_chars = ['\\', '/', '*', '?', ':', '[', ']']
        for char in invalid_chars:
            name = name.replace(char, '')

        # Truncate to 31 characters
        if len(name) > 31:
            name = name[:28] + "..."

        return name or "Sheet"
