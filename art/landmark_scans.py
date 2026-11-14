"""Pack two pinned Poly Haven scans for the playable courts. Requires Pillow."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def pack(root, entry):
    folder = root / entry['id']
    for item in entry['files']:
        data = (folder / item['path']).read_bytes()
        if len(data) != item['bytes'] or hashlib.md5(data).hexdigest() != item['md5']:
            raise ValueError(f"Source changed: {item['path']}")
    model = json.loads((folder / entry['entry']).read_text())
    payload = bytearray((folder / model['buffers'][0]['uri']).read_bytes())
    for image in model['images']:
        with Image.open(folder / image.pop('uri')) as original:
            original.thumbnail((1536, 1536), Image.Resampling.LANCZOS)
            encoded = io.BytesIO()
            original.convert('RGB').save(encoded, 'JPEG', quality=89, subsampling=0)
        payload.extend(b'\0' * (-len(payload) % 4))
        image['bufferView'] = len(model['bufferViews'])
        model['bufferViews'].append(dict(buffer=0, byteOffset=len(payload), byteLength=encoded.tell()))
        payload.extend(encoded.getvalue())
    payload.extend(b'\0' * (-len(payload) % 4))
    model['buffers'] = [dict(byteLength=len(payload))]
    meta = json.dumps(model, separators=(',', ':')).encode()
    meta += b' ' * (-len(meta) % 4)
    header = struct.pack('<4sIIII', b'glTF',2,28+len(meta)+len(payload),len(meta),0x4e4f534a)
    target = ROOT / 'public' / 'models' / (entry['id'] + '.glb')
    target.write_bytes(header + meta + struct.pack('<II',len(payload),0x004e4942) + payload)
    print(target.name, target.stat().st_size)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_root', type=Path)
    entries = json.loads((ROOT / 'native/Art/assets.lock.json').read_text())['assets']
    source_root = parser.parse_args().source_root
    for entry in entries:
        if entry['id'] in {'rock_face_01','chinese_chandelier'}:
            pack(source_root,entry)
