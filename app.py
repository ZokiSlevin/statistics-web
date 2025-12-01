import os
import glob
import pandas as pd
import streamlit as st

# ---------------------------------------------------------
# PUTEVI
# ---------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

IMAGES_DIR = os.path.join(BASE_DIR, "images")
LOGO_PATH = os.path.join(IMAGES_DIR, "me.png")

ORG_FILE = "Organizations.xlsx"
ORG_SHEET = "Organizations"

# ---------------------------------------------------------
# UČITAVANJE PODATAKA
# ---------------------------------------------------------

@st.cache_data(show_spinner="Učitavanje statistike...")
def load_all_data():
    """
    Učitava sve *_statistika.csv iz data/ + Organizations.xlsx
    i vraća jedan merged DataFrame.
    """
    pattern = os.path.join(DATA_DIR, "*_statistika.csv")
    files = sorted(glob.glob(pattern))

    if not files:
        return None, "Nisam našao statističke CSV datoteke u 'data/'"

    frames = []

    for path in files:
        year = os.path.basename(path).split("_")[0]  # npr. 2018

        # CSV je puno brži i ne treba sheet_name
        try:
            df = pd.read_csv(path, dtype=str, encoding="utf-8")
        except Exception as e:
            return None, f"Problem pri čitanju CSV datoteke {os.path.basename(path)}: {e}"

        # normalizacija CUSTOMERID na 9 znamenki (da se može spojiti s CODE)
        if "CUSTOMERID" in df.columns:
            df["CUSTOMERID"] = df["CUSTOMERID"].astype(str).str.zfill(9)
        else:
            return None, f"U datoteci {os.path.basename(path)} nedostaje kolona 'CUSTOMERID'."

        # normalizacija MANUFACTURERCODE na 2 znamenke
        if "MANUFACTURERCODE" in df.columns:
            df["MANUFACTURERCODE"] = df["MANUFACTURERCODE"].astype(str).str.zfill(2)

        df["YEAR"] = year
        frames.append(df)

    stat_df = pd.concat(frames, ignore_index=True)

    # organizations
    org_path = os.path.join(DATA_DIR, ORG_FILE)
    if not os.path.exists(org_path):
        return None, f"Nisam našao {ORG_FILE} u 'data/'"

    try:
        org_df = pd.read_excel(org_path, sheet_name=ORG_SHEET, dtype=str)
    except Exception as e:
        return None, f"Problem pri čitanju {ORG_FILE}: {e}"

    # normalizacija CODE na 9 znamenki i preimenovanje u CUSTOMERID
    if "CODE" not in org_df.columns:
        return None, f"U {ORG_FILE} nedostaje kolona 'CODE'."

    org_df["CODE"] = org_df["CODE"].astype(str).str.zfill(9)
    org_df = org_df.rename(columns={"CODE": "CUSTOMERID"})

    # merge
    full_df = stat_df.merge(org_df, on="CUSTOMERID", how="left")

    return full_df, None

# ---------------------------------------------------------
# UI - HEADER
# ---------------------------------------------------------

def render_header():
    col_left, col_center, col_right = st.columns([1, 3, 1])

    with col_left:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, use_container_width=True)
        else:
            st.write("")

    with col_center:
        st.markdown(
            """
            <div style="text-align: center; padding-top: 10px;">
                <div style="font-size: 28px; font-weight: 700; margin-bottom: 4px;">
                    MEVA - Pretraga VIN brojeva
                </div>
                <div style="font-size: 14px; color: #666;">
                    Web verzija alata za pregled kalkulacija po VIN broju
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_right:
        st.write("")  # za sada prazno, možeš kasnije dodati drugi logo

# ---------------------------------------------------------
# GLAVNI DIO APLIKACIJE
# ---------------------------------------------------------

def main():
    st.set_page_config(
        page_title="MEVA - Pretraga VIN brojeva",
        layout="wide",
    )

    render_header()
    st.markdown("---")

    # stil za gumbe i input (zelena / crvena kao u Tkinteru)
    st.markdown(
        """
        <style>
        /* VIN text input – smanji širinu */
        input[type="text"] {
            width: 320px !important;
        }

        /* Pretraži (drugi stupac u redu) */
        div[data-testid="column"]:nth-of-type(2) button {
            background-color: #006400;
            color: whitesmoke;
            border: 1px solid #006400;
            width: 130px !important;
            height: 38px !important;
        }
        div[data-testid="column"]:nth-of-type(2) button:hover {
            background-color: whitesmoke;
            color: #006400;
            border: 1px solid #006400;
        }

        /* Očisti (treći stupac u redu) */
        div[data-testid="column"]:nth-of-type(3) button {
            background-color: #ff6666;
            color: whitesmoke;
            border: 1px solid #ff6666;
            width: 130px !important;
            height: 38px !important;
        }
        div[data-testid="column"]:nth-of-type(3) button:hover {
            background-color: whitesmoke;
            color: #ff6666;
            border: 1px solid #ff6666;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    df, err = load_all_data()
    if err:
        st.error(err)
        st.stop()

    if df is None or df.empty:
        st.warning("Nema podataka za prikaz.")
        st.stop()

    # ------------------- FILTER / PRETRAGA -------------------
    st.markdown("### 🔎 Pretraga po VIN broju")

    if "vin_input" not in st.session_state:
        st.session_state.vin_input = ""

    col1, col2, col3 = st.columns([6, 2, 2])

    with col1:
        vin = st.text_input(
            "Unesi VIN (točan match):",
            value=st.session_state.vin_input,
            max_chars=50,
            key="vin_input"
        )

    with col2:
        search_clicked = st.button("🔍 Pretraži", use_container_width=True)

    with col3:
        clear_clicked = st.button("🧹 Očisti", use_container_width=True)

    # logika za Očisti
    if clear_clicked:
        st.session_state.vin_input = ""
        st.experimental_rerun()

    # pretraga se radi SAMO kad se klikne Pretraži i VIN nije prazan
    if search_clicked and vin.strip():
        vin_query = vin.strip().upper()

        if "VINNUMBER" not in df.columns:
            st.error("U podacima ne postoji kolona 'VINNUMBER'.")
            st.stop()

        mask = df["VINNUMBER"].fillna("").str.upper() == vin_query
        results = df[mask].copy()

        if results.empty:
            st.info(f"Nema rezultata za VIN: **{vin_query}**")
            return

        # sortiraj po godini i eventualno po TSTAMP-u ako postoji
        sort_cols = []
        if "YEAR" in results.columns:
            sort_cols.append("YEAR")
        if "TSTAMP" in results.columns:
            sort_cols.append("TSTAMP")

        if sort_cols:
            results = results.sort_values(sort_cols)

        st.markdown(f"### Rezultati za VIN: `{vin_query}`")
        st.metric("Broj pronađenih zapisa", len(results))

        # grupiranje po godinama - kao blokovi "Godina 2018, 2019..."
        if "YEAR" in results.columns:
            years = list(results["YEAR"].dropna().unique())
            years.sort()

            for year in years:
                sub = results[results["YEAR"] == year].copy()
                st.markdown(f"#### Godina {year}")

                # ako ne želiš prikazivati YEAR kolonu u tablici:
                if "YEAR" in sub.columns:
                    sub = sub.drop(columns=["YEAR"])

                st.dataframe(sub, use_container_width=True)
        else:
            # fallback – bez YEAR kolone, samo jedna tablica
            st.dataframe(results, use_container_width=True)
    else:
        st.info("Unesi VIN broj i klikni **Pretraži**.")

if __name__ == "__main__":
    main()
