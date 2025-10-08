# 📚 eBook Manager

Ein intelligentes Tool-Set zur Organisation und Verwaltung Ihrer EPUB-Sammlung mit automatischer Genre-Klassifizierung über die Google Books API.

## ✨ Features

### 🖥️ **eBook Importer GUI** (`ebook_importer_gui.py`)
Moderne grafische Benutzeroberfläche zum Import neuer eBooks:
- ✅ Automatische Metadaten-Extraktion aus EPUB-Dateien
- ✅ Genre-Klassifizierung via Google Books API
- ✅ Intelligentes Caching (nutzt `enriched_metadata.json`)
- ✅ Titel-Bereinigung (entfernt Serien-Nummern wie "001 - ")
- ✅ Lernfähiges System (speichert Ihre Genre-Zuordnungen)
- ✅ Organisation nach Genre/Autor
- ✅ Automatische Bereinigung leerer Ordner

### 📊 **Metadaten-Anreicherung** (`ebook_metadata_enricher.py`)
Batch-Processing für große Sammlungen:
- ✅ Verarbeitet hunderte EPUBs automatisch
- ✅ Speichert Metadaten in `enriched_metadata.json`
- ✅ API-Rate-Limiting für Google Books
- ✅ Cache-System für bereits abgefragte Bücher

### 🔧 **eBook Reorganizer** (`ebook_reorganize.py`)
Reorganisiert bestehende Sammlungen:
- ✅ Verschiebt Bücher in Genre/Autor-Struktur
- ✅ Duplikat-Erkennung
- ✅ Trockenlauf-Modus (Preview)
- ✅ Ausführlicher Reorganisations-Report

### 🧹 **Cleanup Tool** (`cleanup_empty_dirs.py`)
Bereinigt leere Ordner:
- ✅ Findet und löscht leere Verzeichnisse
- ✅ Trockenlauf-Modus mit Bericht
- ✅ Statistiken nach Genre

## 🚀 Installation

### Voraussetzungen
- Python 3.8+
- Tkinter (für GUI, meist vorinstalliert)

### Installation

```bash
# Repository klonen
git clone https://github.com/dasarne/ebook-manager.git
cd ebook-manager

# Optional: Virtual Environment erstellen
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# oder
venv\Scripts\activate  # Windows

# (Keine externen Abhängigkeiten nötig - nutzt nur Python Standard Library!)
```

## 📖 Verwendung

### eBook Importer GUI (empfohlen für Einsteiger)

```bash
python3 ebook_importer_gui.py
```

**Workflow:**
1. **Buchsammlung** auswählen (Zielordner)
2. **Neue Bücher** auswählen (Quellordner mit EPUBs)
3. Optionen anpassen:
   - Verschieben vs. Kopieren
   - Google Books API aktivieren
   - Nach Autor organisieren
4. **Import starten**
5. Bei unbekannten Kategorien: Genre zuordnen (lernt für nächstes Mal!)

**Beispiel-Verzeichnisstruktur nach Import:**
```
eBooks_neu/
├── Science Fiction/
│   └── Asimov, Isaac/
│       └── Foundation.epub
├── Belletristik/
│   └── Eschbach, Andreas/
│       └── Die Auferstehung.epub
└── Sachbücher/
    └── Harari, Yuval Noah/
        └── Sapiens.epub
```

### Metadaten-Anreicherung (Batch-Processing)

```bash
# Sammlung analysieren und Metadaten speichern
python3 ebook_metadata_enricher.py /pfad/zu/epub/sammlung

# Mit eigenem Output-Dateinamen
python3 ebook_metadata_enricher.py /pfad/zu/epub/sammlung --output meine_metadaten.json

# Erste 50 Bücher (zum Testen)
python3 ebook_metadata_enricher.py /pfad/zu/epub/sammlung --max-books 50
```

**Erzeugt:** `enriched_metadata.json` - wird automatisch von der GUI genutzt!

### eBook Reorganizer

```bash
# Preview (Trockenlauf)
python3 ebook_reorganize.py /pfad/zu/epub/sammlung

# Tatsächlich reorganisieren
python3 ebook_reorganize.py /pfad/zu/epub/sammlung --execute
```

### Cleanup Tool

```bash
# Preview leere Ordner
python3 cleanup_empty_dirs.py /pfad/zu/epub/sammlung

# Leere Ordner löschen
python3 cleanup_empty_dirs.py /pfad/zu/epub/sammlung --execute
```

## 🧠 Intelligentes System

### Caching-Strategie
1. **enriched_metadata.json** - Langzeit-Cache aller Bücher
2. **~/.cache/ebook_metadata/** - Google Books API-Responses
3. **~/.ebook_genre_mappings.json** - Ihre gelernten Genre-Zuordnungen

### Genre-Klassifizierung (Multi-Strategie)
1. ✅ Benutzerdefinierte Mappings (höchste Priorität)
2. ✅ Vordefinierte Mappings (DE + EN)
3. ✅ Flexible Teilstring-Matches
4. ✅ Broad Keywords
5. ✅ Google Books API (nur wenn nötig)

### Titel-Bereinigung
Automatisches Entfernen störender Präfixe bei Google Books Suche:
- `"001 - Die Auferstehung"` → `"Die Auferstehung"`
- `"Band 1 - Der Herr der Ringe"` → `"Der Herr der Ringe"`
- `"Volume 2: The Return"` → `"The Return"`

## 🎯 Unterstützte Genres

- Belletristik
- Science Fiction
- Fantasy
- Krimi/Thriller
- Liebesromane
- Biografien/Memoiren
- Sachbücher
- Ratgeber
- Wirtschaft
- Jugendbuch
- Kinderbuch
- Sonstiges

## 📁 Projektstruktur

```
ebook-manager/
├── ebook_importer_gui.py       # Hauptanwendung (GUI)
├── ebook_metadata_enricher.py  # Batch Metadaten-Extraktion
├── ebook_reorganize.py         # Sammlung reorganisieren
├── cleanup_empty_dirs.py       # Leere Ordner bereinigen
├── README.md                   # Diese Datei
├── LICENSE                     # MIT Lizenz
└── .gitignore                  # Git Ignore-Regeln
```

## 🔒 Datenschutz

- ✅ Alle Daten bleiben lokal auf Ihrem Computer
- ✅ Google Books API wird nur für Metadaten-Abfrage genutzt
- ✅ Keine Telemetrie oder Tracking
- ✅ Open Source - Code ist einsehbar

## 🤝 Beitragen

Contributions sind willkommen! Bitte:

1. Fork das Repository
2. Erstelle einen Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit deine Änderungen (`git commit -m 'Add some AmazingFeature'`)
4. Push zum Branch (`git push origin feature/AmazingFeature`)
5. Öffne einen Pull Request

## 📝 Lizenz

Dieses Projekt ist unter der MIT Lizenz lizenziert - siehe [LICENSE](LICENSE) Datei für Details.

## 🐛 Bekannte Einschränkungen

- Nur EPUB-Format wird vollständig unterstützt
- Google Books API hat ein Limit von 1000 Anfragen/Tag
- Calibre-ISBNs (z.B. `calibre:12345`) werden ignoriert
- Sehr lange Titel werden gekürzt für bessere Suchergebnisse

## 💡 Tipps & Tricks

### Für große Sammlungen (1000+ Bücher):
1. Erst `ebook_metadata_enricher.py` über Nacht laufen lassen
2. Dann `ebook_importer_gui.py` nutzen - nutzt automatisch den Cache!
3. Resultat: 95%+ schnellerer Import, fast keine API-Calls

### Genre-Zuordnungen verbessern:
- Importieren Sie Bücher und ordnen Sie unbekannte Kategorien zu
- Das System lernt und nutzt Ihre Zuordnungen beim nächsten Mal!
- Mappings werden in `~/.ebook_genre_mappings.json` gespeichert

### Schlechte Klassifizierungen korrigieren:
1. Löschen Sie den Eintrag aus `enriched_metadata.json`
2. Importieren Sie das Buch erneut
3. System fragt API ab und speichert bessere Daten

## 🆘 Häufige Probleme

### "AttributeError: 'EbookImporter' object has no attribute 'log_text'"
**Lösung:** Stellen Sie sicher, Sie haben die neueste Version. Diesen Bug haben wir behoben!

### "Keine Google Books Daten gefunden"
**Mögliche Gründe:**
- ISBN ist ungültig (z.B. Calibre-ID)
- Buch existiert nicht in Google Books
- API-Limit erreicht (1000/Tag)

**Lösung:** System nutzt dann Fallback-Genre "Sonstiges"

### Bücher landen alle in "Sonstiges"
**Lösung:** 
1. Prüfen Sie ob Google Books API aktiviert ist (Checkbox in GUI)
2. Prüfen Sie Ihre Internetverbindung
3. Bei Calibre-Büchern: Oft keine echte ISBN → Titel-Suche wird genutzt

## 🙏 Credits

- Entwickelt zur Organisation persönlicher eBook-Sammlungen
- Nutzt die [Google Books API](https://developers.google.com/books)
- Python Standard Library (keine externen Dependencies!)

## 📧 Kontakt

Bei Fragen oder Problemen öffnen Sie bitte ein Issue auf GitHub.

---

**Happy Reading! 📚✨**
