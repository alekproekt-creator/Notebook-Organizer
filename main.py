
import json
import sys
from collections import deque
from datetime import datetime
from typing import List, Dict, Any, Optional

DATA_FILE = "notebook.json"

class Note:
    def __init__(self, title: str, text: str, tags: List[str], date: Optional[str] = None):
        self.title = title.strip()
        self.text = text.strip()
        self.tags = [t.strip() for t in tags if t.strip()]
        self.date = date or datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.__class__.__name__,
            "title": self.title,
            "text": self.text,
            "tags": self.tags,
            "date": self.date,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]):
        typ = d.get("type", "TextNote")
        mapping = {"TextNote": TextNote, "VoiceNote": VoiceNote}
        ctor = mapping.get(typ, TextNote)
        return ctor(d.get("title", ""), d.get("text", ""), d.get("tags", []), d.get("date"))

class TextNote(Note):
    pass

class VoiceNote(Note):
    # For simplicity voice note stores text as transcript and may have duration in tags or text.
    pass

class Notebook:
    def __init__(self):
        self.notes: List[Note] = []
        self.undo_stack = deque(maxlen=100)

    def load(self, path: str = DATA_FILE):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.notes = [Note.from_dict(d) for d in data if isinstance(d, dict)]
            print(f"Loaded {len(self.notes)} notes.")
        except FileNotFoundError:
            self.notes = []
            print("Data file not found. Starting with empty notebook.")
        except json.JSONDecodeError:
            self.notes = []
            print("Data file corrupt. Starting with empty notebook.")

    def save(self, path: str = DATA_FILE):
        with open(path, "w", encoding="utf-8") as f:
            json.dump([n.to_dict() for n in self.notes], f, ensure_ascii=False, indent=2)
        print(f"Saved {len(self.notes)} notes to {path}.")

    def list(self):
        if not self.notes:
            print("No notes.")
            return
        for i, n in enumerate(self.notes, 1):
            print(f"{i}. [{n.__class__.__name__}] {n.title} | tags: {', '.join(n.tags)} | date: {n.date}")

    def create(self, note: Note):
        self.notes.append(note)
        self.undo_stack.append(("delete", len(self.notes) - 1, None))
        print("Note added.")

    def read(self, index: int) -> Optional[Note]:
        if 0 <= index < len(self.notes):
            return self.notes[index]
        print("Invalid index.")
        return None

    def update(self, index: int, new_note: Note):
        if 0 <= index < len(self.notes):
            old = self.notes[index]
            self.notes[index] = new_note
            self.undo_stack.append(("update", index, old))
            print("Note updated.")
        else:
            print("Invalid index.")

    def delete(self, index: int):
        if 0 <= index < len(self.notes):
            old = self.notes.pop(index)
            self.undo_stack.append(("create", index, old))
            print("Note deleted.")
        else:
            print("Invalid index.")

    def undo(self):
        if not self.undo_stack:
            print("Nothing to undo.")
            return
        action, index, payload = self.undo_stack.pop()
        if action == "delete":
            # undo of create => remove at index
            if 0 <= index < len(self.notes):
                self.notes.pop(index)
            print("Undo: remove recent note.")
        elif action == "create":
            # undo of delete => insert payload back
            if payload:
                self.notes.insert(index, payload)
            print("Undo: restore deleted note.")
        elif action == "update":
            if 0 <= index < len(self.notes) and payload:
                self.notes[index] = payload
            print("Undo: revert update.")
        else:
            print("Unknown undo action.")

    def filter_by_tag(self, tag: str) -> List[Note]:
        return [n for n in self.notes if tag in n.tags]

    def filter_by_date(self, date_str: str) -> List[Note]:
        # date_str can be YYYY-MM-DD or ISO prefix
        return [n for n in self.notes if n.date.startswith(date_str)]

def input_nonempty(prompt: str) -> str:
    s = input(prompt).strip()
    while not s:
        print("Cannot be empty.")
        s = input(prompt).strip()
    return s

def input_tags(prompt: str) -> List[str]:
    s = input(prompt).strip()
    if not s:
        return []
    return [t.strip() for t in s.split(",") if t.strip()]

def main():
    nb = Notebook()
    nb.load()

    while True:
        print("\nNotebook Organizer")
        print("1 List  2 Create  3 Read  4 Update  5 Delete  6 Filter  7 Undo  8 Save  9 Quit")
        cmd = input("Choose: ").strip()
        if cmd == "1":
            nb.list()
        elif cmd == "2":
            typ = input("Type (text/voice) [text]: ").strip().lower() or "text"
            title = input_nonempty("Title: ")
            text = input_nonempty("Text: ")
            tags = input_tags("Tags (comma-separated): ")
            note = TextNote(title, text, tags) if typ == "text" else VoiceNote(title, text, tags)
            nb.create(note)
        elif cmd == "3":
            idx = input("Index: ").strip()
            if not idx.isdigit():
                print("Index must be number.")
                continue
            n = nb.read(int(idx) - 1)
            if n:
                print(json.dumps(n.to_dict(), ensure_ascii=False, indent=2))
        elif cmd == "4":
            idx = input("Index: ").strip()
            if not idx.isdigit():
                print("Index must be number.")
                continue
            i = int(idx) - 1
            old = nb.read(i)
            if not old:
                continue
            print("Leave empty to keep current value.")
            title = input(f"Title [{old.title}]: ").strip() or old.title
            text = input(f"Text [{old.text[:30]}...]: ").strip() or old.text
            tags = input(f"Tags (comma) [{', '.join(old.tags)}]: ").strip()
            tags_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else old.tags
            new = old.__class__(title,text, tags_list, old.date)
            nb.update(i, new)
        elif cmd == "5":
            idx = input("Index: ").strip()
            if not idx.isdigit():
                print("Index must be number.")
                continue
            nb.delete(int(idx) - 1)
        elif cmd == "6":
            sub = input("Filter by tag (t) or date (d)? ").strip().lower()
            if sub == "t":
                tag = input_nonempty("Tag: ")
                res = nb.filter_by_tag(tag)
                for i, n in enumerate(res, 1):
                    print(f"{i}. {n.title} | {n.tags} | {n.date}")
            elif sub == "d":
                d = input_nonempty("Date (YYYY-MM-DD): ")
                res = nb.filter_by_date(d)
                for i, n in enumerate(res, 1):
                    print(f"{i}. {n.title} | {n.tags} | {n.date}")
            else:
                print("Unknown filter.")
        elif cmd == "7":
            nb.undo()
        elif cmd == "8":
            nb.save()
        elif cmd == "9":
            ans = input("Save before exit? (y/n): ").strip().lower()
            if ans == "y":
                nb.save()
            print("Bye.")
            break
        else:
            print("Unknown command.")

if __name__ == "__main__":
    main()


