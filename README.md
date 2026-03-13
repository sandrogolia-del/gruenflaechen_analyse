# 🌳 Grünflächen-Erreichbarkeitsanalyse

Bevölkerungsgewichtete Analyse der Erreichbarkeit von Naherholungsgebieten in deutschen Städten – basierend auf OpenStreetMap und Zensus 2022.

---

## 📊 Beispielergebnisse: Bonn

| Kategorie | Einwohner | Anteil |
|-----------|-----------|--------|
| Sehr gut (0–200m) | 161.622 | 50,3% |
| Gut (200–400m) | 104.914 | 32,6% |
| Mittel (400–600m) | 38.466 | 12,0% |
| Wenig (>600m) | 16.349 | 5,1% |

**Gewichteter Versorgungsindex: 61,1%**  
**Flächenbasiert (500m Puffer): 95,3%** der Stadtfläche liegt innerhalb von 500m einer Grünfläche  
**331** Naherholungsgebiete · **923m** maximale Distanz · **213m** mittlere Distanz

---

## 🗺️ Karten

### Erreichbarkeitskarte
![Erreichbarkeitskarte Bonn](outputs/bonn_erreichbarkeit.png)

### Bevölkerungskarte
![Bevölkerungskarte Bonn](outputs/bonn_bevoelkerung.png)

---

## 🚀 Verwendung

### Voraussetzungen

```bash
pip install -r requirements.txt
```

### Zensus-Daten

Die Zensus-CSV wird benötigt aber nicht mitgeliefert (Dateigröße > 100 MB).

**Download:** [destatis.de](https://www.destatis.de/static/DE/zensus/gitterdaten/Zensus2022_Bevoelkerungszahl.zip)  
**Dateiname:** `Zensus2022_Bevoelkerungszahl_100m-Gitter.csv`  
**Speicherort:** `data/raw/Zensus2022_Bevoelkerungszahl_100m-Gitter.csv`

---

### Option A – Streamlit App (empfohlen)

Die einfachste Möglichkeit – keine Python-Kenntnisse erforderlich:

Die Datei "app.py" aus dem repository auf den Desktop laden. Dann in cmd: 

```bash
streamlit run app.py
```

Die App öffnet sich automatisch im Browser. Dort kannst du:
- Eine beliebige deutsche Stadt eingeben
- Den Pfad zur Zensus-CSV eintragen
- Distanzkategorien per Schieberegler anpassen
- Beide Karten direkt herunterladen
- Ein GeoPackage mit allen Analysedaten exportieren

### Option B – Jupyter Notebook

Für Nutzer die den Code nachvollziehen oder anpassen möchten:

1. Öffne `notebooks/gruenflaechen_analyse.ipynb` in Jupyter, JupyterLab oder VS Code
2. Passe in **Zelle 1** an:

```python
STADT = "Bonn, Deutschland"   # beliebige deutsche Stadt
BASIS = r"C:\Pfad\zu\deinem\Projektordner"
```

3. **Kernel → Restart & Run All**

---

### Unterstützte Städte

Das Projekt funktioniert für alle deutschen Städte. Die Darstellung passt sich automatisch an:
- **Kreisfreie Städte** (z.B. Bonn, Dortmund, Berlin): Stadtteile bzw. Stadtbezirke werden angezeigt
- **Kreisangehörige Orte** (z.B. Pulheim): nur Stadtgrenze

> Die Qualität der Stadtteilgrenzen hängt von der OSM-Datenlage ab. In kleineren Städten können Stadtteile unvollständig eingetragen sein.

---

## 🔧 Methodik

### Versorgungsindex

Für jede Einwohnerzelle (100×100m) des Zensus 2022 wird die Luftliniendistanz
zur nächsten Grünfläche berechnet. Daraus ergibt sich ein linearer Versorgungsindex:

- **0m** → Index 1,0 (bestens versorgt)
- **600m** → Index 0,0 (unversorgt)
- Alles dazwischen wird proportional interpoliert

### Einwohnergewichtung

Der Gesamtindex wird **einwohnergewichtet** berechnet – das bedeutet: eine
Rasterzelle mit 50 Einwohnern hat mehr Einfluss auf das Gesamtergebnis als eine
Zelle mit 5 Einwohnern. Der Index spiegelt damit wider wie gut die **Menschen**
versorgt sind, nicht wie gut die **Fläche** versorgt ist.

Zum Vergleich für Bonn:
- **Flächenbasiert:** 95,3% der Stadtfläche liegt innerhalb von 500m einer Grünfläche
- **Einwohnergewichtet:** 61,1% – weil dicht besiedelte Bereiche mit schlechter
  Versorgung stärker ins Gewicht fallen

### Naherholungsgebiete

Folgende OSM-Tags werden als Naherholungsgebiete klassifiziert
(Mindestfläche: 5.000 m²):

| OSM-Tag | Beschreibung |
|---------|-------------|
| `leisure=park` | Öffentliche Parks |
| `leisure=garden` | Gärten (inkl. Kleingärten) |
| `leisure=nature_reserve` | Naturschutzgebiete |
| `landuse=forest` | Wälder |
| `landuse=grass` | Grünflächen und Wiesen |
| `landuse=recreation_ground` | Ausgewiesene Erholungsflächen |

### Distanzkategorien

| Kategorie | Distanz | Versorgungsindex |
|-----------|---------|-----------------|
| Sehr gut | 0–200m | 1,0–0,67 |
| Gut | 200–400m | 0,67–0,33 |
| Mittel | 400–600m | 0,33–0,0 |
| Wenig | >600m | 0,0 |

### ⚠️ Methodische Einschränkungen

- **Stadtumland wird nicht berücksichtigt** – Einwohner in Randlagen können
  eine schlechtere Versorgung angezeigt bekommen als in der Realität, da
  Grünflächen im direkten Umland nicht einbezogen werden
- **Nur kartierte OSM-Flächen fließen ein** – bewirtschaftete Flächen die
  in der Realität als Naherholungsgebiet genutzt werden (z.B. Feldwege,
  das Meßdorfer Feld in Bonn) werden nicht erfasst
- **Luftlinie statt Gehweg** – die tatsächliche Wegstrecke kann durch
  Barrieren wie Straßen, Gleise oder Bebauung länger sein
- **OSM-Datenlage** – Vollständigkeit und Aktualität der Grünflächen
  variiert je nach Stadt

---

## 📁 Projektstruktur

```
gruenflaechen-analyse/
├── app.py                                # Streamlit App
├── requirements.txt                      # Abhängigkeiten
├── notebooks/
│   └── gruenflaechen_analyse.ipynb       # Jupyter Notebook
├── outputs/
│   ├── bonn_erreichbarkeit.png           # Erreichbarkeitskarte
│   └── bonn_bevoelkerung.png             # Bevölkerungskarte
├── data/
│   └── raw/                              # Zensus-CSV hier ablegen (nicht im Repo)
└── README.md
```

---

## 🛠️ Tools & Datenquellen

| Tool / Daten | Verwendung |
|---|---|
| [OSMnx](https://osmnx.readthedocs.io) | OpenStreetMap-Daten laden |
| [GeoPandas](https://geopandas.org) | Geodatenverarbeitung |
| [Matplotlib](https://matplotlib.org) | Kartenerstellung |
| [Streamlit](https://streamlit.io) | Web-App |
| [Zensus 2022](https://www.zensus2022.de) | Bevölkerungsdaten (100m-Raster) |
| [OpenStreetMap](https://www.openstreetmap.org) | Grünflächen & Verwaltungsgrenzen |

---

## 📄 Lizenz

Dieses Projekt steht unter der [MIT Lizenz](LICENSE).  
Kartendaten © OpenStreetMap contributors · Zensus 2022 © Statistische Ämter des Bundes und der Länder
