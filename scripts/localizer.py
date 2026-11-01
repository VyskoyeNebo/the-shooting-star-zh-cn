import collections
import copy
import hashlib
import io
import json
import pathlib
import re
import struct
import subprocess
import sys
import tomllib
import zipfile

from archive_tools import ClassFile, discover_helpers, encrypted_strings

BASE = pathlib.Path.cwd() / '.work' / 'auto'
ROOT = pathlib.Path(__file__).resolve().parent.parent
DICTIONARY = {}
RIMULIB_ZH = {}


def configure(dictionary, workdir, rimulib_zh):
    global DICTIONARY, BASE, RIMULIB_ZH
    DICTIONARY = dict(dictionary)
    BASE = pathlib.Path(workdir).resolve()
    BASE.mkdir(parents=True, exist_ok=True)
    RIMULIB_ZH = dict(rimulib_zh)
    java_source = pathlib.Path(__file__).resolve().parent / 'VerifyAllTextLinkage.java'
    java_class = BASE / 'VerifyAllTextLinkage.class'
    if not java_class.exists() or java_class.stat().st_mtime < java_source.stat().st_mtime:
        subprocess.run(['javac', '-encoding', 'UTF-8', '-d', str(BASE), str(java_source)], check=True, capture_output=True)


def signature(text):
    tokens = re.findall(r'%(?:\d+\$)?[-#+ 0,(]*\d*(?:\.\d+)?[a-zA-Z%]', text)
    return (sorted(t for t in tokens if re.match(r'%\d+\$', t)),
            [t for t in tokens if not re.match(r'%\d+\$', t)], text.count('\x01'), text.count('\x02'))


def localize_class(original, cf, helpers):
    plain = [(i, cf.string(i)) for i, e in enumerate(cf.cp) if e and e[0] == 8]
    encrypted = encrypted_strings(cf, helpers)
    all_text = [t for _, t in plain] + [t for _, _, t in encrypted]
    if any('needs more letters or strokes than a title holds' in s for s in all_text):
        return original, [], 0, True
    enum = bool(int.from_bytes(cf.body[:2], 'big') & 0x4000)
    changes = []

    def translated(old):
        if old not in DICTIONARY:
            return None
        if enum and re.fullmatch(r'[A-Z][A-Z0-9_]*', old):
            return None
        new = DICTIONARY[old]
        assert signature(old) == signature(new), (old, new)
        if old == new:
            return None
        return new

    for idx, old in plain:
        new = translated(old)
        if new is not None:
            cf.cp[idx] = (8, struct.pack('>H', cf.add_utf(new)))
            changes.append([old, new])
    bsm_changed = set()
    for idx, bsm, old in encrypted:
        new = translated(old)
        if new is None:
            continue
        assert '\x01' not in new and '\x02' not in new
        for entry in cf.cp:
            if entry and entry[0] == 18:
                other_bsm, nat = struct.unpack('>HH', entry[1])
                if other_bsm == bsm:
                    _, desc = cf.pair(nat)
                    assert cf.utf(desc) == '()Ljava/lang/String;'
        cf.bootstraps[bsm] = (cf.concat_handle(), [cf.add_string(new)])
        bsm_changed.add(bsm)
        changes.append([old, new])
    if not changes:
        return original, [], 0, False
    result = cf.build(bootstraps_changed=bool(bsm_changed))
    old_cf = ClassFile(original)
    new_cf = ClassFile(result)
    if bsm_changed:
        a = next(a for a in old_cf.attributes if a[0] == 'BootstrapMethods')
        b = next(a for a in new_cf.attributes if a[0] == 'BootstrapMethods')
        assert old_cf.body[:a[1]] == new_cf.body[:b[1]]
        assert old_cf.body[a[2]:] == new_cf.body[b[2]:]
        for i, item in enumerate(old_cf.bootstraps):
            if i not in bsm_changed:
                assert item == new_cf.bootstraps[i]
            else:
                ref, args = new_cf.bootstraps[i]
                assert new_cf.method_ref(ref)[:2] == ('java/lang/invoke/StringConcatFactory', 'makeConcatWithConstants')
                assert len(args) == 1 and new_cf.string(args[0]) in DICTIONARY.values()
    else:
        assert old_cf.body == new_cf.body
    for i, entry in enumerate(old_cf.cp):
        if entry is not None and entry[0] != 8:
            assert entry == new_cf.cp[i], (cf.class_name(), i)
    return result, changes, len(bsm_changed), False


def metadata(raw, name):
    if name == 'fabric.mod.json':
        old = json.loads(raw)
        new = copy.deepcopy(old)
        if old.get('name') in DICTIONARY:
            new['name'] = DICTIONARY[old['name']]
        if new != old:
            return (json.dumps(new, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if name in {'META-INF/mods.toml', 'META-INF/neoforge.mods.toml'}:
        old = tomllib.loads(raw.decode('utf-8'))
        text = raw.decode('utf-8').replace('displayName = "The Shooting Star (Demo)"', 'displayName = "流星（试玩版）"')
        new = tomllib.loads(text)
        a, b = copy.deepcopy(old), copy.deepcopy(new)
        for value in a.get('mods', []):
            value.pop('displayName', None)
        for value in b.get('mods', []):
            value.pop('displayName', None)
        assert a == b
        return text.encode('utf-8')
    return raw


def archive(raw, file_id, node_path, nodes, changes_all):
    stream = io.BytesIO()
    classes_modified = []
    translated_languages = {}
    inherited_lib = False
    text_changes = 0
    styled_titles = 0
    constants = 0
    with zipfile.ZipFile(io.BytesIO(raw)) as source, zipfile.ZipFile(stream, 'w') as target:
        assert source.testzip() is None
        assert not any(re.search(r'META-INF/[^/]+\.(?:SF|RSA|DSA|EC)$', n, re.I) for n in source.namelist()), 'Signed JAR requires separate handling'
        target.comment = source.comment
        classes = {n: ClassFile(source.read(n)) for n in source.namelist() if n.endswith('.class') and '/shootingstardemo/' in n}
        helpers = discover_helpers(classes)
        original_metadata = {}
        for name in ['fabric.mod.json', 'META-INF/mods.toml', 'META-INF/neoforge.mods.toml']:
            if name in source.namelist():
                data = source.read(name)
                original_metadata[name] = json.loads(data) if name.endswith('.json') else tomllib.loads(data.decode('utf-8'))
                inherited_lib |= b'rimulib' in data
        new_files = {}
        for name in source.namelist():
            if '/lang/' in name and name.endswith('/en_us.json'):
                english = json.loads(source.read(name))
                chinese = {}
                for key, value in english.items():
                    assert value in DICTIONARY, (file_id, node_path, key, value)
                    chinese[key] = DICTIONARY[value]
                    assert signature(value) == signature(chinese[key]), key
                zh_name = name.removesuffix('en_us.json') + 'zh_cn.json'
                new_files[zh_name] = (json.dumps(chinese, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
                translated_languages[zh_name] = len(chinese)
                lang_path = BASE / 'translations' / str(file_id) / (node_path.replace('::', '/').lstrip('/').removesuffix('.jar') if node_path else 'root') / zh_name
                assert lang_path.resolve().is_relative_to((BASE / 'translations').resolve()), 'Unsafe archive resource path'
                lang_path.parent.mkdir(parents=True, exist_ok=True)
                lang_path.write_bytes(new_files[zh_name])
        if translated_languages and inherited_lib:
            new_files['assets/rimulib/lang/zh_cn.json'] = (json.dumps(RIMULIB_ZH, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
            translated_languages['assets/rimulib/lang/zh_cn.json'] = len(RIMULIB_ZH)
        changed_names = set()
        for info in source.infolist():
            name = info.filename
            old = source.read(name)
            new = old
            if name.endswith('.jar'):
                new = archive(old, file_id, node_path + '::' + name, nodes, changes_all)
            elif name in classes:
                new, changes, count, styled = localize_class(old, classes[name], helpers)
                styled_titles += int(styled)
                if changes:
                    classes_modified.append(name)
                    text_changes += len(changes)
                    constants += count
                    changes_all.append({'node': node_path, 'class': name, 'translations': changes})
            elif name in new_files:
                new = new_files.pop(name)
            else:
                new = metadata(old, name)
            if new != old:
                changed_names.add(name)
            target.writestr(copy.copy(info), new)
        for name, data in new_files.items():
            target.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)
    result = stream.getvalue()
    with zipfile.ZipFile(io.BytesIO(raw)) as a, zipfile.ZipFile(io.BytesIO(result)) as b:
        assert b.testzip() is None
        assert len(b.namelist()) == len(set(b.namelist()))
        assert set(b.namelist()) == set(a.namelist()) | set(translated_languages)
        for name in a.namelist():
            if name not in changed_names:
                assert a.read(name) == b.read(name)
            if name.endswith(('.fsh', '.vsh', '.glsl', '.png', '.jpg', '.ogg', '.bin', '.ttf')):
                assert a.read(name) == b.read(name), name
            if name.endswith('.json'):
                json.loads(b.read(name))
        for name, old in original_metadata.items():
            new = json.loads(b.read(name)) if name.endswith('.json') else tomllib.loads(b.read(name).decode('utf-8'))
            if name == 'fabric.mod.json':
                for key in old:
                    if key != 'name':
                        assert old[key] == new[key], (file_id, key)
    jvm_sites = 0
    if classes_modified:
        current = BASE / 'verify-current.jar'
        current.write_bytes(result)
        command = ['javap', '-p', '-c', '-classpath', str(current)] + [s.removesuffix('.class').replace('/', '.') for s in classes_modified]
        probe = subprocess.run(command, capture_output=True)
        assert probe.returncode == 0, (file_id, node_path, probe.stderr.decode(errors='replace'))
        probe = subprocess.run(['java', '-cp', str(BASE), 'VerifyAllTextLinkage', str(current)], capture_output=True)
        assert probe.returncode == 0, (file_id, node_path, probe.stderr.decode(errors='replace'))
        jvm_sites = int(re.search(rb'evaluated (\d+)', probe.stdout).group(1))
    nodes.append({'path': node_path, 'languages': translated_languages, 'changed_classes': len(classes_modified),
                  'hardcoded_replacements': text_changes, 'constant_sites': constants, 'jvm_tested_sites': jvm_sites,
                  'preserved_vector_title_classes': styled_titles, 'original_metadata': original_metadata})
    return result

