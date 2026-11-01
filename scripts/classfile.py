import struct


def decode_mutf8(raw):
    return raw.replace(b'\xc0\x80', b'\0').decode('utf-8', errors='surrogatepass')


def encode_mutf8(text):
    # Class files store UTF-16 code units using Java modified UTF-8.
    units = text.encode('utf-16-be', errors='surrogatepass')
    out = bytearray()
    for i in range(0, len(units), 2):
        c = int.from_bytes(units[i:i + 2], 'big')
        if 1 <= c <= 0x7f:
            out.append(c)
        elif c <= 0x7ff:
            out.extend((0xc0 | (c >> 6), 0x80 | (c & 63)))
        else:
            out.extend((0xe0 | (c >> 12), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63)))
    return bytes(out)


class ClassFile:
    def __init__(self, data):
        assert data[:4] == b'\xca\xfe\xba\xbe'
        self.header = data[:8]
        count = struct.unpack_from('>H', data, 8)[0]
        self.cp = [None] * count
        pos = 10
        i = 1
        while i < count:
            tag = data[pos]
            pos += 1
            start = pos
            if tag == 1:
                size = struct.unpack_from('>H', data, pos)[0]
                pos += 2 + size
            elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
                pos += 4
            elif tag in (5, 6):
                pos += 8
            elif tag in (7, 8, 16, 19, 20):
                pos += 2
            elif tag == 15:
                pos += 3
            else:
                raise ValueError(tag)
            self.cp[i] = (tag, data[start:pos])
            i += 2 if tag in (5, 6) else 1
        self.body = data[pos:]
        self.attributes = self._attributes()
        self.bootstraps = []
        for name, start, end, payload in self.attributes:
            if name == 'BootstrapMethods':
                p = 2
                for _ in range(int.from_bytes(payload[:2], 'big')):
                    ref, n = struct.unpack_from('>HH', payload, p)
                    p += 4
                    args = list(struct.unpack_from('>' + 'H' * n, payload, p))
                    p += 2 * n
                    self.bootstraps.append((ref, args))
                assert p == len(payload)

    def utf(self, idx):
        tag, payload = self.cp[idx]
        assert tag == 1
        return decode_mutf8(payload[2:])

    def pair(self, idx):
        return struct.unpack('>HH', self.cp[idx][1])

    def ref(self, idx):
        return int.from_bytes(self.cp[idx][1], 'big')

    def string(self, idx):
        assert self.cp[idx][0] == 8
        return self.utf(self.ref(idx))

    def class_name(self):
        return self.utf(self.ref(int.from_bytes(self.body[2:4], 'big')))

    def method_ref(self, handle):
        kind = self.cp[handle][1][0]
        ref = int.from_bytes(self.cp[handle][1][1:], 'big')
        owner, nat = self.pair(ref)
        name, desc = self.pair(nat)
        return self.utf(self.ref(owner)), self.utf(name), self.utf(desc)

    def _attributes(self):
        b = self.body
        pos = 6
        n = int.from_bytes(b[pos:pos + 2], 'big')
        pos += 2 + 2 * n
        for _ in range(2):
            count = int.from_bytes(b[pos:pos + 2], 'big')
            pos += 2
            for _ in range(count):
                pos += 6
                attrs = int.from_bytes(b[pos:pos + 2], 'big')
                pos += 2
                for _ in range(attrs):
                    length = int.from_bytes(b[pos + 2:pos + 6], 'big')
                    pos += 6 + length
        count = int.from_bytes(b[pos:pos + 2], 'big')
        pos += 2
        attrs = []
        for _ in range(count):
            start = pos
            name, length = struct.unpack_from('>HI', b, pos)
            pos += 6
            payload = b[pos:pos + length]
            pos += length
            attrs.append((self.utf(name), start, pos, payload))
        assert pos == len(b)
        return attrs

    def add(self, tag, payload):
        value = (tag, payload)
        if value in self.cp:
            return self.cp.index(value)
        self.cp.append(value)
        return len(self.cp) - 1

    def add_utf(self, value):
        raw = encode_mutf8(value)
        assert len(raw) < 65536
        return self.add(1, struct.pack('>H', len(raw)) + raw)

    def add_string(self, value):
        return self.add(8, struct.pack('>H', self.add_utf(value)))

    def concat_handle(self):
        owner = self.add(7, struct.pack('>H', self.add_utf('java/lang/invoke/StringConcatFactory')))
        name = self.add_utf('makeConcatWithConstants')
        desc = self.add_utf('(Ljava/lang/invoke/MethodHandles$Lookup;Ljava/lang/String;Ljava/lang/invoke/MethodType;Ljava/lang/String;[Ljava/lang/Object;)Ljava/lang/invoke/CallSite;')
        nat = self.add(12, struct.pack('>HH', name, desc))
        method = self.add(10, struct.pack('>HH', owner, nat))
        return self.add(15, b'\x06' + struct.pack('>H', method))

    def build(self, bootstraps_changed=False):
        body = self.body
        if bootstraps_changed:
            payload = struct.pack('>H', len(self.bootstraps))
            for ref, args in self.bootstraps:
                payload += struct.pack('>HH', ref, len(args))
                payload += struct.pack('>' + 'H' * len(args), *args)
            attr = next(a for a in self.attributes if a[0] == 'BootstrapMethods')
            _, start, end, _ = attr
            body = body[:start + 2] + struct.pack('>I', len(payload)) + payload + body[end:]
        return self.header + struct.pack('>H', len(self.cp)) + b''.join(bytes([t]) + p for entry in self.cp[1:] if entry for t, p in [entry]) + body


MASK = (1 << 64) - 1


def mix(value):
    value = (value - 7046029254386353131) & MASK
    value = ((value ^ (value >> 30)) * -4658895280553007687) & MASK
    value = ((value ^ (value >> 27)) * -7723592293110705685) & MASK
    return value ^ (value >> 31)


def signed32(value):
    return value - (1 << 32) if value & (1 << 31) else value


def class_hash(name):
    value = 2166136261
    for c in name.rsplit('/', 1)[-1]:
        value = ((value ^ ord(c)) * 16777619) & 0xffffffff
    return signed32(value)

