#!/usr/bin/env python3
"""
classify.py — clasificador de archivos a estructura Windows-style.

Algoritmo:
1. Pre-pass: detecta carpetas ATÓMICAS (software bundles, sitios web, código,
   juegos). Una carpeta es atómica si tiene marcadores adentro (.exe/.dll/.sys,
   .git/, index.html) o está en la whitelist HARD_ATOMIC. Las atómicas viajan
   enteras al destino sin descomponerse.

2. Main pass: para cada archivo,
   - Si tiene un ancestro atómico → va con esa unidad.
   - Sino, recorre el path buscando un anchor Windows-style (Desktop, Documents,
     Pictures, Videos, Music, Downloads, DCIM, Movies, etc.). Lo que viene
     después del anchor es el path relativo en el destino.
   - Si no hay anchor → fallback por extensión.

Mobile (Pixel 7 Stock + (backup celu)) tiene anchors propios.
Takeout pasa entero a ARCHIVOS/ sin descomprimir.

Uso:
    python3 classify.py --inventory inventory.tsv --out classification.csv

Output: TSV con columnas [size, source, dest, rule]
        + summary en classification_summary.txt
"""
import os, csv, re, sys, argparse
from collections import Counter, defaultdict

EXT = {
  'pic':  {'.jpg','.jpeg','.png','.gif','.bmp','.heic','.webp','.tif','.tiff','.ico','.svg','.psd','.ai','.cr2','.nef','.dng','.raw'},
  'vid':  {'.mp4','.mkv','.avi','.mov','.flv','.wmv','.webm','.m4v','.3gp','.mpg','.mpeg','.ts','.vob'},
  'mus':  {'.mp3','.flac','.wav','.ogg','.m4a','.aac','.opus','.wma','.aiff'},
  'doc':  {'.docx','.doc','.pdf','.txt','.odt','.rtf','.csv','.md','.xlsx','.xls','.pptx','.ppt','.tex','.epub','.mobi','.azw3','.numbers','.pages','.key'},
  'inst': {'.exe','.msi','.dmg','.deb','.rpm','.appimage','.apk','.aab','.bat','.cmd','.ps1'},
  'arch': {'.zip','.rar','.7z','.tgz','.tar','.gz','.bz2','.xz','.iso','.img','.cab','.lzma'},
  'rom':  {'.smc','.sfc','.nes','.snes','.gba','.gb','.gbc','.n64','.z64','.v64','.nds','.3ds','.gcm','.cdi','.chd','.pbp','.cso','.rvz','.wad','.gci'},
  'code': {'.py','.js','.ts','.tsx','.jsx','.cpp','.c','.h','.hpp','.java','.go','.rs','.rb','.php','.sql','.sh','.json','.xml','.yaml','.yml','.toml','.ini','.cfg','.conf','.lock'},
}
SOFTWARE_FILES = {'.exe','.dll','.msi','.so','.dylib','.jar','.sys','.efi'}
CODE_DIRS = {'.git','node_modules','venv','.venv','.vscode','.idea'}
SITE_FILES = {'index.html','sitemap.xml'}

# Windows-style anchors (case-insensitive). Maps lower-case anchor -> dest bucket
ANCHORS = {
    'desktop': 'Desktop',
    'documents': 'Documents',
    'documento': 'Documents',
    'documentos': 'Documents',
    'pictures': 'Pictures',
    'picture': 'Pictures',
    'images': 'Pictures',
    'photos': 'Pictures',
    'fotos': 'Pictures',
    'dcim': 'Pictures',
    'editedonlinephotos': 'Pictures',
    'screenshots': 'Pictures',
    'videos': 'Videos',
    'video': 'Videos',
    'movies': 'Videos',
    'films': 'Videos',
    'music': 'Music',
    'música': 'Music',
    'musica': 'Music',
    'audio': 'Music',
    'downloads': 'Downloads',
    'download': 'Downloads',
    'descargas': 'Downloads',
    'torrents': 'Downloads/Torrents',
    'saved games': 'Games/SavedGames',
    'savegames': 'Games/SavedGames',
    'roms': 'Games/ROMs',
    'whatsapp': 'WhatsApp',
}
# Anchors specific to MOBILE
MOBILE_ANCHORS = {
    'dcim': 'Camera',
    'pictures': 'Pictures',
    'editedonlinephotos': 'Pictures',
    'movies': 'Videos',
    'documents': 'Documents',
    'download': 'Downloads',
    'audiobooks': 'Audio',
    'alarms': 'Audio',
    'music': 'Audio',
    'notifications': 'Audio',
    'ringtones': 'Audio',
    'whatsapp': 'WhatsApp',
    'android': 'AndroidData',
}

BOOK_HINT = re.compile(r'(book|libro|novel|farmer|asimov|gurps|solaris|riverworld|stanley[ _]kramer|herencia[ _]del[ _]viento|philip[ _]jose)', re.I)

def index_inventory():
    files = []
    with open(INV) as f:
        for line in f:
            parts = line.rstrip('\n').split('\t', 1)
            if len(parts)!=2: continue
            size = int(parts[0])
            src = parts[1]
            if src.startswith('./'): src = src[2:]
            files.append((size, src))
    return files

def find_atomic_units(files):
    """Find folders that should travel as atomic units.
    Returns dict: folder_path -> ('Software'|'Sites'|'Code'|'Games', display_name)
    """
    # Build folder file list
    folder_contents = defaultdict(list)
    for sz, src in files:
        comps = src.split('/')
        for i in range(1, len(comps)):
            folder = '/'.join(comps[:i])
            folder_contents[folder].append((comps[i:], sz))

    atomic = {}

    # Hardcoded atomic folder names (anywhere in tree)
    HARD_ATOMIC = {
        'PCSX2': 'Games', 'PCSX2_2': 'Games',
        'PSXDownloadHelper': 'Games', 'M5Stack-nesemu-master': 'Games',
        'snes9x-1.60-win32-x64': 'Games', 'virtuanes097e': 'Games',
        'Solaris (1971) [BluRay] [720p] [YTS.AM]': 'Videos-Bundle',
        'La herencia del viento (Stanley Kramer, 1960) [HDTVRip 720 Dual].mkv': None,
        '[Anime Time] Steins;Gate Complete Series (Steins;Gate + Steins;Gate 0 + OVAs + Specials + Movie) [BD] [Dual Audio][1080p][HEVC 10bit x265][Opus][Eng Sub]': 'Videos-Bundle',
        'Chrono-Trigger-Original-Sound-Version': 'Music-Bundle',
        'FalkonPortable': 'Software',
        'TeamViewerPortable': 'Software',
        'SurfacePro_Win10_150723_0': 'Software',
        'TL-WR841HP(UN)_V5_210914': 'Software',
        'DELL_E2010HT-MONITOR_A00-00_R222126': 'Software',
        'Symbols-0.65.0-x64': 'Software',
        'Telegram Desktop': 'Software',
        'flash_download_tools_v3.6.3_0': 'Software',
        'HDD.Regenerator.v1.71.incl.key': 'Software',
        'Flasheo_ARS-Junio2020': 'Software',
        'mb_bios_b450-aorus-m_f63b': 'Software',
        'all-in-one-wp-migration.6.72': 'Software',
        'magento2-btcpay-module': 'Code',
        'samourai': 'Bitcoin',
        'electrum_data': 'Bitcoin',
        'IT4Bitcoin': 'Bitcoin',
        'IT4Crypto': 'Bitcoin',
        'CoinEx - Athena Bitcoin - 2do mes': 'Bitcoin',
        'CoinEx x Athena Bitcoin (Size Revised)': 'Bitcoin',
        'athena': 'Bitcoin',
        'Mis lugares Web': 'Sites',
        'ATMs Website': 'Sites',
        '⚡Stupidcache⚡ (@stupidcache) _ Twitter_files': 'Sites',
        'Farmer, Philip Jose': 'Books-Bundle',
        'CAMPAÑA ROL': 'Games/CampañaRol',
        'UPLOADS': 'Pictures-Bundle',
        'Saved Pictures': 'Pictures-Bundle',
        'EditedOnlinePhotos': 'Pictures-Bundle',
        'mails': 'Documents/Email',
        'mails (1)': 'Documents/Email',
        'Mensajeria': 'Documents/Mensajeria',
        'Compressed': 'Software',  # contains zip archives
        'Programs': 'Software',
        'Navegadores': 'Software',
        'Corel x3': 'Software',
        'beta': 'Software', 'beta64': 'Software',
        'updated': 'Software', 'updated64': 'Software',
        'makehuman-1.1.1-win32': 'Software',
        'smf_2-0-17_install': 'Software',
        'Software': 'Software',
        'Miguel': 'Other',  # personal folder, keep as unit
        'Victorval': 'Other',
        'free_modern_business_card_psd': 'Other',
        'expenses': 'Documents/Expenses',
        'kleopatra.asc': None,
        'Huawei': 'Pictures-Bundle',  # subfolder under Temp, contains DCIM mostly
    }

    for folder, contents in folder_contents.items():
        name = folder.split('/')[-1]
        if name in HARD_ATOMIC:
            cat = HARD_ATOMIC[name]
            if cat:
                atomic[folder] = (cat, name)

    # Also auto-detect: any folder containing software/code/site markers as atomic
    # but skip if already inside an atomic ancestor or is a Windows anchor folder
    for folder, contents in folder_contents.items():
        if folder in atomic: continue
        name = folder.split('/')[-1]
        if name.lower() in ANCHORS: continue  # don't atomize anchors

        # Check ancestors
        if any(folder.startswith(af+'/') for af in atomic):
            continue

        has_sw = False
        has_code = False
        has_site = False
        for relparts, sz in contents:
            base = relparts[-1]
            ext = os.path.splitext(base)[1].lower()
            if ext in SOFTWARE_FILES: has_sw = True
            if base.lower() in SITE_FILES and len(relparts) <= 3: has_site = True
            for cm in CODE_DIRS:
                if cm in relparts: has_code = True

        # Decision: only atomize if folder is at reasonable depth (not too deep, not too shallow)
        depth = folder.count('/')
        if depth < 1 or depth > 3: continue  # only top 1-3 levels
        if name.lower() in {'temp','user','nueva carpeta','nueva carpeta (2)','120gb','2021','android','data','obb','media'}:
            continue  # known wrapper-like folders
        if has_sw and len(contents) >= 5:
            atomic[folder] = ('Software', name)
        elif has_site and len(contents) >= 3:
            atomic[folder] = ('Sites', name)
        elif has_code and len(contents) >= 5:
            atomic[folder] = ('Code', name)

    return atomic

def find_anchor(comps, mobile=False):
    """Walk components and return (anchor_index, bucket) or (None, None)."""
    table = MOBILE_ANCHORS if mobile else ANCHORS
    for i, c in enumerate(comps):
        cl = c.lower()
        if cl in table:
            return i, table[cl]
    return None, None

def classify_loose(rel_path, size, mobile=False):
    """Classify single file by extension when no anchor and no atomic ancestor."""
    name = os.path.basename(rel_path)
    ext = os.path.splitext(name)[1].lower()
    if mobile:
        if ext in EXT['pic']: return 'Pictures'
        if ext in EXT['vid']: return 'Videos'
        if ext in EXT['mus']: return 'Audio'
        if ext in EXT['inst']: return 'Apps'
        if ext in EXT['doc']: return 'Documents'
        if ext in EXT['arch']: return 'Downloads'
        return 'Other'
    if ext in EXT['rom']: return 'Games/ROMs'
    if ext in EXT['inst']: return 'Software'
    if ext in EXT['arch']:
        return 'Software' if size > 500*1024*1024 else 'Downloads'
    if ext in EXT['pic']: return 'Pictures'
    if ext in EXT['vid']: return 'Videos'
    if ext in EXT['mus']: return 'Music'
    if ext in EXT['code']: return 'Code'
    if ext in {'.epub','.mobi','.azw3'}: return 'Books'
    if ext == '.pdf':
        return 'Books' if BOOK_HINT.search(rel_path) else 'Documents'
    if ext in EXT['doc']: return 'Documents'
    return 'Other'

def parse_args():
    ap = argparse.ArgumentParser(description='Clasificador a estructura Windows-style.')
    ap.add_argument('--inventory', '-i', default='inventory.tsv',
                    help='Inventario TSV con columnas size\tpath. Default: inventory.tsv')
    ap.add_argument('--out', '-o', default='classification.tsv',
                    help='Output TSV con clasificación. Default: classification.tsv')
    ap.add_argument('--summary', '-s', default='classification_summary.txt',
                    help='Output summary humano-legible. Default: classification_summary.txt')
    return ap.parse_args()

def main():
    args = parse_args()
    global INV, OUT, SUM
    INV = args.inventory
    OUT = args.out
    SUM = args.summary

    files = index_inventory()
    print(f'[{len(files)} archivos en inventario]', file=sys.stderr)
    atomic = find_atomic_units(files)
    print(f'[{len(atomic)} unidades atómicas detectadas]', file=sys.stderr)

    rows = []
    counts = Counter()
    sizes = Counter()
    sample = defaultdict(list)
    rule_counts = Counter()

    # Sort atomic by depth desc so we match deepest first
    atomic_paths_sorted = sorted(atomic.keys(), key=lambda p: -p.count('/'))

    for sz, src in files:
        comps = src.split('/')
        if not comps: continue
        top = comps[0]
        if top in ('$RECYCLE.BIN','System Volume Information','ORGANIZADO'):
            continue

        # MOBILE detection
        is_mobile = False
        if top == 'Pixel 7 Stock (julio 24)':
            is_mobile = True
        elif top == 'Nueva Carpeta (C)' and len(comps) > 1 and comps[1] == '(backup celu)':
            is_mobile = True

        # Takeout
        if top == 'Takeout':
            dest = f'ARCHIVOS/Takeout/{"/".join(comps[1:])}'
            rows.append((sz, src, dest, 'takeout'))
            counts['ARCHIVOS/Takeout'] += 1
            sizes['ARCHIVOS/Takeout'] += sz
            rule_counts['takeout'] += 1
            if len(sample['ARCHIVOS/Takeout']) < 3:
                sample['ARCHIVOS/Takeout'].append((src, dest))
            continue

        if is_mobile:
            # Strip prefix
            if top == 'Pixel 7 Stock (julio 24)':
                rest_comps = comps[1:]
            else:  # Nueva Carpeta (C)/(backup celu)/...
                rest_comps = comps[2:]
            if not rest_comps:
                continue
            ai, abucket = find_anchor(rest_comps, mobile=True)
            if ai is not None:
                after = rest_comps[ai+1:]
                if after and after[0].lower() in {"camera","screenshots","100andro","100media","100msdcf","dji album","dji export","goscam","opencamera","oneplus camera","saved pictures"}:
                    after = after[1:]
                if not after: after = [rest_comps[-1]]
                rest = '/'.join(after)
                dest = f'MOBILE/{abucket}/{rest}'
                rule = f'mobile-anchor-{abucket}'
            else:
                bucket = classify_loose(src, sz, mobile=True)
                rest = '/'.join(rest_comps)
                dest = f'MOBILE/{bucket}/{rest}'
                rule = f'mobile-loose-{bucket}'
            rows.append((sz, src, dest, rule))
            ck = '/'.join(dest.split('/')[:2])
            counts[ck] += 1; sizes[ck] += sz
            rule_counts[rule] += 1
            if len(sample[ck]) < 3:
                sample[ck].append((src, dest))
            continue

        # PC sources: 80gb sata, ORDENAR, Nueva Carpeta (C)/Nueva carpeta*
        # Strip top-level prefix(es) that are wrappers
        if top == 'Nueva Carpeta (C)':
            if len(comps) < 3: continue
            # strip "Nueva Carpeta (C)/Nueva carpeta" or "/Nueva carpeta (2)"
            rest_comps = comps[2:]
        else:
            rest_comps = comps[1:]
        if not rest_comps:
            continue

        # Reconstruct folder paths and check atomic ancestor
        atomic_match = None
        for ap in atomic_paths_sorted:
            ap_comps = ap.split('/')
            # Is ap an ancestor of src? src starts with ap + '/' AND src != ap
            if src == ap: continue
            if src.startswith(ap + '/'):
                atomic_match = ap
                break

        if atomic_match:
            cat, display = atomic[atomic_match]
            # rel path inside atomic
            rel_inside = src[len(atomic_match)+1:]
            # cat may include slashes (e.g. Games/CampañaRol)
            if cat.endswith('-Bundle'):
                bk = cat[:-len('-Bundle')]
                dest = f'PC/{bk}/{display}/{rel_inside}'
                ck = f'PC/{bk}'
            else:
                dest = f'PC/{cat}/{display}/{rel_inside}'
                ck = f'PC/{cat.split("/")[0]}'
            rule = f'atomic-{cat}'
            rows.append((sz, src, dest, rule))
            counts[ck] += 1; sizes[ck] += sz
            rule_counts[rule] += 1
            if len(sample[ck]) < 3:
                sample[ck].append((src, dest))
            continue

        # Anchor walk
        ai, abucket = find_anchor(rest_comps, mobile=False)
        if ai is not None:
            rest_after = '/'.join(rest_comps[ai+1:]) if ai+1 < len(rest_comps) else rest_comps[ai]
            if not rest_after: rest_after = rest_comps[-1]
            dest = f'PC/{abucket}/{rest_after}'
            rule = f'anchor-{abucket}'
            ck = f'PC/{abucket.split("/")[0]}'
            rows.append((sz, src, dest, rule))
            counts[ck] += 1; sizes[ck] += sz
            rule_counts[rule] += 1
            if len(sample[ck]) < 3:
                sample[ck].append((src, dest))
            continue

        # Loose by extension
        bucket = classify_loose(src, sz)
        rest = '/'.join(rest_comps)
        dest = f'PC/{bucket}/{rest}'
        rule = f'loose-{bucket}'
        ck = f'PC/{bucket.split("/")[0]}'
        rows.append((sz, src, dest, rule))
        counts[ck] += 1; sizes[ck] += sz
        rule_counts[rule] += 1
        if len(sample[ck]) < 3:
            sample[ck].append((src, dest))

    # Save
    with open(OUT,'w') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(['size','source','dest','rule'])
        for sz, src, dest, rule in rows:
            w.writerow([sz, src, dest, rule])

    with open(SUM,'w') as f:
        f.write('=== RESUMEN POR DESTINO ===\n')
        for k,c in sorted(counts.items(), key=lambda x:-sizes[x[0]]):
            gib = sizes[k]/(1024**3)
            f.write(f'  {k:<35s}  {c:6d} archivos  {gib:7.2f} GiB\n')
        f.write(f'\nTOTAL: {sum(counts.values())} archivos  {sum(sizes.values())/(1024**3):.2f} GiB\n')
        f.write(f'\nUnidades atómicas detectadas: {len(atomic)}\n')
        for ap,(cat,name) in sorted(atomic.items()):
            f.write(f'  [{cat}] {ap}\n')
        f.write('\n=== EJEMPLOS POR DESTINO (3 c/u) ===\n')
        for k in sorted(sample):
            f.write(f'\n[{k}]\n')
            for src,dest in sample[k]:
                f.write(f'  {src}\n   → {dest}\n')

    print(open(SUM).read())

main()
