from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'android/app/src/main/assets/www'
FILES = [
    'index.html',
    'styles.css',
    'app.js',
    'sw.js',
    'manifest.webmanifest',
    'assets/icon.svg',
    'config/features.json',
]

for relative in FILES:
    source = ROOT / relative
    target = DEST / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
print(f'Synced {len(FILES)} web assets into {DEST.relative_to(ROOT)}')
