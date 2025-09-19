import pytest
from unittest.mock import MagicMock, patch
import redis

# Import the functions we are testing from the script
from clear_cache import clear_redis_cache, clear_file_caches, main

# Define paths to the modules/functions we need to mock
REDIS_CLIENT_PATH = "clear_cache.redis.from_url"
SHUTIL_PATH = "clear_cache.shutil"
SETTINGS_PATH = "clear_cache.settings"
BUILTINS_INPUT_PATH = "builtins.input"


# --- START: THE FIX (Step 1) ---
@pytest.fixture
def mock_settings(mocker):
    """
    Mocks the settings module and ensures that its Path objects are also
    MagicMocks so we can assert calls to their methods.
    """
    mock_settings = mocker.patch(SETTINGS_PATH)

    # Instead of real Path objects, we use MagicMocks.
    # We only need to mock the attributes that are actually used by the script.
    mock_settings.CHROMA_PERSIST_DIR = MagicMock()
    mock_settings.ARTIFACT_CACHE_DIR = MagicMock()
    mock_settings.RESULTS_DIR = MagicMock()

    return mock_settings


def test_clear_redis_cache_happy_path(mocker):
    """Tests that the redis cache is flushed on a successful connection."""
    # ARRANGE
    mock_redis_client = MagicMock()
    mocker.patch(REDIS_CLIENT_PATH, return_value=mock_redis_client)

    # ACT
    clear_redis_cache()

    # ASSERT
    mock_redis_client.ping.assert_called_once()
    mock_redis_client.flushdb.assert_called_once()


def test_clear_redis_cache_connection_error(mocker):
    """Tests that a connection error is handled gracefully."""
    # ARRANGE
    mock_redis_client = MagicMock()
    mock_redis_client.ping.side_effect = redis.ConnectionError
    mocker.patch(REDIS_CLIENT_PATH, return_value=mock_redis_client)

    # ACT
    clear_redis_cache()  # Should not raise an exception

    # ASSERT
    mock_redis_client.flushdb.assert_not_called()


def test_clear_file_caches_deletes_existing_dirs(mocker, mock_settings):
    """Tests that shutil.rmtree is called for directories that exist."""
    # ARRANGE
    mock_rmtree = mocker.patch(SHUTIL_PATH + ".rmtree")

    # Because our settings attributes are now mocks, we need to configure
    # their '.exists()' method to simulate them existing on the file system.
    mock_settings.CHROMA_PERSIST_DIR.exists.return_value = True
    mock_settings.ARTIFACT_CACHE_DIR.exists.return_value = True
    mock_settings.RESULTS_DIR.exists.return_value = True

    # ACT
    clear_file_caches()

    # ASSERT
    # This assertion remains the same.
    assert mock_rmtree.call_count == 3

    # This assertion will now work correctly because RESULTS_DIR is a mock.
    mock_settings.RESULTS_DIR.mkdir.assert_called_once_with(exist_ok=True)


def test_main_with_yes_flag_bypasses_prompt(mocker):
    """
    Tests the most important feature: the '-y' flag should bypass the
    interactive confirmation prompt.
    """
    # ARRANGE
    # Mock the functions that would perform the actual work
    mock_clear_files = mocker.patch("clear_cache.clear_file_caches")
    mock_clear_redis = mocker.patch("clear_cache.clear_redis_cache")
    mock_input = mocker.patch(BUILTINS_INPUT_PATH)

    # Mock sys.argv to simulate running 'python clear_cache.py -y'
    mocker.patch("sys.argv", ["clear_cache.py", "-y"])

    # ACT
    main()

    # ASSERT
    # The crucial assertion: the input prompt was never called.
    mock_input.assert_not_called()
    # And the work was done.
    mock_clear_files.assert_called_once()
    mock_clear_redis.assert_called_once()


def test_main_without_yes_flag_triggers_prompt(mocker):
    """
    Tests that if no flag is provided, the interactive prompt is shown.
    """
    # ARRANGE
    mock_clear_files = mocker.patch("clear_cache.clear_file_caches")
    mock_clear_redis = mocker.patch("clear_cache.clear_redis_cache")
    # Simulate the user typing 'y' and pressing Enter.
    mock_input = mocker.patch(BUILTINS_INPUT_PATH, return_value="y")

    mocker.patch("sys.argv", ["clear_cache.py"])

    # ACT
    main()

    # ASSERT
    # The prompt should have been called.
    mock_input.assert_called_once()
    # And the work should have been done.
    mock_clear_files.assert_called_once()
