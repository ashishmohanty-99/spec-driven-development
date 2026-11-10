"""Copy to .sdd/extensions/ui_login.py (git-ignored by `sdd init`) and adapt to your login form.

Credentials come from environment variables only. Use a dedicated low-privilege test account.
"""
import os


def login(page, base_url, role=None):
    user = os.environ["SDD_UI_USER"]
    password = os.environ["SDD_UI_PASS"]
    page.goto(f"{base_url}/login")
    page.get_by_label("Email").fill(user)
    page.get_by_label("Password").fill(password)
    page.get_by_role("button", name="Sign in").click()
    page.wait_for_url(lambda url: "/login" not in url)
