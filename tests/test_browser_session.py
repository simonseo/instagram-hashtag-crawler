from __future__ import annotations

from http.cookiejar import CookieJar
from unittest.mock import MagicMock, patch

import pytest

from instagram_hashtag_crawler.browser_session import (
    SUPPORTED_BROWSERS,
    _cookiejar_to_dict,
    _get_browser_cookies,
    load_browser_session,
)

# ---------------------------------------------------------------------------
# _cookiejar_to_dict
# ---------------------------------------------------------------------------


def test_cookiejar_to_dict_empty() -> None:
    cj = CookieJar()
    assert _cookiejar_to_dict(cj) == {}


def test_cookiejar_to_dict_converts() -> None:
    cj = CookieJar()
    # CookieJar doesn't have a simple .set method; mock cookies instead
    cookie1 = MagicMock()
    cookie1.name = "sessionid"
    cookie1.value = "abc123"
    cookie2 = MagicMock()
    cookie2.name = "csrftoken"
    cookie2.value = "xyz789"
    cj._cookies = {}  # noqa: SLF001
    # Patch iteration
    with patch.object(CookieJar, "__iter__", return_value=iter([cookie1, cookie2])):
        result = _cookiejar_to_dict(cj)
    assert result == {"sessionid": "abc123", "csrftoken": "xyz789"}


# ---------------------------------------------------------------------------
# _get_browser_cookies
# ---------------------------------------------------------------------------


def test_get_browser_cookies_unsupported_browser() -> None:
    mock_bc3 = MagicMock()
    with (
        patch.dict("sys.modules", {"browser_cookie3": mock_bc3}),
        pytest.raises(ValueError, match="Unsupported browser"),
    ):
        _get_browser_cookies("netscape")


def test_get_browser_cookies_all_supported_names() -> None:
    """Verify the SUPPORTED_BROWSERS tuple contains expected browsers."""
    assert "chrome" in SUPPORTED_BROWSERS
    assert "firefox" in SUPPORTED_BROWSERS
    assert "safari" in SUPPORTED_BROWSERS
    assert "edge" in SUPPORTED_BROWSERS
    assert "brave" in SUPPORTED_BROWSERS


@patch("instagram_hashtag_crawler.browser_session.browser_cookie3", create=True)
def test_get_browser_cookies_permission_error(mock_bc3: MagicMock) -> None:
    mock_bc3.chrome.side_effect = PermissionError("denied")
    with (
        patch.dict("sys.modules", {"browser_cookie3": mock_bc3}),
        pytest.raises(RuntimeError, match="permission denied"),
    ):
        _get_browser_cookies("chrome")


# ---------------------------------------------------------------------------
# load_browser_session
# ---------------------------------------------------------------------------


@patch("instagram_hashtag_crawler.browser_session._get_browser_cookies")
def test_load_browser_session_missing_sessionid(mock_get: MagicMock) -> None:
    """Raises RuntimeError when sessionid is missing from cookies."""
    cj = CookieJar()
    # Only csrftoken, no sessionid or ds_user_id
    cookie = MagicMock()
    cookie.name = "csrftoken"
    cookie.value = "tok"
    with patch.object(CookieJar, "__iter__", return_value=iter([cookie])):
        mock_get.return_value = cj
        loader = MagicMock()
        with pytest.raises(RuntimeError, match="Missing required Instagram cookies"):
            load_browser_session(loader, "chrome")


@patch("instagram_hashtag_crawler.browser_session._get_browser_cookies")
def test_load_browser_session_success(mock_get: MagicMock) -> None:
    """Successfully loads session when all required cookies are present."""
    cj = CookieJar()
    cookies = []
    for name, value in [
        ("sessionid", "sess123"),
        ("csrftoken", "csrf456"),
        ("ds_user_id", "12345"),
        ("mid", "mid789"),
    ]:
        c = MagicMock()
        c.name = name
        c.value = value
        cookies.append(c)

    with patch.object(CookieJar, "__iter__", return_value=iter(cookies)):
        mock_get.return_value = cj
        loader = MagicMock()
        user_id = load_browser_session(loader, "chrome")

    assert user_id == "12345"
    loader.context.load_session.assert_called_once()
    call_args = loader.context.load_session.call_args
    assert call_args[0][0] == "12345"  # username arg = user_id
    cookie_dict = call_args[0][1]
    assert cookie_dict["sessionid"] == "sess123"
    assert cookie_dict["csrftoken"] == "csrf456"
