from pathlib import Path

required = [
    Path('index.html'),
    Path('styles.css'),
    Path('app.js'),
    Path('sw.js'),
    Path('manifest.webmanifest'),
    Path('assets/icon.svg'),
    Path('config/features.json'),
    Path('android/app/src/main/AndroidManifest.xml'),
    Path('android/app/src/main/java/com/networksystemtools/app/MainActivity.java'),
    Path('backend/agent_server.py'),
    Path('scripts/sync_android_assets.py'),
    Path('scripts/check_android_build_env.py'),
    Path('android/app/src/main/assets/www/index.html'),
    Path('android/app/src/main/assets/www/app.js'),
    Path('logs/.gitignore'),
    Path('tools/.gitkeep'),
    Path('tools/builtin/connectivity_check.json'),
    Path('tools/builtin/dns_lookup.json'),
    Path('tools/builtin/http_headers.json'),
    Path('tools/builtin/local_inventory.json'),
    Path('tools/builtin/recovery_checklist.json'),
    Path('tools/builtin/log_review.json'),
    Path('android/gradle.properties'),
]


missing = [str(path) for path in required if not path.exists()]
if missing:
    raise SystemExit(f"Missing required app files: {', '.join(missing)}")

index = Path('index.html').read_text(encoding='utf-8')
for expected in ('manifest.webmanifest', 'styles.css', 'app.js'):
    if expected not in index:
        raise SystemExit(f"index.html does not reference {expected}")

manifest = Path('manifest.webmanifest').read_text(encoding='utf-8')
for expected in ('standalone', 'Network System Tools', 'assets/icon.svg'):
    if expected not in manifest:
        raise SystemExit(f"manifest.webmanifest missing {expected}")

print('Static PWA files validated.')


features = Path('config/features.json').read_text(encoding='utf-8')
for expected in ('"tiering": "disabled"', '"paidFeatures": false', '"androidWrapper": true', '"aiChat": true', '"internetKillSwitch": true', '"toolUploadDownload": true', '"builtInToolCatalog": true'):
    if expected not in features:
        raise SystemExit(f"config/features.json missing {expected}")

android_main = Path('android/app/src/main/java/com/networksystemtools/app/MainActivity.java').read_text(encoding='utf-8')
if 'WebView' not in android_main or 'file:///android_asset/www/index.html' not in android_main:
    raise SystemExit('Android wrapper must define a WebView and load bundled www assets')


agent = Path('backend/agent_server.py').read_text(encoding='utf-8')
for expected in ('whiterabbitneo', 'human consent required', 'internet_enabled', 'ALLOWLIST'):
    if expected not in agent:
        raise SystemExit(f'backend/agent_server.py missing {expected}')


android_build = Path('android/build.gradle').read_text(encoding='utf-8')
if 'com.android.tools.build:gradle:8.5.2' not in android_build:
    raise SystemExit('android/build.gradle must resolve AGP through the direct classpath artifact')
if 'com.android.application.gradle.plugin' in android_build:
    raise SystemExit('android/build.gradle must not use the plugin-marker module')


for path in sorted(Path('tools/builtin').glob('*.json')):
    text = path.read_text(encoding='utf-8')
    for expected in ('"name"', '"category"', '"requiresConsent"', '"safety"'):
        if expected not in text:
            raise SystemExit(f'{path} missing {expected}')
