import os
import streamlit as st
import osmnx as ox
import geopandas as gpd
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Patch
import pandas as pd
from shapely.geometry import box
from io import BytesIO

# ============================================================
# SEITENKONFIGURATION
# ============================================================
st.set_page_config(
    page_title="Grünflächen-Erreichbarkeitsanalyse",
    page_icon="🌳",
    layout="wide"
)

st.title("🌳 Grünflächen-Erreichbarkeitsanalyse")
st.markdown(
    "Bevölkerungsgewichtete Analyse der Erreichbarkeit von Naherholungsgebieten "
    "für deutsche Städte – basierend auf OpenStreetMap und Zensus 2022."
)

# ============================================================
# SIDEBAR – KONFIGURATION
# ============================================================
with st.sidebar:
    st.header("⚙️ Konfiguration")

    stadt = st.text_input(
        "Stadt",
        value="Bonn, Deutschland",
        help="Beliebige deutsche Stadt, z.B. 'Berlin, Deutschland'"
    )

    zensus_path = st.text_input(
        "Pfad zur Zensus-CSV",
        value=r"C:\Pfad\zur\Zensus2022_Bevoelkerungszahl_100m-Gitter.csv",
        help="Download: https://www.destatis.de/static/DE/zensus/gitterdaten/Zensus2022_Bevoelkerungszahl.zip"
    )

    st.markdown("---")
    st.subheader("📏 Distanzkategorien (Meter)")

    distanz_sehr_gut = st.slider("Sehr gut (0 – x m)", 100, 400, 200, step=50)
    distanz_gut = st.slider("Gut (x – y m)", 200, 600, 400, step=50)
    distanz_mittel = st.slider("Mittel (y – z m)", 400, 1000, 600, step=50)
    max_distanz = distanz_mittel

    st.markdown("---")
    st.subheader("🌿 Mindestfläche")
    min_flaeche = st.slider(
        "Mindestgröße Naherholungsgebiete (m²)",
        1000, 20000, 5000, step=1000
    )

    analyse_starten = st.button("🚀 Analyse starten", use_container_width=True)

# ============================================================
# SESSION STATE – verhindert Reset bei Download-Klicks
# ============================================================
if analyse_starten:
    st.session_state["analyse_fertig"] = True

if not st.session_state.get("analyse_fertig", False):
    st.info(
        "**So funktioniert es:**\n\n"
        "1. Lade die Zensus-CSV herunter: "
        "[destatis.de](https://www.destatis.de/static/DE/zensus/gitterdaten/Zensus2022_Bevoelkerungszahl.zip)\n"
        "2. Trage den Pfad zur CSV-Datei links ein\n"
        "3. Wähle deine Stadt und passe die Parameter an\n"
        "4. Klicke auf **Analyse starten**\n\n"
        "⚠️ Die Analyse dauert je nach Stadt 2–5 Minuten."
    )
    st.stop()

# ============================================================
# ANALYSE
# ============================================================
stadtname = stadt.split(",")[0].strip().lower().replace(" ", "_")

with st.spinner("Lade Stadtgrenze..."):
    try:
        stadtgrenze = ox.geocode_to_gdf(stadt)
    except Exception as e:
        st.error(f"Stadt nicht gefunden: {e}")
        st.stop()

with st.spinner("Lade Grünflächen aus OpenStreetMap..."):
    tags = {
        "leisure": ["park", "garden", "nature_reserve"],
        "landuse": ["grass", "forest", "recreation_ground"]
    }
    gruenflaechen = ox.features_from_place(stadt, tags=tags)
    gruenflaechen = gruenflaechen[
        gruenflaechen.geometry.type.isin(["Polygon", "MultiPolygon"])
    ].copy()
    gruenflaechen = gruenflaechen.set_crs("EPSG:4326", allow_override=True)

with st.spinner("Lade Straßen..."):
    strassen = ox.features_from_place(
        stadt, {"highway": ["motorway", "trunk", "primary", "secondary"]})
    strassen = strassen[strassen.geometry.type == "LineString"].copy()

with st.spinner("Prüfe Stadttyp und lade Verwaltungseinheiten..."):
    place_rank = int(stadtgrenze["place_rank"].values[0]) if "place_rank" in stadtgrenze.columns else 16
    ist_kreisfreie_stadt = place_rank <= 12

    stadtteile = gpd.GeoDataFrame()
    level_gefunden = None
    verwaltungseinheit = None

    if ist_kreisfreie_stadt:
        alle_grenzen = ox.features_from_place(stadt, {"boundary": "administrative"})
        for level in [10, 9, 8]:
            kandidaten_poly = alle_grenzen[
                (alle_grenzen.geometry.type.isin(["Polygon", "MultiPolygon"])) &
                (alle_grenzen["admin_level"].astype(str) == str(level))
            ].copy()
            kandidaten_punkt = alle_grenzen[
                (alle_grenzen.geometry.type == "Point") &
                (alle_grenzen["admin_level"].astype(str) == str(level))
            ].copy()
            kandidaten = pd.concat([kandidaten_poly, kandidaten_punkt])
            if len(kandidaten) == 0:
                continue
            kandidaten = gpd.GeoDataFrame(kandidaten, crs="EPSG:4326")
            kandidaten_proj = kandidaten.to_crs("EPSG:25832")
            stadtgrenze_proj = stadtgrenze.to_crs("EPSG:25832").union_all()
            maske = kandidaten_proj.geometry.centroid.within(stadtgrenze_proj)
            kandidaten = kandidaten[maske].copy()
            if len(kandidaten) >= 2:
                stadtteile = kandidaten
                level_gefunden = level
                break

        if level_gefunden == 10:
            verwaltungseinheit = "Stadtteile"
        elif level_gefunden == 9:
            verwaltungseinheit = "Stadtbezirke"
        elif level_gefunden == 8:
            verwaltungseinheit = "Ortsteile"

with st.spinner("Filtere Naherholungsgebiete..."):
    gruenflaechen_proj = gruenflaechen.to_crs("EPSG:25832").copy()
    gruenflaechen_proj["flaeche_m2"] = gruenflaechen_proj.geometry.area
    relevante_typen = gruenflaechen_proj[
        (
            gruenflaechen_proj.get("landuse", pd.Series()).isin(["forest", "grass", "recreation_ground"]) |
            gruenflaechen_proj.get("leisure", pd.Series()).isin(["park", "garden", "nature_reserve"])
        ) &
        (gruenflaechen_proj["flaeche_m2"] > min_flaeche)
    ].copy()
    relevante_typen["kategorie"] = "Naherholungsgebiet"

with st.spinner("Berechne Distanzen und lade Zensus-Daten..."):
    gruenflaechen_gesamt = relevante_typen.geometry.union_all()
    stadt_25832 = stadtgrenze.to_crs("EPSG:25832")

    try:
        zensus = pd.read_csv(zensus_path, sep=";", encoding="utf-8")
    except Exception as e:
        st.error(f"Zensus-CSV nicht gefunden: {e}")
        st.stop()

    zensus_clean = zensus[zensus["Einwohner"] > 0].copy()
    zensus_gdf = gpd.GeoDataFrame(
        zensus_clean,
        geometry=gpd.points_from_xy(zensus_clean["x_mp_100m"],
                                     zensus_clean["y_mp_100m"]),
        crs="EPSG:3035"
    ).to_crs("EPSG:25832")

    zensus_stadt = gpd.clip(zensus_gdf, stadt_25832).copy()
    zensus_stadt["distanz_m"] = zensus_stadt.geometry.distance(gruenflaechen_gesamt)

with st.spinner("Berechne Versorgungsindex..."):
    zensus_stadt["versorgungsindex"] = (
        1 - (zensus_stadt["distanz_m"] / max_distanz)
    ).clip(0, 1)
    zensus_stadt["gewichtete_versorgung"] = (
        zensus_stadt["versorgungsindex"] * zensus_stadt["Einwohner"]
    )

    einwohner_gesamt = zensus_stadt["Einwohner"].sum()
    versorgungsquote = zensus_stadt["gewichtete_versorgung"].sum() / einwohner_gesamt * 100

    sehr_gut = zensus_stadt[zensus_stadt["distanz_m"] <= distanz_sehr_gut]["Einwohner"].sum()
    gut = zensus_stadt[
        (zensus_stadt["distanz_m"] > distanz_sehr_gut) &
        (zensus_stadt["distanz_m"] <= distanz_gut)]["Einwohner"].sum()
    mittel = zensus_stadt[
        (zensus_stadt["distanz_m"] > distanz_gut) &
        (zensus_stadt["distanz_m"] <= distanz_mittel)]["Einwohner"].sum()
    weniger_gut = zensus_stadt[zensus_stadt["distanz_m"] > distanz_mittel]["Einwohner"].sum()

    gruenflaechen_puffer = gruenflaechen_gesamt.buffer(500)
    schnitt = gruenflaechen_puffer.intersection(stadt_25832.geometry.iloc[0])
    anteil = schnitt.area / stadt_25832.geometry.iloc[0].area * 100

# ============================================================
# ERGEBNISSE ANZEIGEN
# ============================================================
st.success("✅ Analyse abgeschlossen!")
st.markdown(f"## 📊 Ergebnisse für {stadt}")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Versorgungsindex", f"{versorgungsquote:.1f}%", help="Einwohnergewichtet")
col2.metric(f"Sehr gut (0–{distanz_sehr_gut}m)", f"{sehr_gut/einwohner_gesamt*100:.1f}%")
col3.metric(f"Gut ({distanz_sehr_gut}–{distanz_gut}m)", f"{gut/einwohner_gesamt*100:.1f}%")
col4.metric(f"Mittel ({distanz_gut}–{distanz_mittel}m)", f"{mittel/einwohner_gesamt*100:.1f}%")
col5.metric(f"Wenig (>{distanz_mittel}m)", f"{weniger_gut/einwohner_gesamt*100:.1f}%")

st.markdown(
    f"**Flächenbasiert (500m Puffer):** {anteil:.1f}% der Stadtfläche · "
    f"**Naherholungsgebiete:** {len(relevante_typen)} · "
    f"**Max. Distanz:** {zensus_stadt['distanz_m'].max():.0f}m · "
    f"**Mittlere Distanz:** {zensus_stadt['distanz_m'].mean():.0f}m"
)

st.markdown("---")

# ============================================================
# HILFSFUNKTION: GEODATAFRAME BEREINIGEN
# ============================================================
def bereinige_geodataframe(gdf):
    # GeoPackage unterstützt nur eine Geometriespalte pro Layer
    geo_spalten = gdf.select_dtypes(include="geometry").columns.tolist()
    geo_spalten.remove("geometry")
    gdf = gdf.drop(columns=geo_spalten, errors="ignore").copy()

    # Gemischte Typen zu String konvertieren
    for col in list(gdf.columns):
        if col == "geometry":
            continue
        try:
            if gdf[col].dtype == object:
                gdf[col] = gdf[col].astype(str)
        except Exception:
            gdf = gdf.drop(columns=[col])

    # Spalten mit ungültigen GeoPackage-Feldnamen entfernen
    ungueltige_zeichen = [":", " ", "-", "/", "\\"]
    spalten_behalten = []
    for col in gdf.columns:
        if col == "geometry":
            spalten_behalten.append(col)
            continue
        if any(z in col for z in ungueltige_zeichen):
            continue
        spalten_behalten.append(col)

    return gdf[spalten_behalten]


# ============================================================
# HILFSFUNKTION: KARTEN ERSTELLEN
# ============================================================
def erstelle_erreichbarkeitskarte():
    stadtgrenze_4326 = stadtgrenze.to_crs("EPSG:4326")
    naherholung_clip = relevante_typen.to_crs("EPSG:4326").clip(stadtgrenze_4326)

    zonen = [
        (distanz_sehr_gut, "#1a9641", f"Sehr gut (0-{distanz_sehr_gut}m) · {sehr_gut/einwohner_gesamt*100:.1f}%"),
        (distanz_gut,      "#a6d96a", f"Gut ({distanz_sehr_gut}-{distanz_gut}m) · {gut/einwohner_gesamt*100:.1f}%"),
        (distanz_mittel,   "#ffffbf", f"Mittel ({distanz_gut}-{distanz_mittel}m) · {mittel/einwohner_gesamt*100:.1f}%"),
        (1000,             "#fdae61", f"Wenig ({distanz_mittel}-1000m) · {weniger_gut/einwohner_gesamt*100:.1f}%"),
    ]

    fig = plt.figure(figsize=(14, 12))
    gs = fig.add_gridspec(1, 2, width_ratios=[4, 1])
    ax = fig.add_subplot(gs[0])
    ax_legend = fig.add_subplot(gs[1])
    ax_legend.set_axis_off()

    stadtgrenze_4326.plot(ax=ax, color="#d7191c", edgecolor="none", zorder=1)

    for distanz, farbe, label in reversed(zonen):
        puffer = gruenflaechen_gesamt.buffer(distanz)
        puffer_gdf = gpd.GeoDataFrame(
            geometry=[puffer], crs="EPSG:25832"
        ).to_crs("EPSG:4326").clip(stadtgrenze_4326)
        puffer_gdf.plot(ax=ax, color=farbe, alpha=0.8, zorder=2)

    naherholung_clip.plot(ax=ax, color="#2d6a4f", alpha=0.8, zorder=3)
    strassen.to_crs("EPSG:4326").clip(stadtgrenze_4326).plot(
        ax=ax, color="#888888", linewidth=0.8, alpha=0.6, zorder=4)

    if verwaltungseinheit:
        stadtteile_clip = stadtteile.to_crs("EPSG:4326").clip(stadtgrenze_4326)
        poly_mask = stadtteile_clip.geometry.type.isin(["Polygon", "MultiPolygon"])
        if poly_mask.any():
            stadtteile_clip[poly_mask].plot(ax=ax, color="none",
                edgecolor="#333333", linewidth=0.8, alpha=0.9, zorder=5)

    stadtgrenze_4326.plot(ax=ax, color="none", edgecolor="black", linewidth=2, zorder=6)

    legende = [
        Patch(facecolor="#1a9641", alpha=0.8, label=f"Sehr gut (0-{distanz_sehr_gut}m) · {sehr_gut/einwohner_gesamt*100:.1f}%"),
        Patch(facecolor="#a6d96a", alpha=0.8, label=f"Gut ({distanz_sehr_gut}-{distanz_gut}m) · {gut/einwohner_gesamt*100:.1f}%"),
        Patch(facecolor="#ffffbf", alpha=0.8, label=f"Mittel ({distanz_gut}-{distanz_mittel}m) · {mittel/einwohner_gesamt*100:.1f}%"),
        Patch(facecolor="#fdae61", alpha=0.8, label=f"Wenig ({distanz_mittel}-1000m) · {weniger_gut/einwohner_gesamt*100:.1f}%"),
        Patch(facecolor="#d7191c", alpha=0.8, label="Außerhalb · 0.0%"),
        Patch(facecolor="#2d6a4f", alpha=0.8, label="Naherholungsgebiete"),
    ]
    if verwaltungseinheit:
        legende.append(Patch(facecolor="none", edgecolor="#333333", label=verwaltungseinheit))

    ax_legend.legend(handles=legende, fontsize=11, loc="center",
                     framealpha=0.9, edgecolor="gray",
                     title="Versorgungsqualität", title_fontsize=12)

    ax.set_title(
        f"Erreichbarkeit von Naherholungsgebieten – {stadt}\n"
        f"Luftliniendistanz zur nächsten OSM-kartierten Grünfläche "
        f"(Mindestfläche: {min_flaeche:,} m²) · Datengrundlage: OpenStreetMap, Zensus 2022",
        fontsize=13, fontweight="bold", pad=20)
    ax.set_axis_off()
    ax.annotate("© OpenStreetMap contributors · Zensus 2022",
                xy=(0.01, 0.01), xycoords="axes fraction", fontsize=9, color="gray")

    if verwaltungseinheit:
        for idx, row in stadtteile_clip.iterrows():
            punkt = row.geometry.centroid
            if pd.isna(row.get("name", None)):
                continue
            ax.annotate(text=row["name"], xy=(punkt.x, punkt.y),
                        fontsize=9, color="black", alpha=0.9,
                        ha="center", va="center", fontweight="bold",
                        path_effects=[pe.withStroke(linewidth=2, foreground="white")])

    plt.tight_layout()
    return fig


def erstelle_bevoelkerungskarte():
    def punkt_zu_zelle(punkt):
        x, y = punkt.x, punkt.y
        return box(x - 50, y - 50, x + 50, y + 50)

    zensus_stadt["zelle"] = zensus_stadt.geometry.apply(punkt_zu_zelle)
    zensus_poly = zensus_stadt.set_geometry("zelle")

    fig = plt.figure(figsize=(14, 12))
    gs = fig.add_gridspec(1, 2, width_ratios=[4, 1])
    ax = fig.add_subplot(gs[0])
    ax_legend = fig.add_subplot(gs[1])
    ax_legend.set_axis_off()

    stadtgrenze.to_crs("EPSG:25832").plot(ax=ax, color="#f0f0f0", edgecolor="none", zorder=1)

    zensus_poly.plot(ax=ax, column="versorgungsindex", cmap="RdYlGn",
                     vmin=0, vmax=1, alpha=0.85, zorder=2, legend=True,
                     legend_kwds={
                         "label": "Versorgungsindex  ◀  0 = unversorgt (>600m)          1 = bestens versorgt (0m)  ▶",
                         "orientation": "horizontal", "shrink": 0.6, "pad": 0.02
                     })

    relevante_typen.to_crs("EPSG:25832").clip(stadt_25832).plot(
        ax=ax, color="#2d6a4f", alpha=0.8, zorder=3)
    strassen.to_crs("EPSG:25832").clip(stadt_25832).plot(
        ax=ax, color="#888888", linewidth=0.8, alpha=0.6, zorder=4)

    if verwaltungseinheit:
        poly_mask = stadtteile.geometry.type.isin(["Polygon", "MultiPolygon"])
        if poly_mask.any():
            stadtteile[poly_mask].to_crs("EPSG:25832").clip(stadt_25832).plot(
                ax=ax, color="none", edgecolor="#333333",
                linewidth=0.8, alpha=0.9, zorder=5)

    stadtgrenze.to_crs("EPSG:25832").plot(
        ax=ax, color="none", edgecolor="black", linewidth=2, zorder=6)

    legende = [Patch(facecolor="#2d6a4f", alpha=0.8, label="Naherholungsgebiete")]
    if verwaltungseinheit:
        legende.append(Patch(facecolor="none", edgecolor="#333333", label=verwaltungseinheit))

    ax_legend.legend(handles=legende, fontsize=11, loc="center",
                     framealpha=0.9, edgecolor="gray",
                     title="Legende", title_fontsize=12)

    ax.set_title(
        f"Versorgungsqualität mit Naherholungsgebieten (bevölkerungsgewichtet) – {stadt}\n"
        f"Sehr gut (0-{distanz_sehr_gut}m): {sehr_gut/einwohner_gesamt*100:.1f}% · "
        f"Gut ({distanz_sehr_gut}-{distanz_gut}m): {gut/einwohner_gesamt*100:.1f}% · "
        f"Mittel ({distanz_gut}-{distanz_mittel}m): {mittel/einwohner_gesamt*100:.1f}% · "
        f"Wenig (>{distanz_mittel}m): {weniger_gut/einwohner_gesamt*100:.1f}%",
        fontsize=13, fontweight="bold", pad=20)
    ax.set_axis_off()
    ax.annotate("© OpenStreetMap contributors · Zensus 2022",
                xy=(0.01, 0.01), xycoords="axes fraction", fontsize=9, color="gray")

    if verwaltungseinheit:
        for idx, row in stadtteile.to_crs("EPSG:25832").iterrows():
            punkt = row.geometry.centroid
            if pd.isna(row.get("name", None)):
                continue
            ax.annotate(text=row["name"], xy=(punkt.x, punkt.y),
                        fontsize=9, color="black", alpha=0.9,
                        ha="center", va="center", fontweight="bold",
                        path_effects=[pe.withStroke(linewidth=2, foreground="white")])

    plt.tight_layout()
    return fig


# ============================================================
# KARTEN ANZEIGEN
# ============================================================
col_karte1, col_karte2 = st.columns(2)

with col_karte1:
    st.subheader("🗺️ Erreichbarkeitskarte")
    with st.spinner("Erstelle Erreichbarkeitskarte..."):
        fig1 = erstelle_erreichbarkeitskarte()
        st.pyplot(fig1)

        buf1 = BytesIO()
        fig1.savefig(buf1, format="png", dpi=300, bbox_inches="tight")
        buf1.seek(0)

        st.download_button(
            label="⬇️ PNG herunterladen",
            data=buf1,
            file_name=f"{stadtname}_erreichbarkeit.png",
            mime="image/png",
            use_container_width=True
        )
    plt.close(fig1)

with col_karte2:
    st.subheader("👥 Bevölkerungskarte")
    with st.spinner("Erstelle Bevölkerungskarte..."):
        fig2 = erstelle_bevoelkerungskarte()
        st.pyplot(fig2)

        buf2 = BytesIO()
        fig2.savefig(buf2, format="png", dpi=300, bbox_inches="tight")
        buf2.seek(0)

        st.download_button(
            label="⬇️ PNG herunterladen",
            data=buf2,
            file_name=f"{stadtname}_bevoelkerung.png",
            mime="image/png",
            use_container_width=True
        )
    plt.close(fig2)

# ============================================================
# GEOPACKAGE DOWNLOAD
# ============================================================
st.markdown("---")
st.subheader("💾 Daten exportieren")

with st.spinner("Erstelle GeoPackage..."):
    gpkg_pfad = os.path.join(os.path.expanduser("~"), f"{stadtname}_analyse_temp.gpkg")

    stadtgrenze.to_file(gpkg_pfad, layer="stadtgrenze", driver="GPKG")
    gruenflaechen.to_crs("EPSG:25832").pipe(bereinige_geodataframe).to_file(
        gpkg_pfad, layer="gruenflaechen", driver="GPKG")
    relevante_typen.pipe(bereinige_geodataframe).to_file(
        gpkg_pfad, layer="naherholungsgebiete", driver="GPKG")
    zensus_stadt.pipe(bereinige_geodataframe).to_file(
        gpkg_pfad, layer="zensus", driver="GPKG")

    with open(gpkg_pfad, "rb") as f:
        gpkg_bytes = f.read()
    os.remove(gpkg_pfad)

st.download_button(
    label="⬇️ GeoPackage herunterladen (.gpkg)",
    data=gpkg_bytes,
    file_name=f"{stadtname}_analyse.gpkg",
    mime="application/geopackage+sqlite3",
    use_container_width=True
)

# ============================================================
# METHODISCHE HINWEISE
# ============================================================
st.markdown("---")
with st.expander("⚠️ Methodische Hinweise"):
    st.markdown("""
    - **Stadtumland wird nicht berücksichtigt** – Einwohner in Randlagen können schlechter bewertet sein als in der Realität
    - **Nur kartierte OSM-Flächen fließen ein** – bewirtschaftete Flächen die als Naherholungsgebiet genutzt werden (z.B. Meßdorfer Feld, Bonn) werden nicht erfasst
    - **Luftlinie statt Gehweg** – die tatsächliche Wegstrecke kann durch Barrieren länger sein
    - **OSM-Datenlage** – Vollständigkeit und Aktualität der Grünflächen variiert je nach Stadt
    """)
