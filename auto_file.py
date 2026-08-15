import os
import subprocess
import fnmatch
from taxt_to_speak import speak
import asyncio
# =========================
# CUSTOM DESKTOP PATH (YOUR PATH)
# =========================
desktop_path = r"C:\Users\HP\OneDrive\Desktop"

documents_path = os.path.join(os.path.expanduser("~"), "Documents")
downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")

search_paths = [desktop_path, documents_path, downloads_path]

# =========================
# CREATE FILE ON YOUR DESKTOP
# =========================
def create_file_desktop(filename, content=""):
    try:
        file_path = os.path.join(desktop_path, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"✅ File created at: {file_path}"
    except Exception as e:
        return f"❌ Error: {e}"

# =========================
# SEARCH FILE
# =========================
def search_file(filename):
    matches = []
    for path in search_paths:
        for root, dirs, files in os.walk(path):
            for name in files:
                if fnmatch.fnmatch(name.lower(), filename.lower()):
                    matches.append(os.path.join(root, name))
    return matches

# =========================
# OPEN FILE LOCATION
# =========================
def open_file_location(file_path):
    subprocess.run(f'explorer /select,"{file_path}"')

# =========================
# DELETE FILE
# =========================
def delete_file(filename):
    results = search_file(filename)

    if not results:
        return "❌ File not found"

    file_path = results[0]
    open_file_location(file_path)
    os.remove(file_path)

    
   #
# =========================
# AI COMMAND SYSTEM
# =========================
def ai_command(command):
    command = command.lower()

    if "create file" in command:
        name = command.replace("create file", "").strip()
        asyncio.run(speak(f"Creating file named {name} on desktop sir"))
        return create_file_desktop(name, "# Created by Dipu AI")

    elif "find file" in command:
        name = command.replace("find file", "").strip()
        results = search_file(name)
        asyncio.run(speak(f"Searching for file named {name} sir"))

        if results:
            open_file_location(results[0])
            return "🔍 Found:\n" + "\n".join(results[:5])
        else:
            return "❌ File not found"

    elif "delete file" in command:
        name = command.replace("delete file", "").strip()
        asyncio.run(speak(f"Deleting file named {name} sir"))
        return delete_file(name)


# =========================
# MAIN
# =========================
