import time
import requests
import pandas as pd
import streamlit as st

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
CRYPTOCOMPARE_BASE = "https://min-api.cryptocompare.com/data"

_last_request_time = 0
_MIN_INTERVAL = 2.0  # seconds between CoinGecko calls to stay under 30/min


def _cg_get(path: str, params: dict = None) -> dict | list | None:
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    try:
        resp = requests.get(f"{COINGECKO_BASE}{path}", params=params, timeout=15)
        _last_request_time = time.time()
        if resp.status_code == 429:
            st.warning("⚠️ CoinGecko API rate limit aşıldı. 60 saniye bekleyip tekrar deneyin.")
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        st.warning("⚠️ CoinGecko API zaman aşımı. İnternet bağlantınızı kontrol edin.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"API hatası: {e}")
        return None


@st.cache_data(ttl=120, show_spinner=False)
def get_market_data(coin_ids: tuple) -> dict:
    """Fetch current prices and 24h changes for a list of coin IDs."""
    if not coin_ids:
        return {}
    ids_param = ",".join(coin_ids)
    data = _cg_get("/coins/markets", {
        "vs_currency": "usd",
        "ids": ids_param,
        "order": "market_cap_desc",
        "per_page": 250,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h",
    })
    if not data:
        return {}
    return {item["id"]: item for item in data}


@st.cache_data(ttl=3600, show_spinner=False)
def get_price_history(coin_id: str, days: int = 30) -> pd.DataFrame:
    """Fetch daily price history for a single coin."""
    data = _cg_get(f"/coins/{coin_id}/market_chart", {
        "vs_currency": "usd",
        "days": days,
        "interval": "daily",
    })
    if not data or "prices" not in data:
        return pd.DataFrame(columns=["date", "price"])
    df = pd.DataFrame(data["prices"], columns=["timestamp_ms", "price"])
    df["date"] = pd.to_datetime(df["timestamp_ms"], unit="ms")
    return df[["date", "price"]]


@st.cache_data(ttl=86400, show_spinner=False)
def search_coins(query: str) -> list[dict]:
    """Search CoinGecko for coins by name or symbol."""
    data = _cg_get("/search", {"query": query})
    if not data:
        return []
    return data.get("coins", [])[:10]


@st.cache_data(ttl=60, show_spinner=False)
def get_simple_price(coin_id: str) -> float | None:
    """Fetch the current USD price for a single coin."""
    data = _cg_get("/simple/price", {
        "ids": coin_id,
        "vs_currencies": "usd",
    })
    if not data or coin_id not in data:
        return None
    return data[coin_id]["usd"]


@st.cache_data(ttl=900, show_spinner=False)
def get_news(categories: str = "") -> list[dict]:
    """Fetch latest crypto news from CryptoCompare."""
    params = {"lang": "EN", "sortOrder": "latest"}
    if categories:
        params["categories"] = categories
    try:
        resp = requests.get(
            f"{CRYPTOCOMPARE_BASE}/v2/news/",
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("Data", [])
    except requests.exceptions.Timeout:
        st.warning("⚠️ Haber servisi zaman aşımı.")
        return []
    except requests.exceptions.RequestException as e:
        st.error(f"Haber hatası: {e}")
        return []
