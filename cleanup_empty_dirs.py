#!/usr/bin/env python3
"""
Cleanup Empty Directories - Entfernt leere Ordner aus eBook-Sammlung

Funktionen:
- Findet alle leeren Ordner rekursiv
- Dry-Run Modus zum Testen
- Löscht leere Ordner von unten nach oben (Kindordner zuerst)
- Erstellt Bericht über gelöschte Ordner
"""

import os
from pathlib import Path
from collections import defaultdict

class EmptyDirectoryCleaner:
    def __init__(self, base_dir, dry_run=True):
        self.base_dir = Path(base_dir)
        self.dry_run = dry_run
        self.empty_dirs = []
        self.stats = defaultdict(int)
        
    def find_empty_directories(self):
        """Findet alle leeren Ordner rekursiv"""
        print(f"Scanne Verzeichnis: {self.base_dir}")
        
        # Sammle alle Ordner (von unten nach oben für sicheres Löschen)
        all_dirs = []
        for root, dirs, files in os.walk(self.base_dir, topdown=False):
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                all_dirs.append(dir_path)
        
        # Prüfe welche leer sind
        for dir_path in all_dirs:
            try:
                # Prüfe ob Ordner leer ist (keine Dateien, keine Unterordner)
                if not any(dir_path.iterdir()):
                    self.empty_dirs.append(dir_path)
                    
                    # Kategorisiere nach Ebene
                    relative_path = dir_path.relative_to(self.base_dir)
                    depth = len(relative_path.parts)
                    self.stats[f'depth_{depth}'] += 1
                    
                    # Kategorisiere nach Genre (wenn in Genre-Ordner)
                    if len(relative_path.parts) >= 1:
                        genre = relative_path.parts[0]
                        self.stats[f'genre_{genre}'] += 1
                        
            except Exception as e:
                print(f"  Warnung: Fehler beim Prüfen von {dir_path}: {e}")
        
        print(f"✓ Gefunden: {len(self.empty_dirs)} leere Ordner")
        return self.empty_dirs
    
    def print_summary(self):
        """Zeigt Zusammenfassung der gefundenen leeren Ordner"""
        print("\n" + "=" * 80)
        print("LEERE ORDNER - ZUSAMMENFASSUNG")
        print("=" * 80)
        
        if not self.empty_dirs:
            print("\n✓ Keine leeren Ordner gefunden!")
            return
        
        print(f"\nGesamt: {len(self.empty_dirs)} leere Ordner\n")
        
        # Nach Genre gruppieren
        by_genre = defaultdict(list)
        for dir_path in self.empty_dirs:
            relative_path = dir_path.relative_to(self.base_dir)
            if len(relative_path.parts) >= 1:
                genre = relative_path.parts[0]
                by_genre[genre].append(dir_path)
            else:
                by_genre['_root'].append(dir_path)
        
        print("Leere Ordner pro Genre:")
        for genre in sorted(by_genre.keys()):
            count = len(by_genre[genre])
            print(f"  {genre:30s}: {count:3d} Ordner")
        
        # Beispiele zeigen
        print("\n" + "-" * 80)
        print("BEISPIELE (erste 20 leere Ordner):")
        print("-" * 80)
        for i, dir_path in enumerate(self.empty_dirs[:20], 1):
            relative = dir_path.relative_to(self.base_dir)
            print(f"{i:3d}. {relative}")
        
        if len(self.empty_dirs) > 20:
            print(f"     ... und {len(self.empty_dirs) - 20} weitere")
    
    def delete_empty_directories(self):
        """Löscht alle leeren Ordner"""
        if self.dry_run:
            print("\n" + "!" * 80)
            print("DRY-RUN MODUS - Es werden KEINE Ordner gelöscht!")
            print("!" * 80)
            return
        
        print("\n" + "=" * 80)
        print("LÖSCHE LEERE ORDNER")
        print("=" * 80)
        
        deleted = 0
        errors = []
        
        # Lösche von unten nach oben (Kindordner zuerst)
        for dir_path in self.empty_dirs:
            try:
                if dir_path.exists() and not any(dir_path.iterdir()):
                    dir_path.rmdir()
                    deleted += 1
                    if deleted % 10 == 0:
                        print(f"Fortschritt: {deleted}/{len(self.empty_dirs)} gelöscht")
            except Exception as e:
                errors.append({
                    'path': str(dir_path),
                    'error': str(e)
                })
        
        print(f"\n✓ Erfolgreich gelöscht: {deleted} Ordner")
        
        if errors:
            print(f"✗ Fehler: {len(errors)}")
            print("\nFehlerhafte Ordner:")
            for err in errors[:10]:
                print(f"  {err['path']}")
                print(f"    Fehler: {err['error']}")
            if len(errors) > 10:
                print(f"  ... und {len(errors) - 10} weitere Fehler")
    
    def create_report(self, output_file='empty_dirs_report.txt'):
        """Erstellt detaillierten Bericht"""
        report_path = self.base_dir.parent / output_file
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("LEERE ORDNER - DETAILLIERTER BERICHT\n")
            f.write("=" * 80 + "\n\n")
            
            from datetime import datetime
            f.write(f"Erstellt am: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Verzeichnis: {self.base_dir}\n")
            f.write(f"Gefundene leere Ordner: {len(self.empty_dirs)}\n\n")
            
            # Nach Genre gruppieren
            by_genre = defaultdict(list)
            for dir_path in self.empty_dirs:
                relative_path = dir_path.relative_to(self.base_dir)
                if len(relative_path.parts) >= 1:
                    genre = relative_path.parts[0]
                    by_genre[genre].append(relative_path)
            
            f.write("-" * 80 + "\n")
            f.write("NACH GENRE\n")
            f.write("-" * 80 + "\n\n")
            
            for genre in sorted(by_genre.keys()):
                f.write(f"\n{genre} ({len(by_genre[genre])} leere Ordner):\n")
                f.write("-" * 80 + "\n")
                for path in sorted(by_genre[genre]):
                    f.write(f"  {path}\n")
        
        print(f"\n✓ Bericht erstellt: {report_path}")
        return report_path


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Cleanup Empty Directories - Entfernt leere Ordner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  # Zeige leere Ordner (Dry-Run)
  python3 cleanup_empty_dirs.py /pfad/zu/eBooks
  
  # Lösche leere Ordner
  python3 cleanup_empty_dirs.py /pfad/zu/eBooks --execute
  
  # Mit Bericht
  python3 cleanup_empty_dirs.py /pfad/zu/eBooks --report empty_dirs.txt

Hinweise:
  - Verwenden Sie immer zuerst den Dry-Run Modus
  - Ordner werden von unten nach oben gelöscht (sicher)
  - Nur komplett leere Ordner werden gelöscht
        """
    )
    
    parser.add_argument(
        'directory',
        help='Pfad zum zu bereinigenden Verzeichnis'
    )
    
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Löscht die leeren Ordner (ohne diesen Flag nur Vorschau)'
    )
    
    parser.add_argument(
        '--report',
        default='empty_dirs_report.txt',
        help='Name der Berichtsdatei (Standard: empty_dirs_report.txt)'
    )
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.directory):
        print(f"FEHLER: Verzeichnis nicht gefunden: {args.directory}")
        return 1
    
    print("=" * 80)
    print("CLEANUP EMPTY DIRECTORIES")
    print("=" * 80)
    print()
    
    if not args.execute:
        print("⚠ DRY-RUN MODUS - Es werden keine Ordner gelöscht!")
        print("   Verwenden Sie --execute um Ordner zu löschen")
        print()
    
    # Erstelle Cleaner
    cleaner = EmptyDirectoryCleaner(args.directory, dry_run=not args.execute)
    
    # Finde leere Ordner
    cleaner.find_empty_directories()
    
    if not cleaner.empty_dirs:
        print("\n✓ Keine leeren Ordner gefunden!")
        return 0
    
    # Zeige Zusammenfassung
    cleaner.print_summary()
    
    # Erstelle Bericht
    cleaner.create_report(args.report)
    
    if not args.execute:
        print("\n" + "=" * 80)
        print("NÄCHSTER SCHRITT:")
        print("=" * 80)
        print("Überprüfen Sie die Liste und führen Sie dann aus:")
        print(f"  python3 {__file__} {args.directory} --execute")
        print()
    else:
        # Bestätigung
        print("\n" + "!" * 80)
        print("WARNUNG: Diese Operation löscht Ordner!")
        print("!" * 80)
        print(f"\nEs werden {len(cleaner.empty_dirs)} leere Ordner gelöscht.")
        response = input("Möchten Sie fortfahren? (ja/nein): ")
        
        if response.lower() in ['ja', 'j', 'yes', 'y']:
            cleaner.delete_empty_directories()
            print("\n✓ Bereinigung abgeschlossen!")
            
            # Erstelle aktualisierten Bericht
            cleaner.find_empty_directories()
            if cleaner.empty_dirs:
                print(f"\n⚠ Achtung: {len(cleaner.empty_dirs)} Ordner konnten nicht gelöscht werden")
                cleaner.create_report(f"remaining_{args.report}")
            else:
                print("\n✓ Alle leeren Ordner wurden erfolgreich gelöscht!")
        else:
            print("\nAbgebrochen.")
    
    return 0


if __name__ == '__main__':
    exit(main())
