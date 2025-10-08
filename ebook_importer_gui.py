#!/usr/bin/env python3
"""
eBook Importer GUI - Fügt neue Bücher zur Sammlung hinzu

Features:
- Speichert und lädt Pfade für Buchsammlung
- Wählt Verzeichnis mit neuen Büchern aus
- Kopiert oder verschiebt Bücher zur Sammlung
- Organisiert automatisch nach Autor/Titel
- Bereinigt leere Ordner nach dem Import
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import shutil
import os
from pathlib import Path
from datetime import datetime
import zipfile
import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
import time

class EbookImporter:
    def __init__(self, root):
        self.root = root
        self.root.title("eBook Importer")
        self.root.geometry("800x600")
        
        # Konfigurationsdatei
        self.config_file = Path.home() / ".ebook_importer_config.json"
        self.config = self.load_config()
        
        # Cache für Google Books API
        self.cache_dir = Path.home() / ".cache" / "ebook_metadata"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Benutzerdefinierte Mappings (lernfähig)
        self.user_mappings_file = Path.home() / ".ebook_genre_mappings.json"
        self.user_mappings = self.load_user_mappings()
        
        # Metadaten-Cache aus enriched_metadata.json
        self.metadata_cache = {}
        
        # Genre-Mapping von Google Books zu deutschen Genres
        # Unterstützt englische UND deutsche Kategorien
        self.genre_mapping = {
            # Englische Kategorien
            'Fiction / Science Fiction': 'Science Fiction',
            'Fiction / Fantasy': 'Fantasy',
            'Fiction / Mystery & Detective': 'Krimi/Thriller',
            'Fiction / Thrillers': 'Krimi/Thriller',
            'Fiction / Literary': 'Belletristik',
            'Fiction / General': 'Belletristik',
            'Fiction / Romance': 'Liebesromane',
            'Fiction / Historical': 'Belletristik',
            'Biography & Autobiography': 'Biografien/Memoiren',
            'History': 'Sachbücher',
            'Science': 'Sachbücher',
            'Philosophy': 'Sachbücher',
            'Self-Help': 'Ratgeber',
            'Health & Fitness': 'Ratgeber',
            'Business & Economics': 'Wirtschaft',
            'Young Adult Fiction': 'Jugendbuch',
            'Juvenile Fiction': 'Kinderbuch',
            'Travel': 'Sachbücher',
            'Psychology': 'Sachbücher',
            'Religion': 'Sachbücher',
            'Political Science': 'Sachbücher',
            'Social Science': 'Sachbücher',
            'True Crime': 'Krimi/Thriller',
            # Deutsche Kategorien
            'Fiktion': 'Belletristik',
            'Belletristik': 'Belletristik',
            'Science-Fiction': 'Science Fiction',
            'Science Fiction': 'Science Fiction',
            'Fantasy': 'Fantasy',
            'Fantasie': 'Fantasy',
            'Kriminalroman': 'Krimi/Thriller',
            'Thriller': 'Krimi/Thriller',
            'Krimi': 'Krimi/Thriller',
            'Liebesroman': 'Liebesromane',
            'Romantik': 'Liebesromane',
            'Biografie': 'Biografien/Memoiren',
            'Biographie': 'Biografien/Memoiren',
            'Memoiren': 'Biografien/Memoiren',
            'Geschichte': 'Sachbücher',
            'Wissenschaft': 'Sachbücher',
            'Philosophie': 'Sachbücher',
            'Ratgeber': 'Ratgeber',
            'Selbsthilfe': 'Ratgeber',
            'Wirtschaft': 'Wirtschaft',
            'Jugendbuch': 'Jugendbuch',
            'Kinderbuch': 'Kinderbuch',
            'Reiseliteratur': 'Sachbücher',
            'Reisen': 'Sachbücher',
            'Psychologie': 'Sachbücher',
            'Religion': 'Sachbücher',
            'Politik': 'Sachbücher',
            'Soziologie': 'Sachbücher',
        }
        
        # Unbekannte Kategorien sammeln
        self.unknown_categories = set()
        
        self.create_widgets()
        
    def load_config(self):
        """Lädt gespeicherte Konfiguration"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Standard-Konfiguration
        return {
            'collection_path': str(Path.home() / 'Schreibtisch' / 'eBooks_neu'),
            'last_import_path': str(Path.home()),
            'move_files': False,  # Standard: kopieren statt verschieben
            'organize_by_author': True,
            'use_google_books': True,  # Google Books API verwenden
            'api_delay': 1.0  # Wartezeit zwischen API-Anfragen
        }
    
    def save_config(self):
        """Speichert aktuelle Konfiguration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.log(f"Fehler beim Speichern der Konfiguration: {e}")
    
    def load_user_mappings(self):
        """Lädt benutzerdefinierte Genre-Mappings"""
        if self.user_mappings_file.exists():
            try:
                with open(self.user_mappings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_user_mappings(self):
        """Speichert benutzerdefinierte Genre-Mappings"""
        try:
            with open(self.user_mappings_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_mappings, f, indent=2, ensure_ascii=False)
            self.log(f"✓ Genre-Mappings gespeichert: {len(self.user_mappings)} Einträge")
        except Exception as e:
            self.log(f"Fehler beim Speichern der Mappings: {e}")
    
    def load_enriched_metadata(self):
        """Lädt enriched_metadata.json falls vorhanden"""
        # Prüfe im Schreibtisch-Verzeichnis
        self.enriched_file = Path.home() / "Schreibtisch" / "enriched_metadata.json"
        
        if not self.enriched_file.exists():
            # Erstelle leere Datei wenn nicht vorhanden
            with open(self.enriched_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
            return
        
        try:
            with open(self.enriched_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Erstelle Cache-Dictionary für schnellen Zugriff
            for entry in data:
                if isinstance(entry, dict) and 'metadata' in entry:
                    metadata = entry['metadata']
                    
                    # Mehrere Schlüssel für Lookup
                    title = metadata.get('title', '').lower().strip()
                    authors = metadata.get('authors', [])
                    author = authors[0] if authors else ''
                    author = author.lower().strip()
                    isbn_13 = metadata.get('isbn_13', '').strip()
                    isbn_10 = metadata.get('isbn_10', '').strip()
                    
                    # Cache-Keys erstellen
                    cache_keys = []
                    if isbn_13:
                        cache_keys.append(f"isbn:{isbn_13}")
                    if isbn_10:
                        cache_keys.append(f"isbn:{isbn_10}")
                    if title and author:
                        cache_keys.append(f"title_author:{title}:{author}")
                    
                    # Genre aus Metadaten
                    genre = metadata.get('genre_classified', 'Sonstiges')
                    google_books = metadata.get('google_books', {})
                    categories = google_books.get('categories', [])
                    
                    # Speichere unter allen Keys
                    cache_entry = {
                        'genre': genre,
                        'categories': categories,
                        'title': title,
                        'author': author
                    }
                    
                    for key in cache_keys:
                        self.metadata_cache[key] = cache_entry
            
            if self.metadata_cache:
                self.log(f"✓ Metadaten-Cache geladen: {len(self.metadata_cache)} Einträge aus enriched_metadata.json")
        
        except Exception as e:
            self.log(f"⚠ Fehler beim Laden von enriched_metadata.json: {e}")
    
    def save_to_enriched_metadata(self, book_path, metadata, genre, google_books_data):
        """Speichert neue Metadaten in enriched_metadata.json"""
        self.log(f"  🔍 DEBUG: save_to_enriched_metadata aufgerufen")
        self.log(f"  🔍 DEBUG: book_path={book_path}")
        self.log(f"  🔍 DEBUG: self.enriched_file={self.enriched_file}")
        
        try:
            # Lade bestehende Daten
            if self.enriched_file.exists():
                with open(self.enriched_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                data = []
            
            # Extrahiere Kategorien aus Google Books Daten
            categories = []
            if google_books_data and 'items' in google_books_data:
                volume_info = google_books_data['items'][0].get('volumeInfo', {})
                categories = volume_info.get('categories', [])
            
            # Erstelle neuen Eintrag im gleichen Format wie ebook_metadata_enricher.py
            collection_path = Path(self.collection_var.get())
            relative_path = str(book_path.relative_to(collection_path))
            
            new_entry = {
                "filepath": str(book_path),
                "relative_path": relative_path,
                "filename": book_path.name,
                "metadata": {
                    "title": metadata.get('title', ''),
                    "authors": [metadata.get('author', '')] if metadata.get('author') else [],
                    "publisher": "",
                    "published_date": "",
                    "language": "",
                    "isbn_10": metadata.get('isbn_10', ''),
                    "isbn_13": metadata.get('isbn_13', ''),
                    "description": "",
                    "categories": categories,
                    "google_books": {
                        "categories": categories
                    } if categories else {},
                    "genre_classified": genre
                }
            }
            
            # Prüfe ob Eintrag bereits existiert (nach filepath)
            existing_index = None
            for i, entry in enumerate(data):
                if entry.get('filepath') == str(book_path):
                    existing_index = i
                    break
            
            if existing_index is not None:
                # Update bestehenden Eintrag
                data[existing_index] = new_entry
            else:
                # Füge neuen Eintrag hinzu
                data.append(new_entry)
            
            # Speichere zurück
            self.log(f"  🔍 DEBUG: Schreibe {len(data)} Einträge in Datei...")
            with open(self.enriched_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.log(f"  🔍 DEBUG: Datei erfolgreich geschrieben")
            
            # Update auch den internen Cache
            isbn = metadata.get('isbn_13') or metadata.get('isbn_10')
            title = metadata.get('title', '').lower().strip()
            author = metadata.get('author', '').lower().strip()
            
            cache_entry = {
                'genre': genre,
                'categories': categories,
                'title': title,
                'author': author
            }
            
            # Speichere unter allen möglichen Keys
            if isbn:
                self.metadata_cache[f"isbn:{isbn}"] = cache_entry
            if title and author:
                self.metadata_cache[f"title_author:{title}:{author}"] = cache_entry
            
            self.log(f"  💾 Metadaten gespeichert in enriched_metadata.json")
            
        except Exception as e:
            self.log(f"  ⚠ Fehler beim Speichern der Metadaten: {e}")
    
    def lookup_in_metadata_cache(self, isbn=None, title=None, author=None):
        """Sucht in enriched_metadata.json Cache"""
        if not self.metadata_cache:
            return None
        
        # Versuche verschiedene Lookup-Strategien
        if isbn:
            key = f"isbn:{isbn}"
            if key in self.metadata_cache:
                return self.metadata_cache[key]
        
        if title and author:
            title = title.lower().strip()
            author = author.lower().strip()
            key = f"title_author:{title}:{author}"
            if key in self.metadata_cache:
                return self.metadata_cache[key]
        
        return None
    
    def create_widgets(self):
        """Erstellt GUI-Elemente"""
        
        # Header
        header = ttk.Frame(self.root, padding="10")
        header.pack(fill=tk.X)
        
        title = ttk.Label(header, text="eBook Importer", font=('Arial', 16, 'bold'))
        title.pack()
        
        subtitle = ttk.Label(header, text="Fügt neue Bücher zu Ihrer Sammlung hinzu")
        subtitle.pack()
        
        # Hauptbereich
        main = ttk.Frame(self.root, padding="10")
        main.pack(fill=tk.BOTH, expand=True)
        
        # Buchsammlung-Pfad
        collection_frame = ttk.LabelFrame(main, text="Buchsammlung", padding="10")
        collection_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.collection_var = tk.StringVar(value=self.config['collection_path'])
        
        collection_entry = ttk.Entry(collection_frame, textvariable=self.collection_var, width=60)
        collection_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        collection_btn = ttk.Button(collection_frame, text="Durchsuchen...", 
                                   command=self.browse_collection)
        collection_btn.pack(side=tk.LEFT)
        
        # Neue Bücher-Pfad
        import_frame = ttk.LabelFrame(main, text="Neue Bücher", padding="10")
        import_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.import_var = tk.StringVar(value=self.config['last_import_path'])
        
        import_entry = ttk.Entry(import_frame, textvariable=self.import_var, width=60)
        import_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        import_btn = ttk.Button(import_frame, text="Durchsuchen...", 
                               command=self.browse_import)
        import_btn.pack(side=tk.LEFT)
        
        # Optionen
        options_frame = ttk.LabelFrame(main, text="Optionen", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.move_var = tk.BooleanVar(value=self.config['move_files'])
        move_check = ttk.Checkbutton(options_frame, text="Dateien verschieben (statt kopieren)", 
                                     variable=self.move_var)
        move_check.pack(anchor=tk.W)
        
        self.organize_var = tk.BooleanVar(value=self.config['organize_by_author'])
        organize_check = ttk.Checkbutton(options_frame, 
                                        text="Nach Autor organisieren", 
                                        variable=self.organize_var)
        organize_check.pack(anchor=tk.W)
        
        self.google_books_var = tk.BooleanVar(value=self.config.get('use_google_books', True))
        google_books_check = ttk.Checkbutton(options_frame, 
                                             text="Google Books API für Genre-Klassifizierung nutzen", 
                                             variable=self.google_books_var)
        google_books_check.pack(anchor=tk.W)
        
        self.cleanup_var = tk.BooleanVar(value=True)
        cleanup_check = ttk.Checkbutton(options_frame, 
                                       text="Leere Ordner nach Import bereinigen", 
                                       variable=self.cleanup_var)
        cleanup_check.pack(anchor=tk.W)
        
        # Action Buttons
        button_frame = ttk.Frame(main)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        preview_btn = ttk.Button(button_frame, text="Vorschau", 
                                command=self.preview_import)
        preview_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        import_btn = ttk.Button(button_frame, text="Bücher importieren", 
                               command=self.import_books,
                               style="Accent.TButton")
        import_btn.pack(side=tk.LEFT)
        
        # Log-Bereich
        log_frame = ttk.LabelFrame(main, text="Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Status Bar
        self.status_var = tk.StringVar(value="Bereit")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Initial Log
        self.log("eBook Importer gestartet")
        self.log(f"Buchsammlung: {self.collection_var.get()}")
        
        # Metadaten-Cache laden (nach GUI-Erstellung)
        self.load_enriched_metadata()
    
    def log(self, message):
        """Fügt Nachricht zum Log hinzu"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def browse_collection(self):
        """Wählt Buchsammlungs-Verzeichnis aus"""
        path = filedialog.askdirectory(
            title="Buchsammlung auswählen",
            initialdir=self.collection_var.get()
        )
        if path:
            self.collection_var.set(path)
            self.config['collection_path'] = path
            self.save_config()
            self.log(f"Buchsammlung geändert: {path}")
    
    def browse_import(self):
        """Wählt Verzeichnis mit neuen Büchern aus"""
        path = filedialog.askdirectory(
            title="Neue Bücher auswählen",
            initialdir=self.import_var.get()
        )
        if path:
            self.import_var.set(path)
            self.config['last_import_path'] = path
            self.save_config()
            self.log(f"Import-Verzeichnis geändert: {path}")
    
    def extract_epub_metadata(self, epub_path):
        """Extrahiert Metadaten aus EPUB-Datei"""
        try:
            with zipfile.ZipFile(epub_path, 'r') as zip_ref:
                # Suche content.opf
                for name in zip_ref.namelist():
                    if name.endswith('.opf') or 'content.opf' in name.lower():
                        with zip_ref.open(name) as opf_file:
                            tree = ET.parse(opf_file)
                            root = tree.getroot()
                            
                            # Namespace handling
                            ns = {'dc': 'http://purl.org/dc/elements/1.1/'}
                            
                            title = root.find('.//dc:title', ns)
                            creator = root.find('.//dc:creator', ns)
                            
                            # ISBN suchen
                            isbn_13 = None
                            isbn_10 = None
                            for identifier in root.findall('.//dc:identifier', ns):
                                id_text = identifier.text
                                if id_text:
                                    # Entferne Präfixe wie "urn:isbn:"
                                    id_text = id_text.replace('urn:isbn:', '').strip()
                                    
                                    # Filtere ungültige ISBNs aus (z.B. "calibre:12345", "uuid:...")
                                    if ':' in id_text or not id_text.replace('-', '').isdigit():
                                        continue
                                    
                                    # Entferne Bindestriche
                                    id_text = id_text.replace('-', '')
                                    
                                    if len(id_text) == 13 and id_text.isdigit():
                                        isbn_13 = id_text
                                    elif len(id_text) == 10:
                                        isbn_10 = id_text
                            
                            return {
                                'title': title.text if title is not None else None,
                                'author': creator.text if creator is not None else None,
                                'isbn_13': isbn_13,
                                'isbn_10': isbn_10
                            }
        except:
            pass
        
        return {'title': None, 'author': None, 'isbn_13': None, 'isbn_10': None}
    
    def normalize_author(self, author):
        """Normalisiert Autorennamen"""
        if not author:
            return "Unbekannt"
        
        # Entferne Sonderzeichen, die in Dateinamen problematisch sind
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            author = author.replace(char, '')
        
        return author.strip()
    
    def clean_title_for_search(self, title):
        """Bereinigt Titel für Google Books Suche
        
        Entfernt:
        - Serien-Nummern (z.B. "001 - ", "Band 1: ", etc.)
        - Untertitel nach " - " wenn zu lang
        """
        if not title:
            return title
        
        import re
        
        # Entferne Serien-Präfixe: "001 - ", "002 - ", "Band 1 - ", etc.
        title = re.sub(r'^\d{1,3}\s*[-:]\s*', '', title)
        title = re.sub(r'^(Band|Teil|Book|Volume)\s+\d+\s*[-:]\s*', '', title, flags=re.IGNORECASE)
        
        # Bei sehr langen Titeln: Nur Haupttitel (vor erstem " - ")
        if len(title) > 50 and ' - ' in title:
            parts = title.split(' - ')
            title = parts[0]
        
        return title.strip()
    
    def query_google_books(self, isbn=None, title=None, author=None):
        """Fragt Google Books API ab"""
        # Bereinige Titel für bessere Suche
        search_title = self.clean_title_for_search(title) if title else title
        
        # Cache prüfen (mit Original-Titel für eindeutigen Key)
        cache_key = f"{isbn or ''}{title or ''}{author or ''}".replace(' ', '_')
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Query erstellen
        query_parts = []
        if isbn:
            query_parts.append(f'isbn:{isbn}')
        else:
            # Verwende bereinigten Titel für Suche
            if search_title and search_title != title:
                self.log(f"  🔍 Bereinigter Suchtitel: '{search_title}' (Original: '{title}')")
            
            if search_title:
                query_parts.append(f'intitle:{search_title}')
            if author:
                query_parts.append(f'inauthor:{author}')
        
        if not query_parts:
            return None
        
        query = '+'.join(query_parts)
        url = f'https://www.googleapis.com/books/v1/volumes?q={urllib.parse.quote(query)}'
        
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                
                # Cache speichern
                with open(cache_file, 'w') as f:
                    json.dump(data, f)
                
                return data
        except Exception as e:
            self.log(f"  API-Fehler: {e}")
            return None
    
    def classify_genre_from_google_books(self, google_data):
        """Klassifiziert Genre basierend auf Google Books Daten"""
        if not google_data or 'items' not in google_data:
            return None
        
        # Ersten Treffer verwenden
        item = google_data['items'][0]
        volume_info = item.get('volumeInfo', {})
        
        categories = volume_info.get('categories', [])
        
        if not categories:
            return None
        
        # Logging für Debug
        self.log(f"  API-Kategorien: {', '.join(categories)}")
        
        # Strategie 0: Benutzerdefinierte Mappings (höchste Priorität!)
        for category in categories:
            if category in self.user_mappings:
                self.log(f"  → Benutzer-Mapping verwendet: {self.user_mappings[category]}")
                return self.user_mappings[category]
        
        # Strategie 1: Vordefinierte exakte Matches
        for category in categories:
            if category in self.genre_mapping:
                return self.genre_mapping[category]
        
        # Strategie 2: Teilstring-Matches (flexibel)
        for category in categories:
            for key, genre in self.genre_mapping.items():
                if key.lower() in category.lower() or category.lower() in key.lower():
                    return genre
            
            # Auch in Benutzer-Mappings suchen
            for key, genre in self.user_mappings.items():
                if key.lower() in category.lower() or category.lower() in key.lower():
                    self.log(f"  → Benutzer-Mapping (fuzzy) verwendet: {genre}")
                    return genre
        
        # Strategie 3: Einzelwort-Matches für breite Kategorien
        broad_keywords = {
            'fiction': 'Belletristik',
            'fiktion': 'Belletristik',
            'science fiction': 'Science Fiction',
            'fantasy': 'Fantasy',
            'thriller': 'Krimi/Thriller',
            'krimi': 'Krimi/Thriller',
            'mystery': 'Krimi/Thriller',
            'romance': 'Liebesromane',
            'biography': 'Biografien/Memoiren',
            'biografie': 'Biografien/Memoiren',
            'history': 'Sachbücher',
            'geschichte': 'Sachbücher',
            'science': 'Sachbücher',
            'wissenschaft': 'Sachbücher',
            'travel': 'Sachbücher',
            'reise': 'Sachbücher',
            'self-help': 'Ratgeber',
            'ratgeber': 'Ratgeber',
        }
        
        for category in categories:
            category_lower = category.lower()
            for keyword, genre in broad_keywords.items():
                if keyword in category_lower:
                    return genre
        
        # Strategie 4: Unbekannte Kategorien sammeln
        for category in categories:
            self.unknown_categories.add(category)
        
        return None
    
    def get_book_files(self, directory):
        """Findet alle EPUB-Dateien im Verzeichnis
        
        Nur EPUB-Dateien werden unterstützt, da nur diese:
        - Extrahierbare Metadaten haben
        - Mit Google Books API abfragbar sind
        - In enriched_metadata.json gespeichert werden können
        """
        directory = Path(directory)
        if not directory.exists():
            return []
        
        # Nur EPUB-Dateien
        books = list(directory.rglob('*.epub'))
        
        return sorted(books)
    
    def preview_import(self):
        """Zeigt Vorschau der zu importierenden Bücher"""
        self.log("\n" + "="*50)
        self.log("VORSCHAU")
        self.log("="*50)
        
        import_path = Path(self.import_var.get())
        collection_path = Path(self.collection_var.get())
        
        if not import_path.exists():
            self.log("❌ Import-Verzeichnis existiert nicht!")
            return
        
        books = self.get_book_files(import_path)
        
        if not books:
            self.log("❌ Keine eBooks gefunden!")
            return
        
        self.log(f"✓ Gefunden: {len(books)} Bücher")
        self.log("")
        
        for i, book in enumerate(books[:10], 1):
            self.log(f"{i}. {book.name}")
        
        if len(books) > 10:
            self.log(f"   ... und {len(books) - 10} weitere")
        
        self.log("")
        self.log(f"Aktion: {'Verschieben' if self.move_var.get() else 'Kopieren'}")
        self.log(f"Ziel: {collection_path}")
        self.log(f"Organisation: {'Nach Autor' if self.organize_var.get() else 'Direkt'}")
        self.log(f"Google Books API: {'Ja' if self.google_books_var.get() else 'Nein'}")
    
    def import_books(self):
        """Importiert Bücher in die Sammlung"""
        self.log("\n" + "="*50)
        self.log("IMPORT GESTARTET")
        self.log("="*50)
        
        import_path = Path(self.import_var.get())
        collection_path = Path(self.collection_var.get())
        
        # Validierung
        if not import_path.exists():
            messagebox.showerror("Fehler", "Import-Verzeichnis existiert nicht!")
            return
        
        if not collection_path.exists():
            messagebox.showerror("Fehler", "Buchsammlungs-Verzeichnis existiert nicht!")
            return
        
        books = self.get_book_files(import_path)
        
        if not books:
            messagebox.showwarning("Keine Bücher", "Keine eBooks im Import-Verzeichnis gefunden!")
            return
        
        # Bestätigung
        action = "verschieben" if self.move_var.get() else "kopieren"
        result = messagebox.askyesno(
            "Import bestätigen",
            f"{len(books)} Bücher werden {action}.\n\nFortfahren?"
        )
        
        if not result:
            self.log("Import abgebrochen")
            return
        
        # Import durchführen
        success_count = 0
        error_count = 0
        skipped_count = 0
        
        for i, book_path in enumerate(books, 1):
            self.status_var.set(f"Importiere {i}/{len(books)}...")
            self.log(f"\n[{i}/{len(books)}] {book_path.name}")
            
            try:
                genre = "Sonstiges"
                author = "Unbekannt"
                google_data = None  # Initialisiere für späteres Speichern
                metadata = {}
                
                # Für EPUB: Metadaten extrahieren
                if book_path.suffix.lower() == '.epub':
                    metadata = self.extract_epub_metadata(book_path)
                    author = self.normalize_author(metadata.get('author'))
                    
                    self.log(f"  Titel: {metadata.get('title', 'Unbekannt')}")
                    self.log(f"  Autor: {author}")
                    
                    # Genre-Klassifizierung
                    if self.google_books_var.get():
                        isbn = metadata.get('isbn_13') or metadata.get('isbn_10')
                        
                        # Filtere ungültige ISBNs
                        if isbn and (':' in isbn or not isbn.replace('-', '').isdigit()):
                            self.log(f"  ⚠ Ungültige ISBN gefunden: {isbn} (wird ignoriert)")
                            isbn = None
                        
                        if isbn:
                            self.log(f"  ISBN: {isbn}")
                        else:
                            self.log(f"  ℹ Keine gültige ISBN, suche mit Titel+Autor")
                        
                        # Strategie 1: Prüfe enriched_metadata.json Cache
                        cached_entry = self.lookup_in_metadata_cache(
                            isbn=isbn,
                            title=metadata.get('title'),
                            author=metadata.get('author')
                        )
                        
                        if cached_entry:
                            # Daten aus Cache verwenden
                            cached_genre = cached_entry.get('genre')
                            categories = cached_entry.get('categories', [])
                            
                            # Nur Cache verwenden wenn Genre != "Sonstiges" ODER Kategorien vorhanden
                            if cached_genre and cached_genre != 'Sonstiges':
                                # Gutes Genre im Cache → verwenden!
                                genre = cached_genre
                                self.log(f"  ✓ Genre: {genre} (aus enriched_metadata.json)")
                                self.log(f"  📋 Kategorien: {', '.join(categories)}")
                            elif categories:
                                # Genre ist "Sonstiges" ABER Kategorien vorhanden → Reklassifizierung
                                self.log(f"  ℹ Cache: Genre=Sonstiges, aber Kategorien vorhanden")
                                self.log(f"  📋 Kategorien (Cache): {', '.join(categories)}")
                                # Simuliere Google Books Data für classify_genre
                                simulated_data = {
                                    'items': [{
                                        'volumeInfo': {
                                            'categories': categories
                                        }
                                    }]
                                }
                                classified_genre = self.classify_genre_from_google_books(simulated_data)
                                if classified_genre:
                                    genre = classified_genre
                                    self.log(f"  ✓ Genre: {genre} (Reklassifizierung mit Cache-Kategorien)")
                                else:
                                    # Reklassifizierung fehlgeschlagen → API-Abfrage
                                    self.log(f"  ⚠ Reklassifizierung fehlgeschlagen, frage API ab...")
                                    google_data = self.query_google_books(
                                        isbn=isbn,
                                        title=metadata.get('title'),
                                        author=metadata.get('author')
                                    )
                                    
                                    if google_data:
                                        classified_genre = self.classify_genre_from_google_books(google_data)
                                        if classified_genre:
                                            genre = classified_genre
                                            self.log(f"  ✓ Genre: {genre} (via Google Books API)")
                                        else:
                                            self.log(f"  ⚠ Genre: {genre} (Fallback)")
                                    else:
                                        self.log(f"  ⚠ Keine Google Books Daten")
                                    
                                    time.sleep(self.config.get('api_delay', 1.0))
                            else:
                                # Genre ist "Sonstiges" UND keine Kategorien → schlechter Cache!
                                self.log(f"  ⚠ Cache-Eintrag ist unvollständig (Genre=Sonstiges, keine Kategorien)")
                                self.log(f"  ℹ Ignoriere Cache, frage Google Books API ab...")
                                google_data = self.query_google_books(
                                    isbn=isbn,
                                    title=metadata.get('title'),
                                    author=metadata.get('author')
                                )
                                
                                if google_data:
                                    classified_genre = self.classify_genre_from_google_books(google_data)
                                    if classified_genre:
                                        genre = classified_genre
                                        self.log(f"  ✓ Genre: {genre} (via Google Books API)")
                                    else:
                                        self.log(f"  ⚠ Genre: {genre} (Fallback)")
                                else:
                                    self.log(f"  ⚠ Keine Google Books Daten")
                                
                                time.sleep(self.config.get('api_delay', 1.0))
                        else:
                            # Strategie 2: Keine Cache-Daten → API-Anfrage
                            self.log(f"  ℹ Nicht im Cache, frage Google Books API ab...")
                            google_data = self.query_google_books(
                                isbn=isbn,
                                title=metadata.get('title'),
                                author=metadata.get('author')
                            )
                            
                            if google_data:
                                classified_genre = self.classify_genre_from_google_books(google_data)
                                if classified_genre:
                                    genre = classified_genre
                                    self.log(f"  ✓ Genre: {genre} (via Google Books API)")
                                else:
                                    self.log(f"  ⚠ Genre: {genre} (Fallback)")
                            else:
                                self.log(f"  ⚠ Keine Google Books Daten")
                            
                            # API Rate Limiting
                            time.sleep(self.config.get('api_delay', 1.0))
                
                # Zielverzeichnis bestimmen (BEVOR wir prüfen ob Datei existiert)
                if self.organize_var.get():
                    target_dir = collection_path / genre / author
                else:
                    target_dir = collection_path / genre
                
                target_dir.mkdir(parents=True, exist_ok=True)
                target_file = target_dir / book_path.name
                
                # Prüfe ob Datei bereits existiert
                file_already_exists = target_file.exists()
                
                if file_already_exists:
                    self.log(f"  ⚠ Datei existiert bereits")
                    # Speichere Metadaten (mit den gerade abgefragten google_data!)
                    if book_path.suffix.lower() == '.epub' and self.google_books_var.get():
                        if google_data:
                            self.log(f"  ✅ Aktualisiere Metadaten mit neuen API-Daten...")
                        else:
                            self.log(f"  ℹ Aktualisiere Metadaten (keine API-Daten verfügbar)...")
                        self.save_to_enriched_metadata(target_file, metadata, genre, google_data)
                    skipped_count += 1
                    continue
                
                # Kopiere oder verschiebe
                if self.move_var.get():
                    shutil.move(str(book_path), str(target_file))
                    self.log(f"  ✓ Verschoben nach: {target_file.relative_to(collection_path)}")
                else:
                    shutil.copy2(str(book_path), str(target_file))
                    self.log(f"  ✓ Kopiert nach: {target_file.relative_to(collection_path)}")
                
                # Speichere Metadaten für EPUB-Dateien
                if book_path.suffix.lower() == '.epub' and self.google_books_var.get():
                    self.save_to_enriched_metadata(target_file, metadata, genre, google_data)
                
                success_count += 1
                
            except Exception as e:
                self.log(f"  ❌ Fehler: {e}")
                error_count += 1
        
        # Cleanup leere Ordner
        if self.cleanup_var.get():
            self.log("\nBereinige leere Ordner...")
            self.cleanup_empty_dirs(collection_path)
        
        # Zusammenfassung
        self.log("\n" + "="*50)
        self.log("IMPORT ABGESCHLOSSEN")
        self.log("="*50)
        self.log(f"✓ Erfolgreich: {success_count}")
        if skipped_count > 0:
            self.log(f"⚠ Übersprungen: {skipped_count}")
        if error_count > 0:
            self.log(f"❌ Fehler: {error_count}")
        
        # Unbekannte Kategorien anzeigen
        if self.unknown_categories:
            self.log(f"\n⚠ {len(self.unknown_categories)} unbekannte Kategorien gefunden")
            self.log("Möchten Sie diese jetzt zuordnen?")
            
            result = messagebox.askyesno(
                "Unbekannte Kategorien",
                f"{len(self.unknown_categories)} unbekannte Kategorien gefunden.\n\n"
                "Möchten Sie diese jetzt Genre-Kategorien zuordnen?\n"
                "Dies verbessert zukünftige Importe!"
            )
            
            if result:
                self.show_category_mapping_dialog()
        
        self.status_var.set(f"Import abgeschlossen: {success_count} Bücher importiert")
        
        messagebox.showinfo(
            "Import abgeschlossen",
            f"Erfolgreich: {success_count}\nÜbersprungen: {skipped_count}\nFehler: {error_count}"
        )
    
    def show_category_mapping_dialog(self):
        """Zeigt Dialog zum Zuordnen unbekannter Kategorien"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Unbekannte Kategorien zuordnen")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Header
        header = ttk.Label(dialog, 
                          text="Ordnen Sie unbekannte Kategorien deutschen Genres zu:",
                          font=('Arial', 12, 'bold'))
        header.pack(padx=10, pady=10)
        
        info = ttk.Label(dialog, 
                        text="Diese Zuordnungen werden gespeichert und bei zukünftigen Importen verwendet.",
                        wraplength=550)
        info.pack(padx=10, pady=(0, 10))
        
        # Scrollable Frame
        canvas = tk.Canvas(dialog)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Verfügbare Genres
        available_genres = [
            "Belletristik", "Science Fiction", "Fantasy", "Krimi/Thriller",
            "Liebesromane", "Biografien/Memoiren", "Sachbücher", "Ratgeber",
            "Wirtschaft", "Jugendbuch", "Kinderbuch", "Sonstiges"
        ]
        
        # Mappings
        mappings = {}
        
        for i, category in enumerate(sorted(self.unknown_categories)):
            frame = ttk.Frame(scrollable_frame)
            frame.pack(fill=tk.X, padx=10, pady=5)
            
            label = ttk.Label(frame, text=category, width=40)
            label.pack(side=tk.LEFT, padx=(0, 10))
            
            var = tk.StringVar(value="Sonstiges")
            combo = ttk.Combobox(frame, textvariable=var, values=available_genres, width=20)
            combo.pack(side=tk.LEFT)
            
            mappings[category] = var
        
        canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side="right", fill="y", pady=10, padx=(0, 10))
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def save_mappings():
            for category, var in mappings.items():
                genre = var.get()
                self.user_mappings[category] = genre
                self.log(f"  Gelernt: '{category}' → '{genre}'")
            
            self.save_user_mappings()
            self.unknown_categories.clear()
            dialog.destroy()
            
            messagebox.showinfo(
                "Gespeichert",
                f"{len(mappings)} Zuordnungen wurden gespeichert!\n\n"
                "Diese werden bei zukünftigen Importen automatisch verwendet."
            )
        
        def cancel():
            self.unknown_categories.clear()
            dialog.destroy()
        
        ttk.Button(button_frame, text="Speichern", command=save_mappings).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Abbrechen", command=cancel).pack(side=tk.LEFT)
    
    def cleanup_empty_dirs(self, base_dir):
        """Bereinigt leere Ordner"""
        removed_count = 0
        
        # Sammle alle Ordner (von unten nach oben)
        all_dirs = []
        for root, dirs, files in os.walk(base_dir, topdown=False):
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                all_dirs.append(dir_path)
        
        # Lösche leere Ordner
        for dir_path in all_dirs:
            try:
                if dir_path.exists() and not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    removed_count += 1
            except:
                pass
        
        if removed_count > 0:
            self.log(f"✓ {removed_count} leere Ordner entfernt")


def main():
    root = tk.Tk()
    app = EbookImporter(root)
    root.mainloop()


if __name__ == '__main__':
    main()
