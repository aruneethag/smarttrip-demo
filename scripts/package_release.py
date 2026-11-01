"""Build an allowlisted source archive, never copying runtime data or secrets."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
FILES = ['server.py','planner.py','schema.py','README.md','.gitignore','.env.example',
         '.python-version','requirements.txt','render.yaml']
FOLDERS = ['static','schemas','tests','scripts','docs']

def release_files():
    selected = [ROOT / name for name in FILES]
    for folder in FOLDERS:
        selected += sorted(p for p in (ROOT / folder).rglob('*')
                           if p.is_file() and '__pycache__' not in p.parts and p.suffix in ['.py','.json','.html','.css','.js','.md'])
    return selected

def main():
    target=ROOT/'release'/'smarttrip-render.zip'
    target.parent.mkdir(exist_ok=True)
    with ZipFile(target,'w',ZIP_DEFLATED) as archive:
        for path in release_files():
            archive.write(path,path.relative_to(ROOT).as_posix())
    print(f'Created {target} ({len(release_files())} source files). No runtime data, screenshots, or credentials included.')

if __name__=='__main__':main()
