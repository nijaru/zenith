"""Tests for session management functionality."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from zenith.sessions.manager import Session, SessionManager
from zenith.sessions.store import SessionStore


class TestSession:
    """Test Session data container."""

    def test_session_init_defaults(self):
        """Test session initialization with defaults."""
        session = Session("test123")

        assert session.session_id == "test123"
        assert session._data == {}
        assert isinstance(session.created_at, datetime)
        assert session.expires_at is None
        assert session._dirty is False
        assert session._new is True

    def test_session_init_with_data(self):
        """Test session initialization with data."""
        test_data = {"user_id": 123, "username": "testuser"}
        created = datetime.now(UTC) - timedelta(hours=1)
        expires = datetime.now(UTC) + timedelta(hours=1)

        session = Session(
            "test123", data=test_data, created_at=created, expires_at=expires, is_new=False
        )

        assert session.session_id == "test123"
        assert session._data == test_data
        assert session.created_at == created
        assert session.expires_at == expires
        assert session._dirty is False
        assert session._new is False

    def test_session_get(self):
        """Test getting session values."""
        session = Session("test123", {"user_id": 123, "role": "admin"})

        assert session.get("user_id") == 123
        assert session.get("role") == "admin"
        assert session.get("nonexistent") is None
        assert session.get("nonexistent", "default") == "default"

    def test_session_set(self):
        """Test setting session values."""
        session = Session("test123")

        session.set("user_id", 456)
        session.set("theme", "dark")

        assert session._data["user_id"] == 456
        assert session._data["theme"] == "dark"
        assert session._dirty is True

    def test_session_delete(self):
        """Test deleting session keys."""
        session = Session("test123", {"user_id": 123, "theme": "light"})
        session._dirty = False  # Reset dirty flag

        session.delete("theme")

        assert "theme" not in session._data
        assert "user_id" in session._data  # Other keys remain
        assert session._dirty is True

    def test_session_delete_nonexistent(self):
        """Test deleting non-existent key."""
        session = Session("test123", {"user_id": 123})
        session._dirty = False

        session.delete("nonexistent")

        # Should not raise error or mark dirty
        assert session._dirty is False

    def test_session_clear(self):
        """Test clearing all session data."""
        session = Session("test123", {"user_id": 123, "theme": "dark"})
        session._dirty = False

        session.clear()

        assert session._data == {}
        assert session._dirty is True

    def test_session_is_expired(self):
        """Test session expiration check."""
        # Not expired - no expiry set
        session1 = Session("test1")
        assert session1.is_expired() is False

        # Not expired - future expiry
        future = datetime.now(UTC) + timedelta(hours=1)
        session2 = Session("test2", expires_at=future)
        assert session2.is_expired() is False

        # Expired - past expiry
        past = datetime.now(UTC) - timedelta(hours=1)
        session3 = Session("test3", expires_at=past)
        assert session3.is_expired() is True

    def test_session_refresh_expiry(self):
        """Test refreshing session expiry."""
        session = Session("test123")
        session._dirty = False

        max_age = timedelta(hours=2)
        session.refresh_expiry(max_age)

        assert session.expires_at is not None
        assert session.expires_at > datetime.now(UTC)
        assert session._dirty is True

    def test_session_properties(self):
        """Test session properties."""
        session = Session("test123", {"user": "test"}, is_new=False)

        # Initially not dirty, not new (loaded session)
        assert session.is_dirty is False
        assert session.is_new is False

        # Modify data
        session.set("role", "admin")
        assert session.is_dirty is True

        # Mark clean
        session.mark_clean()
        assert session.is_dirty is False
        assert session.is_new is False

    def test_session_to_dict(self):
        """Test converting session to dictionary."""
        created = datetime.now(UTC)
        expires = datetime.now(UTC) + timedelta(hours=1)
        session = Session(
            "test123", data={"user_id": 123}, created_at=created, expires_at=expires
        )

        result = session.to_dict()

        assert result["session_id"] == "test123"
        assert result["data"] == {"user_id": 123}
        assert result["created_at"] == created.isoformat()
        assert result["expires_at"] == expires.isoformat()

    def test_session_to_dict_no_expires(self):
        """Test to_dict with no expiration."""
        session = Session("test123", {"user": "test"})

        result = session.to_dict()

        assert result["expires_at"] is None

    def test_session_from_dict(self):
        """Test creating session from dictionary."""
        created = datetime.now(UTC)
        expires = datetime.now(UTC) + timedelta(hours=1)

        data = {
            "session_id": "test456",
            "data": {"user_id": 789, "role": "user"},
            "created_at": created.isoformat(),
            "expires_at": expires.isoformat(),
        }

        session = Session.from_dict(data)

        assert session.session_id == "test456"
        assert session._data == {"user_id": 789, "role": "user"}
        assert abs((session.created_at - created).total_seconds()) < 1
        assert abs((session.expires_at - expires).total_seconds()) < 1

    def test_session_from_dict_no_expires(self):
        """Test from_dict with no expiration."""
        data = {
            "session_id": "test789",
            "data": {"user": "test"},
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": None,
        }

        session = Session.from_dict(data)

        assert session.expires_at is None

    def test_session_dict_interface(self):
        """Test dict-like interface."""
        session = Session("test123", {"user_id": 123, "theme": "dark"})

        # __getitem__
        assert session["user_id"] == 123

        # __setitem__
        session["role"] = "admin"
        assert session._data["role"] == "admin"
        assert session._dirty is True

        # __delitem__
        del session["theme"]
        assert "theme" not in session._data

        # __contains__
        assert "user_id" in session
        assert "theme" not in session

        # __len__
        assert len(session) == 2  # user_id and role

        # keys, values, items
        assert list(session.keys()) == ["user_id", "role"]
        assert list(session.values()) == [123, "admin"]
        assert list(session.items()) == [("user_id", 123), ("role", "admin")]


class TestSessionManager:
    """Test SessionManager functionality."""

    @pytest.fixture
    def mock_store(self):
        """Mock session store."""
        store = AsyncMock(spec=SessionStore)
        # Ensure async methods return coroutines
        store.delete = AsyncMock(return_value=None)
        store.save = AsyncMock(return_value=None)
        store.load = AsyncMock(return_value=None)
        store.cleanup_expired = AsyncMock(return_value=0)
        return store

    @pytest.fixture
    def session_manager(self, mock_store):
        """Create SessionManager with mock store."""
        return SessionManager(
            store=mock_store,
            cookie_name="test_session",
            max_age=timedelta(hours=1),
            is_secure=False,  # For testing
            is_http_only=True,
            same_site="lax",
        )

    def test_session_manager_init(self, mock_store):
        """Test SessionManager initialization."""
        manager = SessionManager(
            store=mock_store,
            cookie_name="custom_session",
            max_age=timedelta(days=7),
            is_secure=True,
            domain="example.com",
            path="/app",
        )

        assert manager.store == mock_store
        assert manager.cookie_name == "custom_session"
        assert manager.max_age == timedelta(days=7)
        assert manager.secure is True
        assert manager.domain == "example.com"
        assert manager.path == "/app"

    def test_generate_session_id(self, session_manager):
        """Test session ID generation."""
        session_id = session_manager.generate_session_id()

        assert isinstance(session_id, str)
        assert len(session_id) > 0

        # Should generate unique IDs
        session_id2 = session_manager.generate_session_id()
        assert session_id != session_id2

    @pytest.mark.asyncio
    async def test_create_session(self, session_manager, mock_store):
        """Test creating new session."""
        test_data = {"user_id": 123}

        session = await session_manager.create_session(test_data)

        assert isinstance(session, Session)
        assert len(session.session_id) > 0
        assert session._data == test_data
        assert session.expires_at is not None

        # Should save to store
        mock_store.save.assert_called_once_with(session)

    @pytest.mark.asyncio
    async def test_create_session_no_data(self, session_manager, mock_store):
        """Test creating session without initial data."""
        session = await session_manager.create_session()

        assert session._data == {}
        mock_store.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_exists(self, session_manager, mock_store):
        """Test getting existing valid session."""
        # Mock store returns session
        stored_session = Session("test123", {"user_id": 456})
        mock_store.load.return_value = stored_session

        session = await session_manager.get_session("test123")

        assert session == stored_session
        mock_store.load.assert_called_once_with("test123")

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, session_manager, mock_store):
        """Test getting non-existent session."""
        mock_store.load.return_value = None

        session = await session_manager.get_session("nonexistent")

        assert session is None

    @pytest.mark.asyncio
    async def test_get_session_expired(self, session_manager, mock_store):
        """Test getting expired session."""
        # Create expired session
        expired_session = Session(
            session_id="expired123",
            data={"test": "data"},
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        mock_store.load.return_value = expired_session

        session = await session_manager.get_session("expired123")

        assert session is None
        # Should delete expired session
        mock_store.delete.assert_called_once_with("expired123")

    @pytest.mark.asyncio
    async def test_save_session_dirty(self, session_manager, mock_store):
        """Test saving dirty session."""
        session = Session("test123", {"user": "test"})
        session.set("role", "admin")  # Makes dirty

        await session_manager.save_session(session)

        mock_store.save.assert_called_once_with(session)
        assert session._dirty is False  # Should be marked clean

    @pytest.mark.asyncio
    async def test_save_session_clean(self, session_manager, mock_store):
        """Test saving clean session."""
        session = Session("test123", {"user": "test"})
        # Session is not dirty

        await session_manager.save_session(session)

        # Should not save clean session
        mock_store.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_destroy_session(self, session_manager, mock_store):
        """Test destroying session."""
        await session_manager.destroy_session("test123")

        mock_store.delete.assert_called_once_with("test123")

    @pytest.mark.asyncio
    async def test_regenerate_session_id(self, session_manager, mock_store):
        """Test session ID regeneration."""
        old_session = Session("old123", {"user_id": 789, "role": "user"})

        with patch.object(session_manager, "create_session") as mock_create:
            new_session = Session("new456", {"user_id": 789, "role": "user"})
            mock_create.return_value = new_session

            result = await session_manager.regenerate_session_id(old_session)

            # Should create new session with same data
            mock_create.assert_called_once_with({"user_id": 789, "role": "user"})

            # Should delete old session
            mock_store.delete.assert_called_once_with("old123")

            assert result == new_session

    @pytest.mark.asyncio
    async def test_cleanup_expired(self, session_manager, mock_store):
        """Test cleaning up expired sessions."""
        mock_store.cleanup_expired.return_value = 5

        count = await session_manager.cleanup_expired()

        assert count == 5
        mock_store.cleanup_expired.assert_called_once()

    def test_get_cookie_config(self, session_manager):
        """Test getting cookie configuration."""
        config = session_manager.get_cookie_config()

        expected = {
            "key": "test_session",
            "max_age": 3600,  # 1 hour in seconds
            "path": "/",
            "httponly": True,
            "samesite": "lax",
        }
        assert config == expected

    def test_get_cookie_config_secure(self, mock_store):
        """Test cookie config with secure settings."""
        manager = SessionManager(store=mock_store, is_secure=True, domain="example.com")

        config = manager.get_cookie_config()

        assert config["secure"] is True
        assert config["domain"] == "example.com"


class TestSessionIntegration:
    """Test session integration scenarios."""

    @pytest.mark.asyncio
    async def test_user_login_session_flow(self):
        """Test complete user login session flow."""
        mock_store = AsyncMock(spec=SessionStore)
        manager = SessionManager(mock_store, max_age=timedelta(hours=2))

        # User logs in - create session
        login_data = {"user_id": 123, "username": "alice", "role": "user"}
        session = await manager.create_session(login_data)

        assert session["user_id"] == 123
        assert session["username"] == "alice"
        mock_store.save.assert_called()

        # Simulate getting session on subsequent request
        mock_store.load.return_value = session
        retrieved_session = await manager.get_session(session.session_id)

        assert retrieved_session == session
        assert retrieved_session["user_id"] == 123

    @pytest.mark.asyncio
    async def test_session_privilege_escalation_regeneration(self):
        """Test session ID regeneration after privilege change."""
        mock_store = AsyncMock(spec=SessionStore)
        manager = SessionManager(mock_store)

        # User starts with basic session
        session = await manager.create_session({"user_id": 123, "role": "user"})
        old_session_id = session.session_id

        # User performs admin action - regenerate session ID
        session["role"] = "admin"

        with patch.object(manager, "create_session") as mock_create:
            new_session = Session("new_id", {"user_id": 123, "role": "admin"})
            mock_create.return_value = new_session

            regenerated = await manager.regenerate_session_id(session)

            assert regenerated.session_id != old_session_id
            assert regenerated["role"] == "admin"

            # Old session should be deleted
            mock_store.delete.assert_called_with(old_session_id)

    @pytest.mark.asyncio
    async def test_session_expiry_and_cleanup(self):
        """Test session expiration and cleanup."""
        mock_store = AsyncMock(spec=SessionStore)
        manager = SessionManager(mock_store, max_age=timedelta(minutes=1))

        # Create session that's already expired
        expired_session = Session(
            "expired",
            data={"user_id": 123},
            expires_at=datetime.now(UTC) - timedelta(minutes=5),
        )
        mock_store.load.return_value = expired_session

        # Try to get expired session
        result = await manager.get_session("expired")

        # Should return None and delete expired session
        assert result is None
        mock_store.delete.assert_called_once_with("expired")

    @pytest.mark.asyncio
    async def test_session_data_persistence(self):
        """Test session data modifications and persistence."""
        mock_store = AsyncMock(spec=SessionStore)
        manager = SessionManager(mock_store)

        # Create and modify session
        session = await manager.create_session({"cart": []})

        # Add items to cart
        session["cart"].append({"id": 1, "name": "Widget"})
        session["cart"].append({"id": 2, "name": "Gadget"})
        session["total"] = 25.99

        # Save modified session
        await manager.save_session(session)

        # Should save because session is dirty
        assert mock_store.save.call_count == 2  # Initial create + manual save

        # Verify data
        assert len(session["cart"]) == 2
        assert session["total"] == 25.99

    def test_session_dict_interface_edge_cases(self):
        """Test edge cases of session dict interface."""
        session = Session("test", {"existing": "value"})

        # Test that missing keys return None with get()
        assert session.get("nonexistent") is None

        # Test deletion of missing key doesn't raise error
        session.delete("nonexistent")  # Should not raise

        # Test that modifications mark session as dirty
        session._dirty = False
        session["new_key"] = "new_value"
        assert session.is_dirty is True

        session._dirty = False
        del session["existing"]
        assert session.is_dirty is True
