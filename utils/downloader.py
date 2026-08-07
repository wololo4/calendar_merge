import os
import requests
import json
import re
import cloudscraper
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth
from bs4 import BeautifulSoup

from parsers.nhl import parse_nhl_json_to_calendar
from parsers.hockeytech import parse_hockeytech
from parsers.publicationsports import parse_publicationsports
from parsers.ncaa import parse_ncaa_east, parse_ncaa_conf, parse_ncaa_b10
from parsers.khl import parse_khl_json
from parsers.chl_europe import parse_chl_europe_json_to_calendar
from parsers.nl import parse_nl_json
from parsers.ufa import parse_ufa_json_to_calendar
from parsers.vhl import parse_vhl_html
from parsers.liiga import parse_liiga_json_to_calendar
from parsers.del_parser import parse_del_html
from parsers.shl import parse_shl_json_to_calendar

def parse_responsive_calendar(raw_json, team_name):
    events = []

    for day in raw_json:
        day_events = day.get("events")
        if not day_events:
            continue

        for ev in day_events:
            events.append(ev)

    return events

DOWNLOAD_HANDLERS = {}
SCRAPER = cloudscraper.create_scraper()
SESSION = requests.Session()

def register_downloader(name):
    def decorator(func):
        DOWNLOAD_HANDLERS[name] = func
        return func
    return decorator

def download_single_feed(feed_info):
    """Worker function to process one feed concurrently."""
    league, team_name, url, team_filter, parser = feed_info

    print(f"Downloading: {league} - {team_name} -> {url[:50]}...")

    handler = DOWNLOAD_HANDLERS.get(parser)
    if not handler:
        print(f"Unknown parser: {parser}")
        return league, team_name, None

    try:
        return handler(league, team_name, url, team_filter)
    except Exception as e:
        print(f"Error in parser '{parser}' for {team_name}: {e}")
        return league, team_name, None

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
}

def fetch_json(url, headers=None):
    session = SESSION

    req_headers = DEFAULT_HEADERS.copy()
    if headers:
        req_headers.update(headers)

    resp = session.get(url, headers=req_headers, timeout=4)
    resp.raise_for_status()

    return resp.json()


def fetch_html(url, headers=None):
    session = SESSION

    req_headers = DEFAULT_HEADERS.copy()
    if headers:
        req_headers.update(headers)

    resp = session.get(url, headers=req_headers, timeout=4)
    resp.raise_for_status()

    return resp.text

# ============================
# CHL EUROPE JSON
# ============================
@register_downloader("chl_europe")
def download_europe(league, team_name, url, team_filter):
    try:
        raw_json = fetch_json(url)
    except:
        return league, team_name, None
    calendar = parse_chl_europe_json_to_calendar(raw_json, team_filter)
    return league, team_name, calendar

# ============================
# DEL HTML
# ============================
@register_downloader("del")
def download_del(league, team_name, url, team_filter):
    try:
        html = fetch_html(url)
    except:
        return league, team_name, None
    calendar = parse_del_html(html, team_name)
    return league, team_name, calendar

# ============================
# HockeyTech JSON
# ============================
@register_downloader("hockeytech")
def download_hockeytech(league, team_name, url, team_filter):
    try:
        raw_json = fetch_json(url)
    except:
        return league, team_name, None
    calendar = parse_hockeytech(raw_json, team_filter)
    return league, team_name, calendar

# ============================
# KHL JSON
# ============================
@register_downloader("khl")
def download_khl(league, team_name, url, team_filter):
    all_events = []
    page = 1

    while True:
        paged_url = f"{url}&page={page}"
        try:
            raw_json = fetch_json(paged_url)
        except:
            break
        if not raw_json:
            break
        all_events.extend(raw_json)
        page += 1

    calendar = parse_khl_json(all_events, team_filter)
    return league, team_name, calendar

# ============================
# LIIGA JSON
# ============================
@register_downloader("liiga")
def download_liiga(league, team_name, url, team_filter):
    try:
        raw_json = fetch_json(url)
    except:
        return league, team_name, None
    if not team_filter:
        return league, team_name, None
    team_id = team_filter[0]

    filtered = []
    for game in raw_json:
        home = game.get("homeTeamId")
        away = game.get("awayTeamId")
        if home == team_id or away == team_id:
            filtered.append(game)

    calendar = parse_liiga_json_to_calendar(filtered)
    return league, team_name, calendar

# ============================
# NCAA / JSON
# ============================
@register_downloader("ncaa_conf")
def download_ncaa_conf(league, team_name, url, team_filter):
    try:
        raw_json = fetch_json(url)
    except:
        return league, team_name, None
    calendar = parse_ncaa_conf(raw_json, team_name)
    return league, team_name, calendar

@register_downloader("ncaa_b10")
def download_ncaa_b10(league, team_name, url, team_filter):
    try:
        raw_json = fetch_json(url)
    except:
        return league, team_name, None
    calendar = parse_ncaa_b10(raw_json, team_filter)
    return league, team_name, calendar

@register_downloader("ncaa_east")
def download_ncaa_east(league, team_name, url, team_filter):
    try:
        raw_json = fetch_json(url)
    except:
        return league, team_name, None
    calendar = parse_ncaa_east(raw_json, team_name)
    return league, team_name, calendar

# ============================
# NHL (JSON)
# ============================
@register_downloader("nhl")
def download_nhl(league, team_name, url, team_filter):
    try:
        raw_json = fetch_json(url)
    except:
        return league, team_name, None
    games_list = raw_json.get("games", [])
    calendar = parse_nhl_json_to_calendar({"games": games_list})
    return league, team_name, calendar

# ============================
# NL JSON
# ============================
@register_downloader("nl")
def download_nl(league, team_name, url, team_filter):
    try:
        raw_json = fetch_json(url)
    except:
        return league, team_name, None
    calendar = parse_nl_json(raw_json, team_filter)
    return league, team_name, calendar

# ============================
# Publication Sports
# ============================
@register_downloader("publicationsports")
def download_publicationsports(league, team_name, url, team_filter):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            stealth_sync(page)
            page.goto(url, timeout=90000)
            page.wait_for_load_state("networkidle")
            html = page.content()
            browser.close()
        calendar = parse_publicationsports(html, team_filter, league)
        return league, team_name, calendar
    except Exception as e:
        print("Error parsing Publication Sports HTML:", e)
        return league, team_name, None

# ============================
# SHL JSON
# ============================
@register_downloader("shl")
def download_shl(league, team_name, url, team_filter):
    try:
        raw_json = fetch_json(url)
    except:
        return league, team_name, None
    calendar = parse_shl_json_to_calendar(league, team_name, raw_json)
    return league, team_name, calendar

# ============================
# UFA JSON  (FIX)
# ============================
@register_downloader("ufa")
def download_ufa(league, team_name, url, team_filter):
    try:
        raw_json = fetch_json(url)
    except:
        return league, team_name, None
    calendar = parse_ufa_json_to_calendar(raw_json)
    return league, team_name, calendar

# ============================
# VHL HTML
# ============================
@register_downloader("vhl")
def download_vhl(league, team_name, url, team_filter):
    try:
        html = fetch_html(url)
    except:
        return league, team_name, None
    calendar = parse_vhl_html(html, team_name, team_filter)
    return league, team_name, calendar
