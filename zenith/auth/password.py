"""
Secure password hashing for Zenith applications.

Uses Argon2 - the most modern and secure password hashing algorithm.
"""

import logging

from pwdlib import PasswordHash

logger = logging.getLogger("zenith.auth.password")


class PasswordManager:
    """
    Secure password manager using Argon2.

    Features:
    - Argon2 password hashing (most secure and modern)
    - Protection against timing attacks
    - Automatic salt generation
    - Configurable time/memory cost
    - Future-proof algorithm
    """

    def __init__(self):
        """
        Initialize password manager with Argon2.
        """
        self.password_hash = (
            PasswordHash.recommended()
        )  # Uses Argon2 with good defaults
        logger.info("Password manager initialized with Argon2")

        # Keep reference for compatibility
        self.pwd_context = self.password_hash

    def hash_password(self, password: str) -> str:
        """
        Hash a password securely.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        if not password:
            raise ValueError("Password cannot be empty")

        try:
            hashed = self.password_hash.hash(password)
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
            is_valid, updated_hash = self.password_hash.verify_and_update(
                password, hashed
            )

            if is_valid:
                logger.debug("Password verification successful")

                # Check if hash needs upgrading
                if updated_hash:
                    logger.info("Password hash upgraded to newer algorithm/parameters")
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
            # pwdlib handles this in verify_and_update, but we can check if it would produce an updated hash
            _, updated_hash = self.password_hash.verify_and_update("dummy", hashed)
            return updated_hash is not None
        except Exception:
            return True  # If we can't check, assume it needs updating


# Global password manager instance
_password_manager: PasswordManager | None = None


def configure_password_manager() -> PasswordManager:
    """Configure the global password manager with Argon2."""
    global _password_manager
    _password_manager = PasswordManager()
    return _password_manager


def get_password_manager() -> PasswordManager:
    """Get the configured password manager."""
    if _password_manager is None:
        # Auto-configure with defaults if not set (uses Argon2)
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
