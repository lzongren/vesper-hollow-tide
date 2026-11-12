import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
import assets


class Response(io.BytesIO):
    url = 'https://dl.polyhaven.org/test.bin'


def record(path='mesh.bin', data=b'abc'):
    return {'path': path, 'url': Response.url, 'bytes': len(data),
            'md5': hashlib.md5(data).hexdigest()}


class AssetIntegrityTests(unittest.TestCase):
    def test_pinned_catalog_is_valid(self):
        assets.validate_lock(json.loads(assets.LOCKFILE.read_text()))

    def test_rejects_traversal_and_windows_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            for path in ['../escape', '/absolute', 'C:/absolute', 'x\\y', 'x/../../escape']:
                with self.subTest(path=path), self.assertRaises(ValueError):
                    assets.safe_path(Path(folder), path)

    def test_rejects_symlink_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'cache'
            root.mkdir()
            try:
                (root/'link').symlink_to(Path(folder), target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest('Creating symlinks is unavailable for this account')
            with self.assertRaises(ValueError):
                assets.safe_path(root, 'link/escape')

    def test_verified_download_is_reused_without_network(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            asset={'id':'test'}
            with patch.object(assets, 'urlopen', return_value=Response(b'abc')) as network:
                result=assets.fetch_file(root, asset, record(), False)
                self.assertEqual(result['sha256'], hashlib.sha256(b'abc').hexdigest())
                self.assertEqual(network.call_count, 1)
            with patch.object(assets, 'urlopen', side_effect=AssertionError('network used')):
                assets.fetch_file(root, asset, record(), True)

    def test_corrupt_download_does_not_replace_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            target=root/'test'/'mesh.bin'
            target.parent.mkdir()
            target.write_bytes(b'previous')
            with patch.object(assets, 'urlopen', return_value=Response(b'bad')):
                with self.assertRaisesRegex(ValueError, 'integrity'):
                    assets.fetch_file(root, {'id':'test'}, record(), False)
            self.assertEqual(target.read_bytes(), b'previous')
            self.assertEqual(list(target.parent.glob('.download-*')), [])

    def test_verify_only_rejects_missing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, 'Missing or corrupt'):
                assets.fetch_file(Path(folder), {'id':'test'}, record(), True)

    def test_rejects_unpinned_gltf_dependencies(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            directory=root/'test'
            directory.mkdir()
            (directory/'model.gltf').write_text(json.dumps({'asset':{'version':'2.0'}, 'buffers':[{'uri':'unreviewed.bin'}]}))
            with self.assertRaisesRegex(ValueError, 'Unpinned'):
                assets.validate_gltf(root, {'id':'test','entry':'model.gltf','files':[{'path':'model.gltf'}]})

    def test_rejects_remote_gltf_dependencies(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            directory=root/'test'
            directory.mkdir()
            (directory/'model.gltf').write_text(json.dumps({'asset':{'version':'2.0'}, 'images':[{'uri':'https://example.invalid/image.png'}]}))
            with self.assertRaisesRegex(ValueError, 'remote resource'):
                assets.validate_gltf(root, {'id':'test','entry':'model.gltf','files':[{'path':'model.gltf'}]})


if __name__ == '__main__':
    unittest.main()
