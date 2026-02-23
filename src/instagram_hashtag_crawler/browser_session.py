from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from http.cookiejar import CookieJar

    import instaloader

logger = logging.getLogger(__name__)

SUPPORTED_BROWSERS = (
    "chrome",
    "firefox",
    "safari",
    "edge",
    "opera",
    "brave",
    "chromium",
    "vivaldi",
)

REQUIRED_COOKIES = ("sessionid", "csrftoken", "ds_user_id")


def _get_browser_cookies(
    browser: str,
    cookie_file: str | None = None,
) -> CookieJar:
    """Extract Instagram cookies from the specified browser.

    Parameters
    ----------
    browser:
        Browser name (e.g. ``"chrome"``).
    cookie_file:
        Optional path to the browser's cookie database file.  Useful
        when the browser has multiple profiles (e.g. Chrome's
        ``~/Library/Application Support/Google/Chrome/Profile 1/Cookies``).

    Returns an ``http.cookiejar.CookieJar`` containing cookies for
    ``.instagram.com``.  Raises ``RuntimeError`` if *browser_cookie3*
    is not installed or the browser is unsupported.
    """
    try:
        import browser_cookie3  # noqa: PLC0415
    except ImportError as exc:
        msg = (
            "browser_cookie3 is required for --browser. "
            "Install it with: pip install instagram-hashtag-crawler[browser]"
        )
        raise RuntimeError(msg) from exc

    browser_lower = browser.lower()
    if browser_lower not in SUPPORTED_BROWSERS:
        msg = f"Unsupported browser {browser!r}. Choose from: {', '.join(SUPPORTED_BROWSERS)}"
        raise ValueError(msg)

    fn = getattr(browser_cookie3, browser_lower)
    kwargs: dict[str, str] = {"domain_name": ".instagram.com"}
    if cookie_file is not None:
        kwargs["cookie_file"] = cookie_file

    try:
        return fn(**kwargs)
    except PermissionError as exc:
        msg = (
            f"Cannot access {browser} cookies — permission denied. "
            "On macOS, you may need to grant Full Disk Access to your terminal."
        )
        raise RuntimeError(msg) from exc


def _cookiejar_to_dict(cj: CookieJar) -> dict[str, str]:
    """Convert a CookieJar to a plain dict of {name: value}."""
    return {cookie.name: cookie.value for cookie in cj if cookie.value is not None}


def load_browser_session(
    loader: instaloader.Instaloader,
    browser: str,
    cookie_file: str | None = None,
) -> str:
    """Load an Instagram session from browser cookies into *loader*.

    Extracts cookies from the specified browser, validates that the
    required Instagram cookies are present, and loads them into the
    instaloader session.

    Parameters
    ----------
    loader:
        An initialised ``Instaloader`` instance.
    browser:
        Browser name (e.g. ``"chrome"``).
    cookie_file:
        Optional path to the browser's cookie database file.  Pass this
        when the logged-in session lives in a non-default profile.

    Returns the Instagram username (``ds_user_id`` is present but
    ``username`` is not stored in cookies — we return the user ID
    as a fallback and let the caller verify with ``test_login``).

    Raises
    ------
    RuntimeError
        If browser_cookie3 is not installed, the browser is inaccessible,
        or the required Instagram cookies are missing.
    """
    cj = _get_browser_cookies(browser, cookie_file=cookie_file)
    cookie_dict = _cookiejar_to_dict(cj)

    logger.debug("Extracted cookies from %s: %s", browser, sorted(cookie_dict.keys()))

    missing = [name for name in REQUIRED_COOKIES if name not in cookie_dict]
    if missing:
        msg = (
            f"Missing required Instagram cookies from {browser}: {', '.join(missing)}. "
            "Make sure you are logged into instagram.com in your browser."
        )
        raise RuntimeError(msg)

    # load_session expects a plain dict and sets up the full requests.Session
    # internally — including headers and CSRF token.
    user_id = cookie_dict["ds_user_id"]
    loader.context.load_session(user_id, cookie_dict)

    logger.info("Loaded Instagram session from %s (user_id=%s)", browser, user_id)
    return user_id
