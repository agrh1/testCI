"""
Утилиты работы с eventlog ServiceDesk (старая версия интерфейса).
"""

from __future__ import annotations

import logging
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("bot.eventlog")


def get_item(event_id: int, login: str, password: str, base_url: str) -> Optional[str]:
    """
    Подключаемся к странице сообщения, и если такая страница есть - возвращаем её.
    """
    logger.debug("eventlog get_item start: event_id=%s base_url=%s", event_id, base_url)
    with requests.Session() as session:
        payload = {"login": login, "password": password}
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
            )
        }
        rs = session.post(f"{base_url.rstrip('/')}/registertask.ivp", headers=headers, data=payload)
        r = session.get(f"{base_url.rstrip('/')}/eventlog.ivp/view/{event_id}", cookies=rs.cookies)
        logger.debug("eventlog get_item response: event_id=%s status=%s", event_id, r.status_code)
        if r.status_code == 200:
            logger.debug("eventlog get_item ok: event_id=%s size=%s", event_id, len(r.text))
            return r.text
        return None


def get_last_item(login: str, password: str, base_url: str) -> Optional[str]:
    with requests.Session() as session:
        payload = {"login": login, "password": password}
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
            )
        }
        rs = session.post(f"{base_url.rstrip('/')}/registertask.ivp", headers=headers, data=payload)
        r = session.get(f"{base_url.rstrip('/')}/eventlog.ivp/list", cookies=rs.cookies)
        logger.debug("eventlog get_last_item response: status=%s", r.status_code)
        if r.status_code != 200:
            return None
        text = r.text.split()
        for line in text:
            if "eventlog.ivp/view/" in line:
                m = re.search(r"eventlog\.ivp/view/(\d+)", line)
                if not m:
                    continue
                last_item = m.group(1)
                logger.debug("eventlog get_last_item found: %s", last_item)
                return last_item
        return None


def parse_event(text: str) -> dict[str, str]:
    logger.debug("eventlog parse_event start")
    event_info: dict[str, str] = {}
    soup = BeautifulSoup(text, "html.parser")
    event_body = soup.find("div", {"class": "formbody"})
    fields = event_body.find_all("div", {"class": "field"}) if event_body else []
    for field in fields:
        if field.find("label", {"for": "name"}):
            key = field.find("label", {"for": "name"}).text.strip()
        if field.find("label", {"for": "Date"}):
            key = field.find("label", {"for": "Date"}).text.strip()
        if field.find("label", {"for": "Type"}):
            key = field.find("label", {"for": "Type"}).text.strip()
        if field.find("label", {"for": "description"}):
            key = field.find("label", {"for": "description"}).text.strip()
        event_field = field.contents[2].strip()
        event_info[key] = event_field
    logger.debug("eventlog parse_event done: keys=%s", list(event_info.keys()))
    return event_info

