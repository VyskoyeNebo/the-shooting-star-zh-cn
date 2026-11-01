import io
import pathlib
import struct
import sys
import zipfile

from classfile import ClassFile, MASK, class_hash, mix


def members(cf):
    b = cf.body
    p = 6
    interfaces = int.from_bytes(b[p:p + 2], 'big')
    p += 2 + interfaces * 2
    result = []
    for group in range(2):
        n = int.from_bytes(b[p:p + 2], 'big')
        p += 2
        values = []
        for _ in range(n):
            flags, name, desc, count = struct.unpack_from('>HHHH', b, p)
            p += 8
            attrs = {}
            for _ in range(count):
                key, size = struct.unpack_from('>HI', b, p)
                p += 6
                attrs[cf.utf(key)] = b[p:p + size]
                p += size
            values.append((flags, cf.utf(name), cf.utf(desc), attrs))
        result.append(values)
    return result


def method_code(attributes):
    data = attributes.get('Code')
    if data is None:
        return b''
    length = int.from_bytes(data[4:8], 'big')
    return data[8:8 + length]


def discover_helpers(classes):
    helpers = {}
    for cf in classes.values():
        utf8 = {cf.utf(i) for i, e in enumerate(cf.cp) if e and e[0] == 1}
        if not {'java/lang/invoke/ConstantCallSite', 'D', 'u', 'h', 'm'}.issubset(utf8):
            continue
        fields, methods = members(cf)
        u = next((method_code(a) for _, n, d, a in methods if n == 'u' and d == '(IIII)Ljava/lang/String;'), None)
        if u is None:
            continue
        assert u[0] == 0x14, cf.class_name()
        salt_index = int.from_bytes(u[1:3], 'big')
        assert cf.cp[salt_index][0] == 5
        salt = struct.unpack('>q', cf.cp[salt_index][1])[0]
        constant_methods = set()
        for _, name, desc, attrs in methods:
            if desc == '(Ljava/lang/invoke/MethodHandles$Lookup;Ljava/lang/String;Ljava/lang/invoke/MethodType;III)Ljava/lang/invoke/CallSite;':
                code = method_code(attrs)
                if code[:1] == b'\x2c':
                    constant_methods.add(name)
        assert len(constant_methods) == 1, cf.class_name()
        clinit = next(method_code(a) for _, n, _, a in methods if n == '<clinit>')
        chunks = []
        pos = 0
        while pos < len(clinit):
            op = clinit[pos]
            pos += 1
            if op == 0x4b:  # astore_0: initial chunk array is complete
                break
            if op == 0x12:
                ref = clinit[pos]
                pos += 1
                if cf.cp[ref][0] == 8:
                    chunks.append(cf.string(ref))
            elif op in (0x13, 0x14):
                ref = int.from_bytes(clinit[pos:pos + 2], 'big')
                pos += 2
                if cf.cp[ref][0] == 8:
                    chunks.append(cf.string(ref))
            elif op in (0x10, 0xbc):
                pos += 1
            elif op in (0x11, 0xbd):
                pos += 2
            else:
                assert op in {0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x59, 0x53}, (cf.class_name(), hex(op), pos)
        assert chunks
        blob = ''.join(chunks).encode('latin-1')
        helpers[cf.class_name()] = (blob, salt, constant_methods)
    return helpers


def encrypted_strings(cf, helpers):
    result = []
    for idx, entry in enumerate(cf.cp):
        if not entry or entry[0] != 18:
            continue
        bsm, nat = cf.pair(idx)
        _, desc = cf.pair(nat)
        if cf.utf(desc) != '()Ljava/lang/String;':
            continue
        handle, args = cf.bootstraps[bsm]
        owner, name, _ = cf.method_ref(handle)
        if owner not in helpers:
            continue
        data, salt, methods = helpers[owner]
        if name not in methods:
            continue
        assert len(args) == 3 and all(cf.cp[a][0] == 3 for a in args)
        a, b, c = [struct.unpack('>i', cf.cp[v][1])[0] for v in args]
        key = mix(salt ^ ((class_hash(cf.class_name()) * 5871781006564002453) & MASK) ^ ((c * -7046029254386353131) & MASK))
        start = (a ^ (key & 0xffffffff)) & 0xffffffff
        length = (b ^ (key >> 32)) & 0xffffffff
        assert start + length <= len(data), (cf.class_name(), idx, start, length, len(data))
        decoded = bytearray()
        state = key
        for n in range(length):
            if n & 7 == 0:
                state = mix(state ^ n)
            decoded.append(data[start + n] ^ ((state >> ((n & 7) * 8)) & 255))
        result.append((idx, bsm, decoded.decode('utf-8')))
    return result


def archive_nodes(raw, path=''):
    with zipfile.ZipFile(io.BytesIO(raw)) as jar:
        yield path, jar
        for name in jar.namelist():
            if name.endswith('.jar'):
                yield from archive_nodes(jar.read(name), path + '::' + name)


def readable(text):
    if not text or len(text) > 4000 or '\ufffd' in text:
        return False
    if any(ord(c) < 32 and c not in '\x01\x02\n\r\t' for c in text):
        return False
    if any(0x7f <= ord(c) < 0xa0 for c in text):
        return False
    if text.startswith(('V|', 'S|', 'F|', '#version', '#include', '(')):
        return False
    return True
