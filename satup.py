import os
import sys
import re
import time
import shutil
import sqlite3
import logging
import subprocess
from pathlib import Path
from threading import Thread

# Third-party integrations with safe fallbacks
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False

try:
    from send2trash import send2trash
    HAS_SEND2TRASH = True
except ImportError:
    HAS_SEND2TRASH = False

# ==========================================
# 1. CONFIGURATION
# ==========================================
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "solis_ai.db"
LOG_FILE = BASE_DIR / "solis_system.log"

# Setup logging to file (to keep terminal clean)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8')
    ]
)
logger = logging.getLogger("SOLIS_AI")

# Safety System: Protected System Directories
CRITICAL_DIRS = [
    "C:\\Windows",
    "C:\\Program Files",
    "C:\\Program Files (x86)",
    "C:\\System Volume Information",
    "C:\\$Recycle.Bin",
    "/System",
    "/Library",
    "/usr",
    "/bin",
    "/sbin",
    "/etc"
]

DEFAULT_SCAN_ROOT = str(Path.home() / "Documents")  # Default workspace

# ==========================================
# 2. LOCAL DATABASE HANDLER
# ==========================================
class DatabaseHandler:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.create_tables()

    def create_tables(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE,
                    name TEXT,
                    extension TEXT,
                    size INTEGER,
                    created_at REAL,
                    modified_at REAL
                )
            """)
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_name ON files(name);")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_ext ON files(extension);")

    def insert_file(self, file_path, name, ext, size, created, modified):
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO files (path, name, extension, size, created_at, modified_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (str(file_path), name, ext, size, created, modified))
        except sqlite3.Error as e:
            logger.error(f"DB Error: {e}")

    def insert_bulk(self, records):
        try:
            with self.conn:
                self.conn.executemany("""
                    INSERT OR REPLACE INTO files (path, name, extension, size, created_at, modified_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, records)
        except sqlite3.Error as e:
            logger.error(f"DB Bulk Error: {e}")

    def remove_file(self, file_path):
        try:
            with self.conn:
                self.conn.execute("DELETE FROM files WHERE path = ?", (str(file_path),))
        except sqlite3.Error as e:
            logger.error(f"DB Delete Error: {e}")

    def search_files(self, query):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT name, path, extension, size FROM files 
            WHERE name LIKE ? OR path LIKE ? 
            LIMIT 100
        """, (f"%{query}%", f"%{query}%"))
        return cursor.fetchall()

    def find_by_extension(self, extension):
        cursor = self.conn.cursor()
        ext = extension if extension.startswith('.') else f".{extension}"
        cursor.execute("""
            SELECT name, path, extension, size FROM files 
            WHERE LOWER(extension) = LOWER(?)
            LIMIT 100
        """, (ext,))
        return cursor.fetchall()


# ==========================================
# 3. SAFETY & FILE MANAGEMENT
# ==========================================
class FileManager:
    def __init__(self, db_handler):
        self.db = db_handler

    def is_safe_path(self, target_path: str) -> bool:
        try:
            resolved = Path(target_path).resolve()
            for critical in CRITICAL_DIRS:
                crit_path = Path(critical).resolve()
                if crit_path in resolved.parents or resolved == crit_path:
                    return False
            return True
        except Exception:
            return False

    def create_file(self, path: str, content: str = "Created by SOLIS AI.") -> str:
        if not self.is_safe_path(path):
            return "Security Alert: Access to system directory is restricted."
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            self.db.insert_file(str(p), p.name, p.suffix, p.stat().st_size, p.stat().st_ctime, p.stat().st_mtime)
            return f"Success: File created at {p}"
        except Exception as e:
            return f"Error: {str(e)}"

    def create_directory(self, path: str) -> str:
        if not self.is_safe_path(path):
            return "Security Alert: Access to system directory is restricted."
        try:
            p = Path(path)
            p.mkdir(parents=True, exist_ok=True)
            return f"Success: Directory created at {p}"
        except Exception as e:
            return f"Error: {str(e)}"

    def delete_item(self, path: str, force: bool = False) -> str:
        if not self.is_safe_path(path):
            return "Security Alert: System directories cannot be deleted."
        p = Path(path)
        if not p.exists():
            return "Error: File or Directory does not exist."
        try:
            if not force and HAS_SEND2TRASH:
                send2trash(str(p))
                self.db.remove_file(str(p))
                return f"Success: Sent to Recycle Bin: {p.name}"
            else:
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
                self.db.remove_file(str(p))
                return f"Success: Permanently deleted: {p.name}"
        except Exception as e:
            return f"Error: {str(e)}"

    def move_item(self, src: str, dest: str) -> str:
        if not self.is_safe_path(src) or not self.is_safe_path(dest):
            return "Security Alert: Access to system directory is restricted."
        try:
            shutil.move(src, dest)
            self.db.remove_file(src)
            p = Path(dest)
            if p.exists() and p.is_file():
                self.db.insert_file(str(p), p.name, p.suffix, p.stat().st_size, p.stat().st_ctime, p.stat().st_mtime)
            return f"Success: Moved item to {dest}"
        except Exception as e:
            return f"Error: {str(e)}"


# ==========================================
# 4. BACKGROUND FILE MONITORING
# ==========================================
class FileWatcherHandler(FileSystemEventHandler):
    def __init__(self, db_handler):
        super().__init__()
        self.db = db_handler

    def on_created(self, event):
        if not event.is_directory:
            self._update_record(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self.db.remove_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._update_record(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self.db.remove_file(event.src_path)
            self._update_record(event.dest_path)

    def _update_record(self, path_str):
        try:
            p = Path(path_str)
            if p.exists() and p.is_file():
                stat = p.stat()
                self.db.insert_file(str(p), p.name, p.suffix, stat.st_size, stat.st_ctime, stat.st_mtime)
        except Exception:
            pass


# ==========================================
# 5. SEMANTIC COMMAND PROCESSOR (AI CORE)
# ==========================================
class NLPEngine:
    def __init__(self, file_manager, db_handler):
        self.fm = file_manager
        self.db = db_handler

    def parse_command(self, user_input: str) -> dict:
        text = user_input.strip().lower()

        # Command: Find / Search
        match_search = re.search(r"(?:find|search|look for)\s+(.+)", text)
        if match_search:
            query = match_search.group(1).replace("files", "").replace("file", "").strip()
            if query.startswith("*.") or query.startswith("."):
                ext = query.replace("*", "")
                results = self.db.find_by_extension(ext)
                return {"intent": "search", "response": f"Found {len(results)} file(s) with extension '{ext}':", "data": results}
            results = self.db.search_files(query)
            return {"intent": "search", "response": f"Found {len(results)} match(es) for '{query}':", "data": results}

        # Command: Create Folder
        match_folder = re.search(r"(?:create|make|build)\s+(?:folder|directory)\s+(?:named\s+)?(.+)", user_input, re.IGNORECASE)
        if match_folder:
            name = match_folder.group(1).strip()
            target_path = Path(DEFAULT_SCAN_ROOT) / name
            result = self.fm.create_directory(str(target_path))
            return {"intent": "create_dir", "response": result, "data": []}

        # Command: Create File
        match_file = re.search(r"(?:create|make|write)\s+(?:file|document)\s+(?:named\s+)?(.+)", user_input, re.IGNORECASE)
        if match_file:
            name = match_file.group(1).strip()
            target_path = Path(DEFAULT_SCAN_ROOT) / name
            result = self.fm.create_file(str(target_path))
            return {"intent": "create_file", "response": result, "data": []}

        # Command: Delete File
        match_delete = re.search(r"(?:delete|remove|erase)\s+(.+)", user_input, re.IGNORECASE)
        if match_delete:
            target_name = match_delete.group(1).strip()
            results = self.db.search_files(target_name)
            if results:
                file_to_delete = results[0][1]
                result = self.fm.delete_item(file_to_delete)
                return {"intent": "delete", "response": f"Action on '{results[0][0]}': {result}", "data": []}
            return {"intent": "delete", "response": f"Could not find any file named '{target_name}' to delete.", "data": []}

        # Help Screen / Unrecognized
        return {
            "intent": "help",
            "response": (
                "Available commands:\n"
                "  • 'find *.py' or 'find *.docx' (Search by file type)\n"
                "  • 'search filename' (Search by term)\n"
                "  • 'create folder FolderName' (Create a folder inside Documents)\n"
                "  • 'create file filename.txt' (Create a file inside Documents)\n"
                "  • 'delete filename.txt' (Delete file safely)\n"
                "  • 'index' (To run system file indexing)\n"
                "  • 'help' (Show this menu)\n"
                "  • 'exit' or 'quit' (Exit application)"
            ),
            "data": []
        }


# ==========================================
# 6. TERMINAL APP ENGINE
# ==========================================
class SolisTerminalApp:
    def __init__(self):
        self.db = DatabaseHandler(DB_PATH)
        self.fm = FileManager(self.db)
        self.nlp = NLPEngine(self.fm, self.db)
        self.watcher_observer = None

    def start_background_watcher(self):
        if HAS_WATCHDOG:
            try:
                handler = FileWatcherHandler(self.db)
                self.watcher_observer = Observer()
                self.watcher_observer.schedule(handler, path=DEFAULT_SCAN_ROOT, recursive=True)
                self.watcher_observer.start()
                print(f"[*] Live File Monitoring Active on: {DEFAULT_SCAN_ROOT}")
            except Exception as e:
                print(f"[!] Monitoring could not start: {e}")
        else:
            print("[!] Install 'watchdog' package to enable real-time tracking.")

    def run_indexing(self):
        print("[*] Reindexing local files... Please wait.")
        records = []
        count = 0
        scan_path = Path(DEFAULT_SCAN_ROOT)
        if not scan_path.exists():
            scan_path.mkdir(parents=True, exist_ok=True)

        for root, dirs, files in os.walk(str(scan_path)):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ["__pycache__", "node_modules"]]
            for file in files:
                file_path = Path(root) / file
                try:
                    stat = file_path.stat()
                    records.append((
                        str(file_path),
                        file,
                        file_path.suffix,
                        stat.st_size,
                        stat.st_ctime,
                        stat.st_mtime
                    ))
                    count += 1
                except Exception:
                    continue

                if len(records) >= 150:
                    self.db.insert_bulk(records)
                    records = []

        if records:
            self.db.insert_bulk(records)
        print(f"[*] Indexing Sweep Completed. {count} item(s) cached in local DB.")

    def print_table(self, data):
        if not data:
            return
        # Print results in a structured terminal table
        print("-" * 90)
        print(f"{'File Name':<25} | {'Type':<6} | {'Size (KB)':<10} | {'Full Path'}")
        print("-" * 90)
        for name, path, ext, size in data:
            size_kb = max(1, round(size / 1024))
            name_trunc = name[:23] + ".." if len(name) > 25 else name
            path_trunc = path[:45] + ".." if len(path) > 47 else path
            print(f"{name_trunc:<25} | {ext:<6} | {size_kb:<10} | {path_trunc}")
        print("-" * 90)

    def start(self):
        print("==================================================")
        print("          SOLIS AI - TERMINAL ASSISTANT           ")
        print("==================================================")
        print(f"Database Path: {DB_PATH}")
        print(f"Default Scan Directory: {DEFAULT_SCAN_ROOT}")
        print("Type 'help' to see the commands.")
        print("==================================================")

        # Initial fast indexing on startup
        self.run_indexing()
        self.start_background_watcher()

        while True:
            try:
                user_input = input("\nSOLIS AI > ").strip()
                if not user_input:
                    continue

                if user_input.lower() in ["exit", "quit"]:
                    print("[*] Shutting down SOLIS AI. Goodbye!")
                    break

                if user_input.lower() == "index":
                    self.run_indexing()
                    continue

                # Parse and execute using NLP engine
                parsed = self.nlp.parse_command(user_input)
                print(f"\nSOLIS: {parsed['response']}")

                # Display table if search results are returned
                if parsed["intent"] == "search" and parsed["data"]:
                    self.print_table(parsed["data"])

            except (KeyboardInterrupt, EOFError):
                print("\n[*] Interrupted. Exiting SOLIS AI.")
                break
            except Exception as e:
                print(f"[!] System encountered an error: {e}")

        # Cleanup watcher
        if self.watcher_observer and self.watcher_observer.is_alive():
            self.watcher_observer.stop()
            self.watcher_observer.join()


# ==========================================
# 7. MAIN ENTRYPOINT
# ==========================================
if __name__ == "__main__":
    app = SolisTerminalApp()
    app.start()