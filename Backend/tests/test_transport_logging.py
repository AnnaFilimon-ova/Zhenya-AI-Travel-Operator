import logging

from app.providers import transport


def test_http_client_logs_do_not_print_urls_with_token():
    assert logging.getLogger("httpx").level >= logging.WARNING
    assert logging.getLogger("httpcore").level >= logging.WARNING
