from pathlib import Path
import os
import secrets

directory = Path(__file__).resolve().parent
names = [line.split("=", 1)[0] for line in (directory / ".env.example").read_text().splitlines()]
with os.fdopen(os.open(directory / ".env", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w") as env:
    for name in names:
        env.write(f"{name}={secrets.token_hex(32)}\n")
