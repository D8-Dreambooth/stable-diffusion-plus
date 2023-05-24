import os
import hashlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class ModelWatcher:
    def __init__(self):
        self.directories = []
        self.observer = Observer()
        self.handler = ModelEventHandler(self.process_changes)

    def start(self):
        for directory in self.directories:
            self.observer.schedule(self.handler, directory, recursive=True)
        self.observer.start()
        print("ModelWatcher started.")

    def stop(self):
        self.observer.stop()
        self.observer.join()
        print("ModelWatcher stopped.")

    async def process_changes(self, event):
        if event.event_type in ['created', 'modified']:
            if event.is_directory:
                directory_hash = self.calculate_directory_hash(event.src_path)
                print(f"Directory modified: {event.src_path} - Hash: {directory_hash}")
                # Trigger your desired function with the directory path and hash
            else:
                file_hash = self.calculate_file_hash(event.src_path)
                print(f"File modified: {event.src_path} - Hash: {file_hash}")
                # Trigger your desired function with the file path and hash

    def calculate_directory_hash(self, directory):
        hasher = hashlib.sha256()
        for root, _, files in os.walk(directory):
            for file in files:
                with open(os.path.join(root, file), "rb") as f:
                    hasher.update(f.read())
        return hasher.hexdigest()

    def calculate_file_hash(self, file):
        hasher = hashlib.sha256()
        with open(file, "rb") as f:
            hasher.update(f.read())
        return hasher.hexdigest()

    def register_directory(self, directory):
        if directory not in self.directories:
            self.directories.append(directory)
            if self.observer.is_alive():
                self.observer.schedule(self.handler, directory, recursive=True)
                print(f"New directory registered: {directory}")


class ModelEventHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback

    def on_any_event(self, event):
        self.callback(event)
