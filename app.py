import streamlit as st
import pandas as pd
from datetime import datetime, date

from database import (
    init_db, add_transaction, delete_transaction,
    get_all_transactions, get_current_holdings,
    save_snapshot, get_snapshots,
)
from api import get_market_data, get_price_history, search_coins, get_simple_price, get_news
from charts import (
    make_donut_chart, make_pnl_bar_chart, make_portfolio_line_chart,
    make_24h_change_chart, make_allocation_table_fig,
)
from utils import COIN_ID_MAP, COIN_NAMES, fmt_usd, fmt_pct, fmt_qty, smart_price_format

st.set_page_config(
    page_title="Kripto Portföy",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stMetric"] {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 12px;
    padding: 16px 20px;
}
[data-testid="stMetricLabel"] { font-size: 0.78rem; color: #8B949E; }
[data-testid="stMetricValue"] { font-size: 1.45rem; font-weight: 700; }
[data-testid="block-container"] { padding-top: 1.5rem; }
div[data-testid="stHorizontalBlock"] { gap: 0.75rem; }
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }
.stAlert { border-radius: 8px; }
h1 { color: #00D4FF; font-size: 1.6rem !important; }
h2 { font-size: 1.2rem !important; }
</style>
""", unsafe_allow_html=True)

# ── DB init (once per session) ───────────────────────────────────────────────
if "conn" not in st.session_state:
    st.session_state.conn = init_db()

conn = st.session_state.conn


# ── Helper: enrich holdings with live prices ─────────────────────────────────
def enrich_holdings(holdings: pd.DataFrame, prices: dict) -> pd.DataFrame:
    if holdings.empty:
        return holdings
    rows = []
    for _, row in holdings.iterrows():
        p = prices.get(row["coin_id"], {})
        current_price = p.get("current_price", 0.0)
        current_value = row["net_quantity"] * current_price
        cost = row["total_cost_usd"] or 0.0
        pnl_usd = current_value - cost
        pnl_pct = (pnl_usd / cost * 100) if cost > 0 else 0.0
        change_24h = p.get("price_change_percentage_24h", 0.0) or 0.0
        rows.append({
            **row.to_dict(),
            "current_price": current_price,
            "current_value": current_value,
            "pnl_usd": pnl_usd,
            "pnl_pct": pnl_pct,
            "change_24h": change_24h,
            "image": p.get("image", ""),
        })
    return pd.DataFrame(rows)


# ════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ════════════════════════════════════════════════════════════════════════════
def page_dashboard():
    st.title("📊 Portföy Dashboard")

    holdings = get_current_holdings(conn)

    if holdings.empty:
        st.info("Portföyünüzde henüz coin yok. **Alım Ekle** sayfasından coin ekleyin.")
        return

    coin_ids = tuple(holdings["coin_id"].tolist())

    with st.spinner("Fiyatlar güncelleniyor..."):
        prices = get_market_data(coin_ids)

    enriched = enrich_holdings(holdings, prices)

    total_value   = enriched["current_value"].sum()
    total_cost    = enriched["total_cost_usd"].sum()
    total_pnl     = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0.0

    # 24h portfolio change
    change_24h_usd = 0.0
    for _, row in enriched.iterrows():
        chg = row["change_24h"]
        if chg != 0:
            old_price = row["current_price"] / (1 + chg / 100)
            change_24h_usd += (row["current_price"] - old_price) * row["net_quantity"]

    # Save today's snapshot
    today_str = date.today().isoformat()
    if total_value > 0:
        save_snapshot(conn, today_str, total_value, total_cost)

    # ── Metric cards ──────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Portföy Değeri",  f"${total_value:,.2f}")
    c2.metric("💸 Toplam Maliyet",  f"${total_cost:,.2f}")
    c3.metric(
        "📈 Kar / Zarar",
        f"${total_pnl:+,.2f}",
        delta=f"{total_pnl_pct:+.2f}%",
        delta_color="normal",
    )
    c4.metric(
        "⚡ 24s Değişim",
        f"${change_24h_usd:+,.2f}",
        delta=None,
    )

    st.divider()

    # ── Charts row 1: line + donut ─────────────────────────────────────────
    col_l, col_r = st.columns([1.6, 1])

    with col_l:
        snapshots = get_snapshots(conn, days=365)
        fig_line = make_portfolio_line_chart(snapshots)
        st.plotly_chart(fig_line, use_container_width=True)

    with col_r:
        labels = enriched["coin_symbol"].tolist()
        values = enriched["current_value"].tolist()
        fig_donut = make_donut_chart(labels, values, total_value)
        st.plotly_chart(fig_donut, use_container_width=True)

    # ── Charts row 2: P&L bar + 24h change ────────────────────────────────
    col_l2, col_r2 = st.columns(2)

    with col_l2:
        fig_pnl = make_pnl_bar_chart(
            enriched["coin_symbol"].tolist(),
            enriched["pnl_usd"].tolist(),
        )
        st.plotly_chart(fig_pnl, use_container_width=True)

    with col_r2:
        fig_24h = make_24h_change_chart(
            enriched["coin_symbol"].tolist(),
            enriched["change_24h"].tolist(),
        )
        st.plotly_chart(fig_24h, use_container_width=True)

    # ── Treemap ────────────────────────────────────────────────────────────
    fig_tree = make_allocation_table_fig(enriched)
    st.plotly_chart(fig_tree, use_container_width=True)

    # ── Holdings table ─────────────────────────────────────────────────────
    st.subheader("Varlık Listesi")
    display = enriched[[
        "coin_symbol", "net_quantity", "avg_buy_price",
        "current_price", "current_value", "pnl_usd", "pnl_pct", "change_24h",
    ]].copy()
    display.columns = [
        "Coin", "Miktar", "Ort. Maliyet ($)",
        "Güncel Fiyat ($)", "Değer ($)", "K/Z ($)", "K/Z (%)", "24s (%)",
    ]
    display = display.sort_values("Değer ($)", ascending=False)

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Miktar":           st.column_config.NumberColumn(format="%.6f"),
            "Ort. Maliyet ($)": st.column_config.NumberColumn(format="$%.6f"),
            "Güncel Fiyat ($)": st.column_config.NumberColumn(format="$%.6f"),
            "Değer ($)":        st.column_config.NumberColumn(format="$%.2f"),
            "K/Z ($)":          st.column_config.NumberColumn(format="$%+.2f"),
            "K/Z (%)":          st.column_config.NumberColumn(format="%+.2f%%"),
            "24s (%)":          st.column_config.NumberColumn(format="%+.2f%%"),
        },
    )


# ════════════════════════════════════════════════════════════════════════════
# PAGE: ADD POSITION
# ════════════════════════════════════════════════════════════════════════════
def page_add():
    st.title("➕ Alım Ekle")

    known_symbols = sorted(COIN_ID_MAP.keys())
    all_options   = known_symbols + ["🔍 Diğer (ara)..."]

    with st.form("buy_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            coin_choice = st.selectbox("Coin", options=all_options)
            quantity    = st.number_input("Miktar", min_value=0.0, value=0.0,
                                          format="%.8f", step=0.00000001)

        with col2:
            price_usd = st.number_input("Alış Fiyatı (USD)", min_value=0.0,
                                         value=0.0, format="%.8f", step=0.00000001)
            tx_date   = st.date_input("Tarih", value=date.today())

        notes = st.text_input("Not (isteğe bağlı)", placeholder="Örn: Binance'ten aldım")

        # Manual entry for unknown coins
        custom_symbol = ""
        custom_coin_id = ""
        if coin_choice == "🔍 Diğer (ara)...":
            st.markdown("---")
            custom_symbol = st.text_input("Coin sembolü (örn: INJ)", "").upper()
            custom_coin_id = st.text_input(
                "CoinGecko ID (örn: injective-protocol)",
                "",
                help="https://www.coingecko.com adresinden coin ID'sini bulabilirsiniz.",
            )

        submitted = st.form_submit_button("💾 Kaydet", use_container_width=True, type="primary")

        if submitted:
            if coin_choice == "🔍 Diğer (ara)...":
                symbol  = custom_symbol.strip()
                coin_id = custom_coin_id.strip()
                if not symbol or not coin_id:
                    st.error("Lütfen sembol ve CoinGecko ID girin.")
                    return
            else:
                symbol  = coin_choice
                coin_id = COIN_ID_MAP[coin_choice]

            if quantity <= 0:
                st.error("Miktar 0'dan büyük olmalı.")
                return
            if price_usd <= 0:
                st.error("Alış fiyatı 0'dan büyük olmalı.")
                return

            add_transaction(conn, symbol, coin_id, "buy",
                            quantity, price_usd, tx_date.isoformat(), notes)
            total = quantity * price_usd
            st.success(f"✅ {quantity:.8f} {symbol} @ ${price_usd:.6f} eklendi! "
                       f"Toplam maliyet: ${total:,.2f}")
            st.cache_data.clear()

    # Quick price lookup (outside form)
    st.divider()
    st.subheader("📡 Anlık Fiyat Sorgula")
    lookup_sym = st.selectbox("Coin seçin", options=known_symbols, key="lookup")
    if st.button("Fiyatı Çek"):
        cid = COIN_ID_MAP[lookup_sym]
        with st.spinner(f"{lookup_sym} fiyatı alınıyor..."):
            price = get_simple_price(cid)
        if price is not None:
            st.success(f"**{lookup_sym}** güncel fiyat: **${price:,.8f}**")
        else:
            st.error("Fiyat alınamadı.")


# ════════════════════════════════════════════════════════════════════════════
# PAGE: SELL
# ════════════════════════════════════════════════════════════════════════════
def page_sell():
    st.title("💸 Satış Yap")

    holdings = get_current_holdings(conn)
    if holdings.empty:
        st.info("Portföyünüzde satılacak coin yok.")
        return

    symbols = holdings["coin_symbol"].tolist()
    avg_prices = dict(zip(holdings["coin_symbol"], holdings["avg_buy_price"]))
    qtys       = dict(zip(holdings["coin_symbol"], holdings["net_quantity"]))
    coin_ids   = dict(zip(holdings["coin_symbol"], holdings["coin_id"]))

    with st.form("sell_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            coin_sym = st.selectbox("Satılacak Coin", options=symbols)
            max_qty  = qtys.get(coin_sym, 0.0)
            st.caption(f"Mevcut: **{fmt_qty(max_qty)} {coin_sym}**  |  "
                       f"Ort. Maliyet: **${avg_prices.get(coin_sym, 0):.6f}**")
            quantity = st.number_input("Satış Miktarı", min_value=0.0,
                                        max_value=float(max_qty), value=0.0,
                                        format="%.8f", step=0.00000001)

        with col2:
            price_usd = st.number_input("Satış Fiyatı (USD)", min_value=0.0,
                                         value=0.0, format="%.8f", step=0.00000001)
            tx_date   = st.date_input("Tarih", value=date.today())

        notes = st.text_input("Not", placeholder="Örn: Hedef fiyata ulaştı")

        submitted = st.form_submit_button("💸 Sat", use_container_width=True, type="primary")

        if submitted:
            if quantity <= 0:
                st.error("Satış miktarı 0'dan büyük olmalı.")
                return
            if quantity > max_qty:
                st.error(f"Yetersiz bakiye. Mevcut: {fmt_qty(max_qty)} {coin_sym}")
                return
            if price_usd <= 0:
                st.error("Satış fiyatı 0'dan büyük olmalı.")
                return

            avg_cost = avg_prices.get(coin_sym, 0.0)
            realized_pnl = (price_usd - avg_cost) * quantity

            add_transaction(conn, coin_sym, coin_ids[coin_sym], "sell",
                            quantity, price_usd, tx_date.isoformat(), notes)

            pnl_color = "🟢" if realized_pnl >= 0 else "🔴"
            st.success(
                f"✅ {fmt_qty(quantity)} {coin_sym} @ ${price_usd:.6f} satıldı!  \n"
                f"{pnl_color} Gerçekleşen K/Z: **${realized_pnl:+,.2f}**"
            )
            st.cache_data.clear()


# ════════════════════════════════════════════════════════════════════════════
# PAGE: NEWS
# ════════════════════════════════════════════════════════════════════════════
def page_news():
    st.title("📰 Kripto Haberleri")

    holdings = get_current_holdings(conn)
    if holdings.empty:
        categories = "BTC,ETH,SOL"
    else:
        categories = ",".join(holdings["coin_symbol"].unique()[:20])

    col1, col2 = st.columns([3, 1])
    with col1:
        search_term = st.text_input("Haberlerde ara...", placeholder="Bitcoin, Ethereum...")
    with col2:
        count = st.selectbox("Göster", [10, 25, 50], index=0)

    with st.spinner("Haberler yükleniyor..."):
        news_data = get_news(categories=categories)

    if not news_data:
        st.warning("Haber yüklenemedi. Lütfen daha sonra tekrar deneyin.")
        return

    # Filter by search
    if search_term:
        q = search_term.lower()
        news_data = [
            n for n in news_data
            if q in n.get("title", "").lower() or q in n.get("body", "").lower()
        ]

    st.caption(f"{len(news_data)} haber bulundu. Son güncelleme: {datetime.now().strftime('%H:%M')}")
    st.divider()

    for item in news_data[:count]:
        pub_dt = datetime.fromtimestamp(item.get("published_on", 0))
        with st.container(border=True):
            img_col, txt_col = st.columns([0.12, 0.88])
            with img_col:
                img = item.get("imageurl", "")
                if img:
                    st.image(img, width=72)
            with txt_col:
                cats = item.get("categories", "").replace("|", " · ")
                st.markdown(f"**[{item['title']}]({item['url']})**")
                st.caption(
                    f"🗞 {item.get('source', '')}  ·  "
                    f"🕐 {pub_dt.strftime('%d %b %Y %H:%M')}  ·  "
                    f"🏷 {cats}"
                )
                body = item.get("body", "")
                if body:
                    st.write(body[:220] + ("..." if len(body) > 220 else ""))


# ════════════════════════════════════════════════════════════════════════════
# PAGE: TRANSACTION HISTORY
# ════════════════════════════════════════════════════════════════════════════
def page_history():
    st.title("📋 İşlem Geçmişi")

    df = get_all_transactions(conn)
    if df.empty:
        st.info("Henüz işlem kaydı yok.")
        return

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_type = st.multiselect(
            "İşlem Tipi", ["buy", "sell"], default=["buy", "sell"],
            format_func=lambda x: "🟢 Alım" if x == "buy" else "🔴 Satış",
        )
    with col2:
        filter_coin = st.multiselect("Coin", options=sorted(df["coin_symbol"].unique()))
    with col3:
        min_date = pd.to_datetime(df["tx_date"].min()).date()
        max_date = pd.to_datetime(df["tx_date"].max()).date()
        date_range = st.date_input("Tarih Aralığı", value=(min_date, max_date))

    # Apply filters
    mask = df["tx_type"].isin(filter_type)
    if filter_coin:
        mask &= df["coin_symbol"].isin(filter_coin)
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        mask &= df["tx_date"] >= date_range[0].isoformat()
        mask &= df["tx_date"] <= date_range[1].isoformat()
    filtered = df[mask].copy()

    # Summary
    buys  = filtered[filtered["tx_type"] == "buy"]
    sells = filtered[filtered["tx_type"] == "sell"]
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Toplam İşlem", len(filtered))
    mc2.metric("Alım Toplamı",  f"${(buys['quantity']  * buys['price_usd']).sum():,.2f}")
    mc3.metric("Satış Toplamı", f"${(sells['quantity'] * sells['price_usd']).sum():,.2f}")

    st.divider()

    # Display with delete checkboxes
    display = filtered[["id", "tx_date", "tx_type", "coin_symbol",
                          "quantity", "price_usd", "notes"]].copy()
    display["total_usd"] = display["quantity"] * display["price_usd"]
    display["tx_type"]   = display["tx_type"].map({"buy": "🟢 Alım", "sell": "🔴 Satış"})
    display.rename(columns={
        "id": "ID", "tx_date": "Tarih", "tx_type": "Tür",
        "coin_symbol": "Coin", "quantity": "Miktar",
        "price_usd": "Fiyat ($)", "total_usd": "Toplam ($)", "notes": "Not",
    }, inplace=True)

    edited = st.data_editor(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID":        st.column_config.NumberColumn(disabled=True),
            "Tarih":     st.column_config.TextColumn(disabled=True),
            "Tür":       st.column_config.TextColumn(disabled=True),
            "Coin":      st.column_config.TextColumn(disabled=True),
            "Miktar":    st.column_config.NumberColumn(format="%.8f", disabled=True),
            "Fiyat ($)": st.column_config.NumberColumn(format="$%.8f", disabled=True),
            "Toplam ($)":st.column_config.NumberColumn(format="$%.2f", disabled=True),
            "Not":       st.column_config.TextColumn(disabled=True),
        },
        num_rows="dynamic",
    )

    # Delete by ID input
    st.divider()
    st.subheader("İşlem Sil")
    del_id = st.number_input("Silinecek işlem ID", min_value=1, step=1, value=1)
    if st.button("🗑️ İşlemi Sil", type="secondary"):
        if del_id in filtered["ID"].values if "ID" in filtered.columns else df["id"].values:
            delete_transaction(conn, int(del_id))
            st.success(f"İşlem #{del_id} silindi.")
            st.cache_data.clear()
            st.rerun()
        else:
            st.error("Bu ID mevcut işlemler arasında bulunamadı.")


# ════════════════════════════════════════════════════════════════════════════
# SIDEBAR + NAVIGATION
# ════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 💎 Kripto Portföy")
    st.caption("Portföy Takip Uygulaması")
    st.divider()

    if st.button("🔄 Fiyatları Yenile", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    holdings_sidebar = get_current_holdings(conn)
    if not holdings_sidebar.empty:
        st.caption(f"**{len(holdings_sidebar)}** coin takip ediliyor")
    st.caption(f"Son güncelleme: {datetime.now().strftime('%H:%M:%S')}")

pages = {
    "📊 Dashboard":     page_dashboard,
    "➕ Alım Ekle":     page_add,
    "💸 Satış Yap":     page_sell,
    "📰 Haberler":      page_news,
    "📋 İşlem Geçmişi": page_history,
}

selected = st.sidebar.radio(
    "Sayfa",
    list(pages.keys()),
    label_visibility="collapsed",
)

pages[selected]()
