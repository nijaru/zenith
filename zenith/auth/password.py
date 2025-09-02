"""
Secure password hashing for Zenith applications.

Uses bcrypt for industry-standard password security with
configurable rounds and secure verification.
"""

import logging

from passlib.context import CryptContext

logger = logging.getLogger("zenith.auth.password")


class PasswordManager:
    """
    Secure password manager using bcrypt.

    Features:
    - bcrypt hashing with configurable rounds
    - Secure password verification
    - Protection against timing attacks
    - Automatic salt generation
    - Future-proof algorithm upgrading
    """

    def __init__(self, rounds: int = 12):
        """
        Initialize password manager.

        Args:
            rounds: bcrypt rounds (4-31, default 12)
                   Higher = more secure but slower
                   12 rounds = ~250ms on modern hardware
        """
        if not 4 <= rounds <= 31:
            raise ValueError("bcrypt rounds must be between 4 and 31")

        self.rounds = rounds

        # Create passlib context for secure password handling
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            default="bcrypt",
            bcrypt__rounds=rounds,
            # Automatically upgrade to new rounds if changed
            deprecated="auto",
        )

        logger.info(f"Password manager initialized with {rounds} bcrypt rounds")

    def hash_password(self, password: str) -> str:
        """
        Hash a password securely using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        if not password:
            raise ValueError("Password cannot be empty")

        try:
            hashed = self.pwd_context.hash(password)
            logger.debug("Password hashed successfully")
            return hashed
        except Exception as e:
            logger.error(f"Failed to hash password: {e}")
            raise

    def verify_password(self, password: str, hashed: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            password: Plain text password to verify
            hashed: Previously hashed password

        Returns:
            True if password matches, False otherwise
        """
        if not password or not hashed:
            return False

        try:
            is_valid = self.pwd_context.verify(password, hashed)

            if is_valid:
                logger.debug("Password verification successful")

                # Check if hash needs upgrading (if rounds changed)
                if self.pwd_context.needs_update(hashed):
                    logger.info("Password hash needs updating to new rounds")
                    # Note: Framework could automatically rehash here on login
            else:
                logger.debug("Password verification failed")

            return is_valid

        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False

    def needs_rehash(self, hashed: str) -> bool:
        """Check if a password hash needs updating."""
        try:
            return self.pwd_context.needs_update(hashed)
        except Exception:
            return True  # If we can't check, assume it needs updating


# Global password manager instance
_password_manager: PasswordManager | None = None


def configure_password_manager(rounds: int = 12) -> PasswordManager:
    """Configure the global password manager."""
    global _password_manager
    _password_manager = PasswordManager(rounds=rounds)
    return _password_manager


def get_password_manager() -> PasswordManager:
    """Get the configured password manager."""
    if _password_manager is None:
        # Auto-configure with defaults if not set
        configure_password_manager()
    assert _password_manager is not None  # Type hint for pyright
    return _password_manager


# Convenience functions
def hash_password(password: str) -> str:
    """Hash a password using the global password manager."""
    return get_password_manager().hash_password(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password using the global password manager."""
    return get_password_manager().verify_password(password, hashed)


def generate_secure_password(length: int = 16) -> str:
    """
    Generate a secure random password.

    Useful for temporary passwords or API keys.
    """
    import secrets
    import string

    if length < 8:
        raise ValueError("Password length should be at least 8 characters")

    # Character set: letters, digits, and some symbols
    chars = string.ascii_letters + string.digits + "!@#$%^&*"

    # Ensure at least one of each type
    password = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*"),
    ]

    # Fill the rest randomly
    for _ in range(length - 4):
        password.append(secrets.choice(chars))

    # Shuffle to avoid predictable patterns
    secrets.SystemRandom().shuffle(password)

    return "".join(password)
