from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANDROID = ROOT / 'android'
REQUIRED = [
    ANDROID / 'settings.gradle',
    ANDROID / 'build.gradle',
    ANDROID / 'app/build.gradle',
    ANDROID / 'gradle.properties',
]

missing = [str(path.relative_to(ROOT)) for path in REQUIRED if not path.exists()]
if missing:
    raise SystemExit(f'Missing Android build files: {", ".join(missing)}')

build_gradle = (ANDROID / 'build.gradle').read_text(encoding='utf-8')
if 'com.android.tools.build:gradle:8.5.2' not in build_gradle:
    raise SystemExit('Android build must use direct com.android.tools.build:gradle:8.5.2 classpath resolution')
if 'com.android.application.gradle.plugin' in build_gradle:
    raise SystemExit('Android build should not depend on the com.android.application plugin marker')

gradle = shutil.which('gradle')
if not gradle:
    raise SystemExit('gradle executable not found')

result = subprocess.run([gradle, '--version'], cwd=ANDROID, text=True, capture_output=True, check=False, timeout=30)
if result.returncode != 0:
    raise SystemExit(result.stderr or result.stdout)

print('Android Gradle configuration sanity check passed.')
if not os.environ.get('ANDROID_HOME') and not os.environ.get('ANDROID_SDK_ROOT'):
    print('Warning: ANDROID_HOME/ANDROID_SDK_ROOT is not set; assembleDebug requires a local Android SDK.', file=sys.stderr)
