#!/usr/bin/env python3
"""
eBook Metadata Enricher - Reichert eBook-Metadaten mit Google Books API an

Funktionen:
- Extrahiert Metadaten aus EPUB-Dateien (ISBN, Titel, Autor)
- Fragt Google Books API ab für erweiterte Metadaten
- Verbessert Genre-Klassifizierung
- Kann Metadaten optional zurück in EPUBs schreiben
- Caching für API-Abfragen (Rate Limiting beachten)
"""

import os
import re
import json
import time
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import urllib.request
import urllib.parse
import urllib.error

class MetadataEnricher:
    def __init__(self, cache_dir=None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path.home() / '.cache' / 'ebook_metadata'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # API Rate Limiting
        self.last_api_call = 0
        self.min_api_interval = 1.0  # Sekunden zwischen API-Aufrufen
        
        # Genre-Mapping von Google Books Kategorien zu deutschen Genres
        self.genre_mapping = {
            'Fiction / Science Fiction': 'Science Fiction',
            'Fiction / Fantasy': 'Fantasy',
            'Fiction / Mystery & Detective': 'Krimi/Thriller',
            'Fiction / Thriller': 'Krimi/Thriller',
            'Fiction / Literary': 'Belletristik',
            'Fiction / General': 'Belletristik',
            'Fiction / Contemporary': 'Belletristik',
            'Fiction / Historical': 'Historische Romane',
            'Fiction / Romance': 'Liebesromane',
            'Biography & Autobiography': 'Biografien/Memoiren',
            'History': 'Sachbücher',
            'Science': 'Sachbücher',
            'Philosophy': 'Sachbücher',
            'Psychology': 'Sachbücher',
            'Self-Help': 'Ratgeber',
            'Business & Economics': 'Wirtschaft',
            'Technology': 'Sachbücher',
            'Computers': 'Sachbücher',
            'Cooking': 'Ratgeber',
            'Health & Fitness': 'Ratgeber',
            'True Crime': 'Krimi/Thriller',
            'Young Adult Fiction': 'Jugendbuch',
            'Juvenile Fiction': 'Kinderbuch'
        }
    
    def extract_epub_metadata(self, filepath):
        """Extrahiert Metadaten aus EPUB-Datei"""
        metadata = {
            'title': '',
            'authors': [],
            'publisher': '',
            'published_date': '',
            'language': '',
            'isbn_10': '',
            'isbn_13': '',
            'description': '',
            'categories': []
        }
        
        try:
            with zipfile.ZipFile(filepath, 'r') as zip_file:
                # Finde OPF-Datei
                opf_path = self._find_opf_path(zip_file)
                
                if opf_path:
                    opf_content = zip_file.read(opf_path)
                    root = ET.fromstring(opf_content)
                    
                    # Namespaces
                    ns = {
                        'opf': 'http://www.idpf.org/2007/opf',
                        'dc': 'http://purl.org/dc/elements/1.1/'
                    }
                    
                    # Extrahiere Metadaten
                    metadata_elem = root.find('.//opf:metadata', ns)
                    if metadata_elem is not None:
                        # Titel
                        title_elem = metadata_elem.find('.//dc:title', ns)
                        if title_elem is not None and title_elem.text:
                            metadata['title'] = title_elem.text.strip()
                        
                        # Autoren
                        for creator_elem in metadata_elem.findall('.//dc:creator', ns):
                            if creator_elem.text:
                                role = creator_elem.get('{http://www.idpf.org/2007/opf}role', 'aut')
                                if role in ['aut', 'author']:
                                    metadata['authors'].append(creator_elem.text.strip())
                        
                        # Verlag
                        publisher_elem = metadata_elem.find('.//dc:publisher', ns)
                        if publisher_elem is not None and publisher_elem.text:
                            metadata['publisher'] = publisher_elem.text.strip()
                        
                        # Veröffentlichungsdatum
                        date_elem = metadata_elem.find('.//dc:date', ns)
                        if date_elem is not None and date_elem.text:
                            metadata['published_date'] = date_elem.text.strip()
                        
                        # Sprache
                        lang_elem = metadata_elem.find('.//dc:language', ns)
                        if lang_elem is not None and lang_elem.text:
                            metadata['language'] = lang_elem.text.strip()
                        
                        # Beschreibung
                        desc_elem = metadata_elem.find('.//dc:description', ns)
                        if desc_elem is not None and desc_elem.text:
                            metadata['description'] = desc_elem.text.strip()
                        
                        # ISBN
                        for identifier_elem in metadata_elem.findall('.//dc:identifier', ns):
                            if identifier_elem.text:
                                id_text = identifier_elem.text.strip()
                                # ISBN-13
                                if 'isbn' in id_text.lower() or len(id_text.replace('-', '')) == 13:
                                    isbn = re.sub(r'[^0-9]', '', id_text)
                                    if len(isbn) == 13:
                                        metadata['isbn_13'] = isbn
                                # ISBN-10
                                elif len(id_text.replace('-', '')) == 10:
                                    isbn = re.sub(r'[^0-9X]', '', id_text.upper())
                                    if len(isbn) == 10:
                                        metadata['isbn_10'] = isbn
                        
                        # Kategorien/Subjects
                        for subject_elem in metadata_elem.findall('.//dc:subject', ns):
                            if subject_elem.text:
                                metadata['categories'].append(subject_elem.text.strip())
        
        except Exception as e:
            print(f"  Fehler beim Lesen von {filepath.name}: {e}")
        
        return metadata
    
    def _find_opf_path(self, zip_file):
        """Findet den Pfad zur OPF-Datei in einem EPUB"""
        try:
            # Versuche über container.xml
            container_xml = zip_file.read('META-INF/container.xml')
            container_root = ET.fromstring(container_xml)
            ns = {'container': 'urn:oasis:names:tc:opendocument:xmlns:container'}
            rootfile = container_root.find('.//container:rootfile', ns)
            if rootfile is not None:
                return rootfile.get('full-path')
        except:
            pass
        
        # Fallback: Suche nach .opf Dateien
        for name in zip_file.namelist():
            if name.endswith('.opf'):
                return name
        
        return None
    
    def query_google_books_api(self, isbn=None, title=None, author=None):
        """Fragt Google Books API ab"""
        
        # Rate Limiting
        elapsed = time.time() - self.last_api_call
        if elapsed < self.min_api_interval:
            time.sleep(self.min_api_interval - elapsed)
        
        # Baue Query
        if isbn:
            query = f'isbn:{isbn}'
        elif title and author:
            query = f'intitle:{title}+inauthor:{author}'
        elif title:
            query = f'intitle:{title}'
        else:
            return None
        
        # Cache prüfen
        cache_key = query.replace(':', '_').replace('+', '_').replace(' ', '_')
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # API-Abfrage
        try:
            url = f'https://www.googleapis.com/books/v1/volumes?q={urllib.parse.quote(query)}&maxResults=1'
            
            with urllib.request.urlopen(url, timeout=10) as response:
                self.last_api_call = time.time()
                data = json.loads(response.read().decode())
                
                # Cache speichern
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                return data
        
        except urllib.error.HTTPError as e:
            if e.code == 429:  # Too Many Requests
                print(f"  ⚠ API Rate Limit erreicht, warte 60 Sekunden...")
                time.sleep(60)
                return self.query_google_books_api(isbn, title, author)
            else:
                print(f"  HTTP Fehler {e.code}: {e.reason}")
        except Exception as e:
            print(f"  API-Fehler: {e}")
        
        return None
    
    def enrich_metadata(self, epub_metadata):
        """Reichert Metadaten mit Google Books API an"""
        enriched = epub_metadata.copy()
        enriched['google_books'] = {}
        enriched['genre_classified'] = 'Sonstiges'
        
        # Versuche zuerst mit ISBN
        api_data = None
        if epub_metadata['isbn_13']:
            api_data = self.query_google_books_api(isbn=epub_metadata['isbn_13'])
        elif epub_metadata['isbn_10']:
            api_data = self.query_google_books_api(isbn=epub_metadata['isbn_10'])
        
        # Fallback: Titel und Autor
        if not api_data and epub_metadata['title'] and epub_metadata['authors']:
            author = epub_metadata['authors'][0] if epub_metadata['authors'] else ''
            api_data = self.query_google_books_api(
                title=epub_metadata['title'],
                author=author
            )
        
        # Verarbeite API-Daten
        if api_data and 'items' in api_data and len(api_data['items']) > 0:
            book_info = api_data['items'][0]['volumeInfo']
            
            enriched['google_books'] = {
                'title': book_info.get('title', ''),
                'authors': book_info.get('authors', []),
                'publisher': book_info.get('publisher', ''),
                'published_date': book_info.get('publishedDate', ''),
                'description': book_info.get('description', ''),
                'categories': book_info.get('categories', []),
                'page_count': book_info.get('pageCount', 0),
                'language': book_info.get('language', ''),
                'average_rating': book_info.get('averageRating', 0),
                'thumbnail': book_info.get('imageLinks', {}).get('thumbnail', '')
            }
            
            # Genre-Klassifizierung
            enriched['genre_classified'] = self._classify_genre_from_api(enriched['google_books'])
            
            # Fülle fehlende Metadaten auf
            if not enriched['title'] and enriched['google_books']['title']:
                enriched['title'] = enriched['google_books']['title']
            
            if not enriched['authors'] and enriched['google_books']['authors']:
                enriched['authors'] = enriched['google_books']['authors']
            
            if not enriched['publisher'] and enriched['google_books']['publisher']:
                enriched['publisher'] = enriched['google_books']['publisher']
            
            if not enriched['published_date'] and enriched['google_books']['published_date']:
                enriched['published_date'] = enriched['google_books']['published_date']
            
            if not enriched['description'] and enriched['google_books']['description']:
                enriched['description'] = enriched['google_books']['description']
        
        return enriched
    
    def _classify_genre_from_api(self, google_books_data):
        """Klassifiziert Genre basierend auf Google Books Daten"""
        categories = google_books_data.get('categories', [])
        
        if not categories:
            return 'Sonstiges'
        
        # Versuche Kategorien zu mappen
        for category in categories:
            for pattern, german_genre in self.genre_mapping.items():
                if pattern.lower() in category.lower():
                    return german_genre
        
        # Fallback: Verwende erste Kategorie als Basis
        first_category = categories[0]
        
        # Einfache Heuristiken
        if 'fiction' in first_category.lower():
            if 'science' in first_category.lower():
                return 'Science Fiction'
            elif 'fantasy' in first_category.lower():
                return 'Fantasy'
            elif 'mystery' in first_category.lower() or 'thriller' in first_category.lower():
                return 'Krimi/Thriller'
            else:
                return 'Belletristik'
        elif 'biography' in first_category.lower():
            return 'Biografien/Memoiren'
        elif any(word in first_category.lower() for word in ['history', 'science', 'philosophy', 'psychology']):
            return 'Sachbücher'
        elif 'self-help' in first_category.lower() or 'health' in first_category.lower():
            return 'Ratgeber'
        
        return 'Sonstiges'
    
    def process_directory(self, directory, max_books=None, delay_between_books=1.0):
        """Verarbeitet alle EPUBs in einem Verzeichnis"""
        directory = Path(directory)
        
        print("=" * 80)
        print("METADATEN-ANREICHERUNG MIT GOOGLE BOOKS API")
        print("=" * 80)
        print(f"\nVerzeichnis: {directory}")
        print(f"Cache: {self.cache_dir}")
        print()
        
        # Finde alle EPUBs
        epub_files = list(directory.rglob('*.epub'))
        
        if max_books:
            epub_files = epub_files[:max_books]
        
        print(f"Gefunden: {len(epub_files)} EPUB-Dateien")
        print()
        
        results = []
        
        for i, epub_file in enumerate(epub_files, 1):
            print(f"[{i}/{len(epub_files)}] {epub_file.name}")
            
            # Extrahiere Basis-Metadaten
            epub_metadata = self.extract_epub_metadata(epub_file)
            
            if epub_metadata['title']:
                print(f"  Titel: {epub_metadata['title']}")
            if epub_metadata['authors']:
                print(f"  Autor: {', '.join(epub_metadata['authors'])}")
            if epub_metadata['isbn_13']:
                print(f"  ISBN-13: {epub_metadata['isbn_13']}")
            elif epub_metadata['isbn_10']:
                print(f"  ISBN-10: {epub_metadata['isbn_10']}")
            
            # Reichere mit API an
            enriched = self.enrich_metadata(epub_metadata)
            
            if enriched['google_books']:
                print(f"  ✓ Google Books Daten gefunden")
                if enriched['google_books']['categories']:
                    print(f"  Kategorien: {', '.join(enriched['google_books']['categories'])}")
                print(f"  Genre: {enriched['genre_classified']}")
            else:
                print(f"  ⚠ Keine Google Books Daten gefunden")
                print(f"  Genre: {enriched['genre_classified']} (Fallback)")
            
            results.append({
                'filepath': str(epub_file),
                'relative_path': str(epub_file.relative_to(directory)),
                'filename': epub_file.name,
                'metadata': enriched
            })
            
            print()
            
            # Verzögerung zwischen Büchern
            if i < len(epub_files):
                time.sleep(delay_between_books)
        
        return results
    
    def export_to_json(self, results, output_file):
        """Exportiert Ergebnisse als JSON"""
        output_path = Path(output_file)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ JSON-Export erstellt: {output_path}")
        return output_path
    
    def create_genre_report(self, results):
        """Erstellt einen Genre-Report"""
        genre_stats = defaultdict(int)
        genre_books = defaultdict(list)
        
        for result in results:
            genre = result['metadata']['genre_classified']
            genre_stats[genre] += 1
            genre_books[genre].append(result['filename'])
        
        print("\n" + "=" * 80)
        print("GENRE-VERTEILUNG")
        print("=" * 80)
        print()
        
        for genre in sorted(genre_stats.keys(), key=lambda x: genre_stats[x], reverse=True):
            count = genre_stats[genre]
            percentage = (count / len(results)) * 100
            print(f"{genre:30s}: {count:3d} Bücher ({percentage:5.1f}%)")
        
        print()
        print("=" * 80)
        print("DETAILLIERTE GENRE-ZUORDNUNG")
        print("=" * 80)
        
        for genre in sorted(genre_stats.keys()):
            print(f"\n{genre} ({genre_stats[genre]} Bücher):")
            print("-" * 80)
            for book in sorted(genre_books[genre])[:10]:
                print(f"  • {book}")
            if len(genre_books[genre]) > 10:
                print(f"  ... und {len(genre_books[genre]) - 10} weitere")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='eBook Metadata Enricher - Verbessert Metadaten mit Google Books API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  # Teste mit 10 Büchern
  python3 ebook_metadata_enricher.py /pfad/zu/eBooks --max-books 10
  
  # Verarbeite alle Bücher (langsam, wegen API Rate Limiting)
  python3 ebook_metadata_enricher.py /pfad/zu/eBooks --delay 2.0
  
  # Mit benutzerdefiniertem Cache
  python3 ebook_metadata_enricher.py /pfad/zu/eBooks --cache /pfad/zu/cache

Hinweise:
  - Google Books API hat Rate Limits (1000 Anfragen/Tag für kostenlose Nutzung)
  - Ergebnisse werden gecacht, um wiederholte API-Aufrufe zu vermeiden
  - Verwenden Sie --delay um API Rate Limits zu respektieren
  - ISBN-basierte Suchen sind am genauesten
        """
    )
    
    parser.add_argument(
        'directory',
        help='Pfad zum eBook-Verzeichnis'
    )
    
    parser.add_argument(
        '--max-books',
        type=int,
        help='Maximale Anzahl zu verarbeitender Bücher (für Tests)'
    )
    
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Verzögerung zwischen Büchern in Sekunden (Standard: 1.0)'
    )
    
    parser.add_argument(
        '--cache',
        help='Pfad zum Cache-Verzeichnis (Standard: ~/.cache/ebook_metadata)'
    )
    
    parser.add_argument(
        '--output',
        default='enriched_metadata.json',
        help='Name der JSON-Ausgabedatei (Standard: enriched_metadata.json)'
    )
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.directory):
        print(f"FEHLER: Verzeichnis nicht gefunden: {args.directory}")
        return 1
    
    # Erstelle Enricher
    enricher = MetadataEnricher(cache_dir=args.cache)
    
    # Verarbeite Verzeichnis
    results = enricher.process_directory(
        args.directory,
        max_books=args.max_books,
        delay_between_books=args.delay
    )
    
    if not results:
        print("Keine EPUBs gefunden!")
        return 0
    
    # Exportiere Ergebnisse
    enricher.export_to_json(results, args.output)
    
    # Erstelle Genre-Report
    enricher.create_genre_report(results)
    
    print("\n" + "=" * 80)
    print("ZUSAMMENFASSUNG")
    print("=" * 80)
    print(f"Verarbeitete Bücher: {len(results)}")
    
    with_google_data = sum(1 for r in results if r['metadata']['google_books'])
    print(f"Mit Google Books Daten: {with_google_data} ({(with_google_data/len(results)*100):.1f}%)")
    
    print(f"\nErgebnisse gespeichert in: {args.output}")
    print("\nNächste Schritte:")
    print("  1. Überprüfen Sie die Genre-Verteilung")
    print("  2. Verwenden Sie die enriched_metadata.json für die Reorganisation")
    print("  3. Optional: Nutzen Sie ebook_reorganize_v2.py für bessere Organisation")
    
    return 0


if __name__ == '__main__':
    exit(main())
