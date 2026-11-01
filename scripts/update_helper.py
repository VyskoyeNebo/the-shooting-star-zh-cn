"""No-API update helper; Codex scheduled tasks provide new translations."""
import argparse
import hashlib
import json
import pathlib
import re
import urllib.parse
import urllib.request
import zipfile

from archive_tools import ClassFile, archive_nodes, discover_helpers, encrypted_strings, readable
import localizer

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = ROOT / '.work/update'
PROJECT = 1719195


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def request(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
    return urllib.request.urlopen(req, timeout=60)


def catalog():
    files = []
    index = 0
    total = None
    while total is None or len(files) < total:
        url = f'https://www.curseforge.com/api/v1/mods/{PROJECT}/files?pageIndex={index}&pageSize=50&sort=dateCreated&sortDescending=true&removeAlphas=false'
        with request(url) as response:
            data = json.load(response)
        count = data['pagination']['totalCount']
        if total is not None and total != count:
            raise RuntimeError('The upstream catalog changed during pagination; retry the check.')
        total = count
        assert data['data'] or len(files) == total, 'Incomplete upstream catalog'
        files += data['data']
        index += 1
        assert index <= 200, 'Unexpected upstream page count'
    assert len(files) == total == len({f['id'] for f in files})
    return files


def new_files(files, published):
    done = {f['id'] for f in published['files']}
    return sorted((f for f in files if f['id'] not in done), key=lambda f: f['id'])


def source_record(item):
    name = item['fileName']
    assert name == pathlib.PurePosixPath(name).name and '\\' not in name
    assert re.fullmatch(r'[A-Za-z0-9_.+ -]+\.jar', name), 'Unexpected archive filename'
    result = {k: item[k] for k in ['id', 'displayName', 'fileName', 'fileLength', 'dateCreated', 'gameVersions']}
    result['source_url'] = f'https://www.curseforge.com/minecraft/mc-mods/the-shooting-star-demo/files/{item["id"]}'
    result['download_url'] = f'https://edge.forgecdn.net/files/{item["id"] // 1000}/{item["id"] % 1000}/' + urllib.parse.quote(name)
    return result


def download(item):
    record = source_record(item)
    path = WORK / 'originals' / str(item['id']) / record['fileName']
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.stat().st_size != item['fileLength']:
        temp = path.with_suffix('.download')
        with request(record['download_url']) as response, temp.open('wb') as target:
            while chunk := response.read(1024 * 1024):
                target.write(chunk)
        assert temp.stat().st_size == item['fileLength'], 'Source length mismatch'
        temp.replace(path)
    with zipfile.ZipFile(path) as jar:
        assert jar.testzip() is None
    record['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    record['local_path'] = str(path.relative_to(WORK))
    return record


def inventory(record, memory):
    mandatory = {}
    review = {}
    nodes = []
    source = WORK / record['local_path']
    for node, jar in archive_nodes(source.read_bytes()):
        class_files = {n: ClassFile(jar.read(n)) for n in jar.namelist() if n.endswith('.class') and '/shootingstardemo/' in n}
        helpers = discover_helpers(class_files)
        languages = {}
        for name in jar.namelist():
            if '/lang/' in name and name.endswith('/en_us.json'):
                english = json.loads(jar.read(name))
                languages[name] = len(english)
                for key, value in english.items():
                    if value not in memory:
                        mandatory.setdefault(value, []).append({'node': node, 'language': name, 'key': key})
        for name, cf in class_files.items():
            for index, entry in enumerate(cf.cp):
                if not entry or entry[0] not in (17, 18):
                    continue
                bsm, nat = cf.pair(index)
                _, desc = cf.pair(nat)
                if cf.utf(desc) not in {'()Ljava/lang/String;', 'Ljava/lang/String;'}:
                    continue
                owner, _, _ = cf.method_ref(cf.bootstraps[bsm][0])
                if not owner.startswith('java/') and owner not in helpers:
                    raise RuntimeError('Unrecognized text bootstrap; inspect the new build before publishing: ' + owner)
                if entry[0] == 17:
                    raise RuntimeError('A new constant-dynamic string format requires inspection before publishing.')
            plain = [cf.string(i) for i, e in enumerate(cf.cp) if e and e[0] == 8]
            dynamic = encrypted_strings(cf, helpers)
            texts = plain + [text for _, _, text in dynamic]
            if any('needs more letters or strokes than a title holds' in text for text in texts):
                continue
            for text in texts:
                if text in memory or not readable(text) or '\n' in text:
                    continue
                if re.search('[A-Za-z]', text) and (' ' in text or text.isupper()):
                    review.setdefault(text, []).append({'node': node, 'class': name})
        nodes.append({'path': node, 'languages': languages, 'mod_class_count': len(class_files), 'encrypted_pools': list(helpers)})
    assert sum(n['mod_class_count'] for n in nodes) > 0, 'The mod namespace changed; inspect it before adapting the localizer.'
    return {'file': record, 'required_translations': mandatory, 'constants_to_review': review, 'nodes': nodes}


def build_file(record):
    memory = read(ROOT / 'translations/translation-memory.json')
    source = WORK / record['local_path']
    raw = source.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == record['sha256']
    localizer.configure(memory, WORK / 'verify', read(ROOT / 'translations/rimulib/zh_cn.json'))
    nodes, changes = [], []
    translated = localizer.archive(raw, record['id'], '', nodes, changes)
    filename = pathlib.Path(record['fileName']).stem + '--cf' + str(record['id']) + '--zh_cn.jar'
    dest = ROOT / 'dist' / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(translated)
    result = {k: v for k, v in record.items() if k != 'local_path'}
    result.update({'translated_filename': filename, 'translated_sha256': hashlib.sha256(translated).hexdigest(),
                   'translated_size': len(translated), 'nodes': nodes, 'checks_passed': True, 'in_game_tested': False})
    write(WORK / 'builds' / (str(record['id']) + '.json'), result)
    write(WORK / 'reports' / (str(record['id']) + '-changes.json'), changes)
    (ROOT / 'dist' / (str(record['id']) + '-SHA256SUMS.txt')).write_text(result['translated_sha256'] + '  ' + filename + '\n', encoding='utf-8')
    print(f'BUILT {record["id"]}: {filename}', flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['check', 'prepare', 'build'])
    parser.add_argument('--file-id', type=int, action='append', default=[])
    args = parser.parse_args()
    if args.command == 'build':
        plan = read(WORK / 'plan.json')
        selected = [x['file'] for x in plan['files'] if not args.file_id or x['file']['id'] in args.file_id]
        assert selected, 'Run prepare first'
        results = [build_file(record) for record in selected]
        write(WORK / 'built.json', results)
        return
    files = catalog()
    additions = new_files(files, read(ROOT / 'versions.json'))
    if args.command == 'check':
        print(json.dumps({'upstream_total': len(files), 'new_files': [source_record(f) for f in additions]}, ensure_ascii=False, indent=2))
        return
    selected = [f for f in files if f['id'] in args.file_id] if args.file_id else additions
    if args.file_id:
        assert {f['id'] for f in selected} == set(args.file_id), 'File ID is not published in this project'
    memory = read(ROOT / 'translations/translation-memory.json')
    plan = {'files': [inventory(download(item), memory) for item in selected]}
    write(WORK / 'plan.json', plan)
    print(json.dumps({'prepared': len(selected), 'required_new_texts': sum(len(x['required_translations']) for x in plan['files']),
                      'plan': '.work/update/plan.json'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
