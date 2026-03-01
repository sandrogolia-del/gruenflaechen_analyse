# 🌳 Grünflächen-Erreichbarkeitsanalyse

Bevölkerungsgewichtete Analyse der fußläufigen Erreichbarkeit von Naherholungsgebieten in deutschen Städten – basierend auf OpenStreetMap und Zensus 2022.

---

## 📊 Beispielergebnisse: Bonn

| Kategorie | Einwohner | Anteil |
|-----------|-----------|--------|
| Sehr gut (0–200m) | 139.028 | 43,3% |
| Gut (200–400m) | 100.726 | 31,3% |
| Mittel (400–600m) | 51.129 | 15,9% |
| Wenig (>600m) | 30.468 | 9,5% |

**Gewichteter Versorgungsindex: 55,2%**  
Niemand wohnt weiter als 1 km von einem Naherholungsgebiet entfernt.

---

## 🗺️ Karten

### Erreichbarkeitskarte
![Erreichbarkeitskarte Bonn](outputs/bonn_erreichbarkeit.png)

### Bevölkerungskarte
![Bevölkerungskarte Bonn](outputs/bonn_bevoelkerung.png)

---

## 🔧 Methodik

**Versorgungsindex:** Linearer Index basierend auf Luftliniendistanz zur nächsten Grünfläche.
- 0m → Index 1,0 (bestens versorgt)
- 600m → Index 0,0 (unversorgt)

**Bevölkerungsgewichtung:** Jede Rasterzelle (100×100m) des Zensus 2022 wird mit ihrem Versorgungsindex gewichtet. Der gewichtete Durchschnitt ergibt die Gesamtversorgungsquote der Stadt.

**Naherholungsgebiete:** Wälder, Parks und Naturschutzgebiete aus OpenStreetMap mit einer Mindestfläche von 5.000 m².

---

## 🚀 Verwendung

### Voraussetzungen

```bash
pip install osmnx geopandas matplotlib pandas shapely
```

### Zensus-Daten

Die Zensus-CSV wird benötigt aber nicht mitgeliefert (Dateigröße > 100 MB).

**Download:** [destatis.de](https://www.destatis.de/static/DE/zensus/gitterdaten/Zensus2022_Bevoelkerungszahl.zip)  
**Dateiname:** `Zensus2022_Bevoelkerungszahl_100m-Gitter.csv`  
**Speicherort:** `data/raw/Zensus2022_Bevoelkerungszahl_100m-Gitter.csv`

### Konfiguration

Öffne `notebooks/gruenflaechen_analyse.ipynb` und passe in **Zelle 1** an:

```python
STADT = "Bonn, Deutschland"   # beliebige deutsche Stadt
BASIS = r"C:\Pfad\zu\deinem\Projektordner"
```

Anschließend: **Kernel → Restart & Run All**

### Unterstützte Städte

Das Notebook funktioniert für alle deutschen Städte. Die Darstellung passt sich automatisch an:
- **Kreisfreie Städte** (z.B. Bonn, Dortmund, Berlin): Stadtteile bzw. Stadtbezirke werden angezeigt
- **Kreisangehörige Orte** (z.B. Pulheim): nur Stadtgrenze

> Die Qualität der Stadtteilgrenzen hängt von der OSM-Datenlage ab. In kleineren Städten können Stadtteile unvollständig eingetragen sein.

---

## 📁 Projektstruktur

```
gruenflaechen-analyse/
├── notebooks/
│   └── gruenflaechen_analyse.ipynb   # Hauptanalyse
├── outputs/
│   ├── bonn_erreichbarkeit.png       # Erreichbarkeitskarte
│   └── bonn_bevoelkerung.png         # Bevölkerungskarte
├── data/
│   └── raw/                          # Zensus-CSV hier ablegen (nicht im Repo)
└── README.md
```

---

## 🛠️ Tools & Datenquellen

| Tool / Daten | Verwendung |
|---|---|
| [OSMnx](https://osmnx.readthedocs.io) | OpenStreetMap-Daten laden |
| [GeoPandas](https://geopandas.org) | Geodatenverarbeitung |
| [Matplotlib](https://matplotlib.org) | Kartenerstellung |
| [Zensus 2022](https://www.zensus2022.de) | Bevölkerungsdaten (100m-Raster) |
| [OpenStreetMap](https://www.openstreetmap.org) | Grünflächen & Verwaltungsgrenzen |

---

## 📄 Lizenz

Dieses Projekt steht unter der [MIT Lizenz](LICENSE).  
Kartendaten © OpenStreetMap contributors · Zensus 2022 © Statistische Ämter des Bundes und der Länder
