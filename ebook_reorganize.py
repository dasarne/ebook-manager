#!/usr/bin/env python3
"""
eBook Reorganizer - Organisiert eBooks nach Genre/Autor und behandelt Duplikate

Funktionen:
- Reorganisation nach Genre/Autor (Option B)
- Duplikate in Papierkorb verschieben
- Dry-Run Modus zum Testen
"""

import os
import re
import shutil
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import subprocess

class EbookReorganizer:
    def __init__(self, base_dir, dry_run=True):
        self.base_dir = Path(base_dir)
        self.dry_run = dry_run
        self.ebooks = []
        self.duplicates = defaultdict(list)
        self.moves = []  # Liste der geplanten Verschiebungen
        
        # Genre-Klassifizierung basierend auf Autoren und Stichwörtern
        self.genre_mapping = {
            'Science Fiction': [
                'asimov', 'isaac', 'sanderson', 'brandon', 'herbert', 'frank',
                'clarke', 'arthur', 'adams', 'douglas', 'foundation', 'dune',
                'neuromancer', 'ender', 'hyperion', 'mars', 'space', 'robot'
            ],
            'Fantasy': [
                'tolkien', 'rowling', 'harry potter', 'herr der ringe',
                'game of thrones', 'martin', 'pratchett', 'disc', 'wheel of time'
            ],
            'Krimi/Thriller': [
                'fitzek', 'sebastian', 'leon', 'donna', 'brunetti', 'coben',
                'child', 'reacher', 'mankell', 'larsson', 'millennium'
            ],
            'Belletristik': [
                'arenz', 'ewald', 'hansen', 'heidenreich', 'elke', 'strunk', 'heinz',
                'henn', 'carsten', 'rooney', 'sally', 'moyes', 'jojo', 'riley', 'lucinda',
                'garmus', 'bonnie', 'yarros', 'rebecca', 'wahl', 'caroline', 'abel', 'susanne',
                'pilgaard', 'stine', 'lee', 'felix', 'levithan', 'david', 'steinhoefel'
            ],
            'Sachbücher': [
                'precht', 'richard', 'philosophie', 'kast', 'bas', 'harari', 'yuval',
                'sapiens', 'deus', 'yogeshwar', 'ranga', 'wiest', 'brianna',
                'munroe', 'randall', 'what if', 'lauren', 'mark', 'fit ohne',
                'psychologie', 'geschichte', 'pid', 'regelungstechnik'
            ],
            'Biografien/Memoiren': [
                'mein', 'ich bin', 'meine mutter', 'autobio', 'leben von'
            ]
        }
    
    def classify_genre(self, author, title):
        """Klassifiziert ein eBook nach Genre basierend auf Autor und Titel"""
        search_text = f"{author} {title}".lower()
        
        # Zähle Treffer pro Genre
        genre_scores = defaultdict(int)
        
        for genre, keywords in self.genre_mapping.items():
            for keyword in keywords:
                if keyword in search_text:
                    genre_scores[genre] += 1
        
        # Rückgabe Genre mit höchstem Score, oder "Sonstiges"
        if genre_scores:
            return max(genre_scores.items(), key=lambda x: x[1])[0]
        
        # Zusätzliche Heuristiken
        if any(word in search_text for word in ['roman', 'erzählung', 'geschichte']):
            return 'Belletristik'
        
        return 'Sonstiges'
    
    def scan_ebooks(self):
        """Scannt das Verzeichnis nach allen eBooks"""
        print(f"Scanne Verzeichnis: {self.base_dir}")
        
        extensions = ['.epub', '.pdf', '.mobi', '.azw3']
        
        for ext in extensions:
            files = list(self.base_dir.rglob(f'*{ext}'))
            
            for filepath in files:
                # Überspringe versteckte Dateien und spezielle Ordner
                if any(part.startswith('.') for part in filepath.parts):
                    continue
                if '.sdr' in str(filepath):
                    continue
                    
                info = self.get_file_info(filepath)
                self.ebooks.append(info)
        
        print(f"Gefunden: {len(self.ebooks)} eBooks")
        return self.ebooks
    
    def get_file_info(self, filepath):
        """Sammelt Informationen über eine eBook-Datei"""
        stat = filepath.stat()
        extension = filepath.suffix.lower()
        
        # Parse Dateiname
        author, title = self.parse_filename(filepath)
        
        info = {
            'path': filepath,
            'relative_path': str(filepath.relative_to(self.base_dir)),
            'filename': filepath.name,
            'extension': extension,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'size_bytes': stat.st_size,
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'author': author,
            'title': title,
            'genre': ''
        }
        
        # Klassifiziere Genre
        info['genre'] = self.classify_genre(author, title)
        
        return info
    
    def parse_filename(self, filepath):
        """Extrahiert Autor und Titel aus Dateinamen"""
        filename = filepath.stem
        
        # Entferne bekannte Suffixe
        filename = re.sub(r'\(z-lib\.org\)', '', filename)
        filename = re.sub(r'\[.*?\]', '', filename)
        filename = re.sub(r'\(German Edition\)', '', filename)
        filename = re.sub(r'\(.*?Edition\)', '', filename)
        filename = filename.strip()
        
        author = ''
        title = ''
        
        # Versuche "Autor - Titel" Pattern
        if ' - ' in filename:
            parts = filename.split(' - ', 1)
            author = parts[0].strip()
            title = parts[1].strip()
        # Versuche "Nachname, Vorname" Pattern
        elif ',' in filename and ' - ' not in filename:
            parts = filename.split(',', 1)
            author = parts[0].strip()
            if len(parts) > 1:
                remaining = parts[1].strip()
                # Wenn nach dem Komma noch ein Vorname kommt
                if ' - ' in remaining:
                    name_parts = remaining.split(' - ', 1)
                    author = f"{author}, {name_parts[0].strip()}"
                    title = name_parts[1].strip()
                else:
                    title = remaining
        else:
            title = filename
            
        return author, title
    
    def find_duplicates(self):
        """Findet Duplikate (gleiches Buch in verschiedenen Formaten)"""
        print("\nSuche nach Duplikaten...")
        
        # Gruppiere nach normalisierten Titeln und Autoren
        title_groups = defaultdict(list)
        
        for ebook in self.ebooks:
            # Normalisiere für Vergleich
            normalized_title = re.sub(r'[^a-zA-Z0-9]', '', ebook['title'].lower())
            normalized_author = re.sub(r'[^a-zA-Z0-9]', '', ebook['author'].lower())
            
            if normalized_title:
                key = f"{normalized_author}_{normalized_title}"
                title_groups[key].append(ebook)
        
        # Finde Gruppen mit mehreren Dateien
        for key, books in title_groups.items():
            if len(books) > 1:
                self.duplicates[key] = books
        
        print(f"Gefunden: {len(self.duplicates)} Duplikat-Gruppen mit {sum(len(v) for v in self.duplicates.values())} Dateien")
        return self.duplicates
    
    def select_best_format(self, duplicate_group):
        """Wählt das beste Format aus einer Duplikat-Gruppe"""
        # Präferenz-Reihenfolge: EPUB > PDF > MOBI > AZW3
        format_priority = {'.epub': 4, '.pdf': 3, '.mobi': 2, '.azw3': 1}
        
        # Sortiere nach Format-Priorität, dann nach Dateigröße
        sorted_books = sorted(
            duplicate_group,
            key=lambda x: (format_priority.get(x['extension'], 0), x['size_bytes']),
            reverse=True
        )
        
        return sorted_books[0], sorted_books[1:]  # Beste, Rest
    
    def sanitize_filename(self, name):
        """Bereinigt Datei-/Ordnernamen für Dateisystem"""
        # Entferne/ersetze problematische Zeichen
        name = re.sub(r'[<>:"|?*]', '', name)
        name = re.sub(r'[/\\]', '-', name)
        name = name.strip('. ')
        # Kürze wenn nötig
        if len(name) > 200:
            name = name[:200]
        return name
    
    def create_reorganization_plan(self):
        """Erstellt einen Plan zur Reorganisation"""
        print("\nErstelle Reorganisations-Plan...")
        
        # Neue Basis-Struktur
        new_base = self.base_dir.parent / "eBooks_neu"
        trash_dir = self.base_dir.parent / "eBooks_Papierkorb"
        
        # Verarbeite Duplikate
        duplicates_to_trash = []
        kept_books = set()
        
        for key, books in self.duplicates.items():
            best, rest = self.select_best_format(books)
            kept_books.add(best['path'])
            
            for book in rest:
                duplicates_to_trash.append({
                    'source': book['path'],
                    'target': trash_dir / book['relative_path'],
                    'reason': f"Duplikat von {best['filename']}"
                })
        
        # Verarbeite alle Bücher (außer die zum Papierkorb verschobenen)
        for ebook in self.ebooks:
            if ebook['path'] in kept_books or ebook['path'] not in [d['source'] for d in duplicates_to_trash]:
                # Bestimme Zielort
                genre = ebook['genre']
                author = self.sanitize_filename(ebook['author']) if ebook['author'] else "Unbekannter_Autor"
                
                # Zielverzeichnis: Genre/Autor/
                target_dir = new_base / genre / author
                target_file = target_dir / ebook['filename']
                
                self.moves.append({
                    'source': ebook['path'],
                    'target': target_file,
                    'genre': genre,
                    'author': author,
                    'is_duplicate': False
                })
        
        # Füge Duplikate hinzu
        for dup in duplicates_to_trash:
            self.moves.append({
                'source': dup['source'],
                'target': dup['target'],
                'genre': 'Papierkorb',
                'author': '',
                'is_duplicate': True,
                'reason': dup['reason']
            })
        
        print(f"Geplante Operationen: {len(self.moves)}")
        print(f"  - {len(self.moves) - len(duplicates_to_trash)} Bücher zu reorganisieren")
        print(f"  - {len(duplicates_to_trash)} Duplikate in Papierkorb")
        
        return self.moves
    
    def print_plan_summary(self):
        """Zeigt eine Zusammenfassung des Plans"""
        print("\n" + "=" * 80)
        print("REORGANISATIONS-PLAN ZUSAMMENFASSUNG")
        print("=" * 80)
        
        # Gruppiere nach Genre
        by_genre = defaultdict(int)
        duplicates_count = 0
        
        for move in self.moves:
            if move['is_duplicate']:
                duplicates_count += 1
            else:
                by_genre[move['genre']] += 1
        
        print("\nBücher pro Genre:")
        for genre in sorted(by_genre.keys()):
            print(f"  {genre:30s}: {by_genre[genre]:3d} Bücher")
        
        print(f"\nDuplikate in Papierkorb: {duplicates_count}")
        
        print("\n" + "-" * 80)
        print("BEISPIEL-VERSCHIEBUNGEN (erste 10):")
        print("-" * 80)
        for i, move in enumerate(self.moves[:10]):
            source = move['source'].relative_to(self.base_dir)
            target = move['target']
            if move['is_duplicate']:
                print(f"{i+1}. [DUPLIKAT] {source}")
                print(f"   -> Papierkorb/{target.name}")
                print(f"   Grund: {move.get('reason', 'Duplikat')}")
            else:
                print(f"{i+1}. {source}")
                print(f"   -> {move['genre']}/{move['author']}/{target.name}")
            print()
    
    def execute_reorganization(self):
        """Führt die Reorganisation aus"""
        if self.dry_run:
            print("\n" + "!" * 80)
            print("DRY-RUN MODUS - Es werden KEINE Dateien verschoben!")
            print("!" * 80)
            return
        
        print("\n" + "=" * 80)
        print("STARTE REORGANISATION")
        print("=" * 80)
        
        success = 0
        errors = []
        
        for i, move in enumerate(self.moves, 1):
            try:
                source = move['source']
                target = move['target']
                
                # Erstelle Zielverzeichnis
                target.parent.mkdir(parents=True, exist_ok=True)
                
                # Verschiebe Datei
                shutil.move(str(source), str(target))
                success += 1
                
                if i % 50 == 0:
                    print(f"Fortschritt: {i}/{len(self.moves)} Dateien verschoben...")
                    
            except Exception as e:
                errors.append({
                    'source': source,
                    'error': str(e)
                })
        
        print(f"\n✓ Erfolgreich: {success} Dateien")
        if errors:
            print(f"✗ Fehler: {len(errors)} Dateien")
            print("\nFehlerhafte Dateien:")
            for err in errors[:10]:
                print(f"  - {err['source']}: {err['error']}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='eBook Reorganizer - Organisiert nach Genre/Autor',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'directory',
        nargs='?',
        default='/home/arne/Schreibtisch/eBooks',
        help='Pfad zum eBook-Verzeichnis'
    )
    
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Führt die Reorganisation durch (ohne diesen Flag nur Vorschau)'
    )
    
    args = parser.parse_args()
    
    # Prüfe Verzeichnis
    if not os.path.isdir(args.directory):
        print(f"FEHLER: Verzeichnis nicht gefunden: {args.directory}")
        return 1
    
    print("=" * 80)
    print("eBook REORGANIZER - Genre/Autor Organisation")
    print("=" * 80)
    print()
    
    if not args.execute:
        print("⚠ DRY-RUN MODUS - Es werden keine Dateien verschoben!")
        print("   Verwenden Sie --execute um die Reorganisation durchzuführen")
        print()
    
    # Erstelle Reorganizer
    reorganizer = EbookReorganizer(args.directory, dry_run=not args.execute)
    
    # Scanne eBooks
    reorganizer.scan_ebooks()
    
    if not reorganizer.ebooks:
        print("Keine eBooks gefunden!")
        return 0
    
    # Finde Duplikate
    reorganizer.find_duplicates()
    
    # Erstelle Plan
    reorganizer.create_reorganization_plan()
    
    # Zeige Zusammenfassung
    reorganizer.print_plan_summary()
    
    if not args.execute:
        print("\n" + "=" * 80)
        print("NÄCHSTER SCHRITT:")
        print("=" * 80)
        print("Führen Sie das Skript mit --execute aus, um die Reorganisation durchzuführen:")
        print(f"  python3 {__file__} {args.directory} --execute")
        print()
    else:
        # Bestätigung einholen
        print("\n" + "!" * 80)
        print("WARNUNG: Diese Operation verschiebt Dateien!")
        print("!" * 80)
        response = input("\nMöchten Sie fortfahren? (ja/nein): ")
        
        if response.lower() in ['ja', 'j', 'yes', 'y']:
            reorganizer.execute_reorganization()
            print("\n✓ Reorganisation abgeschlossen!")
        else:
            print("\nAbgebrochen.")
    
    return 0


if __name__ == '__main__':
    exit(main())
