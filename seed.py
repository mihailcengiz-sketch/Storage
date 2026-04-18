"""
Portföy başlangıç verilerini yükler.
Bir kere çalıştırın: python seed.py

NOT: Aşağıdaki miktar ve fiyatlar TAHMINIDIR.
     Gerçek alım bilgilerinizle eşleşmiyorsa:
     1. Uygulamayı açın → İşlem Geçmişi → ilgili kayıtları silin
     2. Alım Ekle sayfasından gerçek değerlerle yeniden girin.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from database import init_db, add_transaction

# Portföy verileri - ekran görüntülerinden hesaplanan yaklaşık değerler
# Sütunlar: (sembol, coin_id, miktar, alış_fiyatı, tarih)
SEED_DATA = [
    # Büyük cap coinler
    ("BTC",   "bitcoin",            0.0004,         102500.0,      "2024-11-01"),
    ("ETH",   "ethereum",           3.5,             2384.0,       "2024-01-15"),
    ("BNB",   "binancecoin",        1.5,             420.0,        "2024-01-15"),
    ("SOL",   "solana",             5.0,             200.0,        "2024-01-15"),
    ("XRP",   "ripple",             750.0,           0.75,         "2024-01-15"),
    ("ADA",   "cardano",            4500.0,          0.25,         "2024-01-15"),
    ("DOGE",  "dogecoin",           8000.0,          0.12,         "2024-01-15"),
    ("AVAX",  "avalanche-2",        75.0,            40.0,         "2024-01-15"),

    # Layer 2 / Ekosistem
    ("ARB",   "arbitrum",           8000.0,          0.055,        "2024-01-15"),
    ("OP",    "optimism",           4000.0,          0.16,         "2024-03-01"),
    ("APT",   "aptos",              1000.0,          0.96,         "2024-01-15"),
    ("SUI",   "sui",                1800.0,          0.60,         "2024-01-15"),
    ("ZRO",   "layerzero",          300.0,           2.40,         "2024-06-20"),
    ("ZK",    "zksync",             15000.0,         0.025,        "2024-06-17"),
    ("MON",   "monad-2",            15000.0,         0.038,        "2025-01-01"),

    # Meme coinler
    ("SHIB",  "shiba-inu",          12_000_000.0,    0.000028,     "2024-01-15"),
    ("PEPE",  "pepe",               80_000_000.0,    0.0000120,    "2024-03-01"),
    ("FLOKI", "floki",              800_000.0,       0.000153,     "2024-01-15"),

    # DeFi / Altyapı
    ("IOTA",  "iota",               100_000.0,       0.0062,       "2024-01-15"),
    ("WLD",   "worldcoin-wld",      1200.0,          0.78,         "2024-03-15"),
    ("CETUS", "cetus-protocol",     90_000.0,        0.0064,       "2024-04-01"),
    ("COTI",  "coti",               90_000.0,        0.0031,       "2024-01-15"),
    ("ACH",   "alchemy-pay",        130_000.0,       0.0031,       "2024-01-15"),

    # Stablecoinler
    ("USDT",  "tether",             1.0,             1.0,          "2024-01-15"),
    ("USDC",  "usd-coin",           91.0,            1.0,          "2024-01-15"),
    ("USDbC", "bridged-usdc-base",  63.0,            1.0,          "2024-01-15"),

    # Diğer
    ("MIU",   "miu-token",          40_000_000.0,    0.0000102,    "2024-06-01"),
    ("NFP",   "nfprompt",           4500.0,          0.090,        "2024-06-01"),
    ("KILO",  "kiloex",             5000.0,          0.00079,      "2025-02-01"),
    ("GUN",   "gunz",               300.0,           0.0140,       "2025-01-01"),
]


def main():
    print("Portföy veritabanı oluşturuluyor...")
    conn = init_db()

    added = 0
    for symbol, coin_id, qty, price, tx_date in SEED_DATA:
        try:
            add_transaction(
                conn, symbol, coin_id, "buy",
                qty, price, tx_date,
                notes="Başlangıç verisi - düzenleyebilirsiniz"
            )
            total = qty * price
            print(f"  ✓ {symbol:6s}  {qty:>18,.4f}  @ ${price:>12,.8f}  = ${total:>10,.2f}")
            added += 1
        except Exception as e:
            print(f"  ✗ {symbol}: {e}")

    conn.close()
    print(f"\n{added} işlem eklendi.")
    print("\nŞimdi uygulamayı başlatın:")
    print("  streamlit run app.py")


if __name__ == "__main__":
    main()
