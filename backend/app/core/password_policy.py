"""
Password Policy and Validation.

Enforces password strength requirements.
"""

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PasswordValidationResult:
    """Result of password validation."""

    is_valid: bool
    errors: List[str]
    score: int  # 0-100 strength score
    suggestions: List[str]


class PasswordPolicy:
    """
    Password policy enforcement.

    Default requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character (optional in relaxed mode)
    """

    def __init__(
        self,
        min_length: int = 8,
        max_length: int = 128,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = False,  # Optional for usability
        special_chars: str = "!@#$%^&*()_+-=[]{}|;:,.<>?",
    ):
        self.min_length = min_length
        self.max_length = max_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digit = require_digit
        self.require_special = require_special
        self.special_chars = special_chars

    def validate(self, password: str) -> PasswordValidationResult:
        """
        Validate a password against the policy.

        Args:
            password: The password to validate

        Returns:
            PasswordValidationResult with validation details
        """
        errors = []
        suggestions = []
        score = 0

        # Length checks
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters long")
        elif len(password) >= self.min_length:
            score += 20
            if len(password) >= 12:
                score += 10
            if len(password) >= 16:
                score += 10

        if len(password) > self.max_length:
            errors.append(f"Password must be at most {self.max_length} characters long")

        # Character type checks
        has_upper = bool(re.search(r"[A-Z]", password))
        has_lower = bool(re.search(r"[a-z]", password))
        has_digit = bool(re.search(r"\d", password))
        has_special = bool(re.search(f"[{re.escape(self.special_chars)}]", password))

        if self.require_uppercase and not has_upper:
            errors.append("Password must contain at least one uppercase letter")
        elif has_upper:
            score += 15

        if self.require_lowercase and not has_lower:
            errors.append("Password must contain at least one lowercase letter")
        elif has_lower:
            score += 15

        if self.require_digit and not has_digit:
            errors.append("Password must contain at least one digit")
        elif has_digit:
            score += 15

        if self.require_special and not has_special:
            errors.append("Password must contain at least one special character")
        elif has_special:
            score += 15

        # Common password patterns check
        common_patterns = [
            r"^123456",
            r"^password",
            r"^qwerty",
            r"^abc123",
            r"^letmein",
            r"^welcome",
            r"^admin",
            r"^login",
        ]

        for pattern in common_patterns:
            if re.search(pattern, password.lower()):
                errors.append("Password is too common or predictable")
                score = max(0, score - 30)
                break

        # Suggestions for improvement
        if not has_upper:
            suggestions.append("Add uppercase letters for stronger password")
        if not has_lower:
            suggestions.append("Add lowercase letters for stronger password")
        if not has_digit:
            suggestions.append("Add numbers for stronger password")
        if not has_special:
            suggestions.append("Add special characters for stronger password")
        if len(password) < 12:
            suggestions.append("Consider using a longer password (12+ characters)")

        # Cap score at 100
        score = min(100, max(0, score))

        return PasswordValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            score=score,
            suggestions=suggestions if score < 80 else [],
        )

    def get_requirements_text(self) -> str:
        """Get a human-readable description of password requirements."""
        requirements = [f"At least {self.min_length} characters"]

        if self.require_uppercase:
            requirements.append("At least one uppercase letter")
        if self.require_lowercase:
            requirements.append("At least one lowercase letter")
        if self.require_digit:
            requirements.append("At least one digit")
        if self.require_special:
            requirements.append("At least one special character")

        return ", ".join(requirements)


# Default policy instance
default_policy = PasswordPolicy(
    min_length=8,
    require_uppercase=True,
    require_lowercase=True,
    require_digit=True,
    require_special=False,  # Not required but improves score
)


def validate_password(password: str) -> PasswordValidationResult:
    """Validate password using default policy."""
    return default_policy.validate(password)


def check_password_strength(password: str) -> dict:
    """
    Check password strength and return details for API response.

    Returns:
        Dict with is_valid, score, errors, suggestions
    """
    result = validate_password(password)
    return {
        "is_valid": result.is_valid,
        "score": result.score,
        "errors": result.errors,
        "suggestions": result.suggestions,
        "requirements": default_policy.get_requirements_text(),
    }
