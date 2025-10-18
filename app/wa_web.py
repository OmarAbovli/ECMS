"""Helpers to automate WhatsApp Web sending using Playwright or fallbacks.

This module provides best-effort functions. To use Playwright you must install
`playwright` and run `playwright install` to get browsers. As fallback the
module can use `pywhatkit.sendwhatmsg_instantly` for simple send (which opens
the default browser and relies on logged-in WhatsApp Web session).

Note: Running Playwright or Selenium from a server requires a persistent
graphical session or running in headless mode and ensuring cookies/session
auth is handled. For production integrations prefer WhatsApp Business API.
"""
from typing import Optional
import time
import logging

log = logging.getLogger(__name__)

def send_with_playwright(phone: str, message: str, headless: bool = True, timeout: int = 30) -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        return {"ok": False, "error": f"playwright_not_available: {e}"}

    phone = phone.lstrip('+')
    url = f"https://web.whatsapp.com/send?phone={phone}&text={message}"

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=headless)
            context = browser.new_context()
            page = context.new_page()
            page.goto(url, timeout=timeout*1000)
            # wait for the send button or for chat to load
            # Try clicking the send button if available
            try:
                page.wait_for_selector('div[data-testid="conversation-compose-box-input"]', timeout=8000)
            except Exception:
                pass
            # press Enter to send
            try:
                page.keyboard.press('Enter')
            except Exception:
                pass
            time.sleep(2)
            context.close()
            browser.close()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_with_pywhatkit(phone: str, message: str) -> dict:
    # pywhatkit usually opens web.whatsapp and requires manual confirmation if not logged
    try:
        import pywhatkit
    except Exception as e:
        return {"ok": False, "error": f"pywhatkit_not_available: {e}"}
    try:
        # pywhatkit expects e.g. '+201234567890' or '201234567890'
        phone_arg = phone if phone.startswith('+') else '+' + phone
        # instant send (may open browser and require being logged in)
        pywhatkit.sendwhatmsg_instantly(phone_arg, message, wait_time=10, tab_close=True)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def send_via_web_best_effort(phone: str, message: str) -> dict:
    """Try Playwright first, then pywhatkit. Returns dict {ok: bool, error?: str}."""
    # URL-encode message minimally
    from urllib.parse import quote_plus
    encoded = quote_plus(message)
    # try playwright
    r = send_with_playwright(phone, encoded, headless=True)
    if r.get('ok'):
        return r
    # fallback to pywhatkit
    r2 = send_with_pywhatkit(phone, message)
    if r2.get('ok'):
        return r2
    # both failed
    return {"ok": False, "error": f"playwright_err={r.get('error')}|pywhatkit_err={r2.get('error')}"}
