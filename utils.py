COIN_ID_MAP = {
    "BTC":   "bitcoin",
    "ETH":   "ethereum",
    "SOL":   "solana",
    "BNB":   "binancecoin",
    "XRP":   "ripple",
    "ADA":   "cardano",
    "DOGE":  "dogecoin",
    "AVAX":  "avalanche-2",
    "SHIB":  "shiba-inu",
    "PEPE":  "pepe",
    "ARB":   "arbitrum",
    "OP":    "optimism",
    "APT":   "aptos",
    "SUI":   "sui",
    "IOTA":  "iota",
    "WLD":   "worldcoin-wld",
    "ZRO":   "layerzero",
    "ZK":    "zksync",
    "MON":   "monad-2",
    "CETUS": "cetus-protocol",
    "FLOKI": "floki",
    "USDT":  "tether",
    "USDC":  "usd-coin",
    "USDbC": "bridged-usdc-base",
    "COTI":  "coti",
    "NFP":   "nfprompt",
    "ACH":   "alchemy-pay",
    "MIU":   "miu-token",
    "KILO":  "kiloex",
    "GUN":   "gunz",
}

COIN_NAMES = {
    "BTC":   "Bitcoin",
    "ETH":   "Ethereum",
    "SOL":   "Solana",
    "BNB":   "BNB",
    "XRP":   "XRP",
    "ADA":   "Cardano",
    "DOGE":  "Dogecoin",
    "AVAX":  "Avalanche",
    "SHIB":  "Shiba Inu",
    "PEPE":  "Pepe",
    "ARB":   "Arbitrum",
    "OP":    "Optimism",
    "APT":   "Aptos",
    "SUI":   "Sui",
    "IOTA":  "IOTA",
    "WLD":   "Worldcoin",
    "ZRO":   "LayerZero",
    "ZK":    "zkSync",
    "MON":   "Monad",
    "CETUS": "Cetus Protocol",
    "FLOKI": "FLOKI",
    "USDT":  "Tether",
    "USDC":  "USD Coin",
    "USDbC": "Bridged USDC",
    "COTI":  "COTI",
    "NFP":   "NFPrompt",
    "ACH":   "Alchemy Pay",
    "MIU":   "MIU",
    "KILO":  "KiloEx",
    "GUN":   "GUNZ",
}


def fmt_usd(value: float, decimals: int = 2) -> str:
    if abs(value) >= 1_000_000:
        return f"${value/1_000_000:,.2f}M"
    if abs(value) >= 1_000:
        return f"${value:,.{decimals}f}"
    return f"${value:,.{max(decimals, 4)}f}"


def fmt_pct(value: float) -> str:
    return f"{value:+.2f}%"


def fmt_qty(value: float) -> str:
    if value >= 1:
        return f"{value:,.4f}"
    return f"{value:.8f}".rstrip("0").rstrip(".")


def smart_price_format(price: float) -> str:
    if price >= 1000:
        return f"${price:,.2f}"
    if price >= 1:
        return f"${price:,.4f}"
    if price >= 0.0001:
        return f"${price:.6f}"
    return f"${price:.10f}"
