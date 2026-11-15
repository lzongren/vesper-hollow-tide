"""Prepare Epic's sample DNA and the signed-off art bake in project-local Saved.

Invoked with Unreal's bundled Windows Python. Pin all binaries and assets by
digest. The converter runs in an isolated embedded interpreter matching the DNA ABI.
"""

import hashlib
import msvcrt
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

REVISION = "8297ff1bd6f1692a6e221aa8395a66486e5a53c9"
EPIC = (
    "https://raw.githubusercontent.com/EpicGames/MetaHuman-DNA-Calibration/"
    + REVISION
    + "/"
)
RUNTIME = {
    "python.zip": (
        "https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip",
        "608619f8619075629c9c69f361352a0da6ed7e62f83a0e19c63e0ea32eb7629d",
    ),
    "numpy.whl": (
        "https://files.pythonhosted.org/packages/19/77/538f202862b9183f54108557bfda67e17603fc560c384559e769321c9d92/numpy-1.26.4-cp310-cp310-win_amd64.whl",
        "b97fe8060236edf3662adfc2c633f56a08ae30560c56310562cb4f95500022d5",
    ),
    "pillow.whl": (
        "https://files.pythonhosted.org/packages/a9/d3/60c781c83a785d6afbd6a326ed4d759d141de43aa7365725cbcd65ce5e54/pillow-11.3.0-cp310-cp310-win_amd64.whl",
        "19d2ff547c75b8e3ff46f4d9ef969a06c30ab2d4263a9e287733aa8b2429ce8f",
    ),
}
SDK = {
    "dna.py": "3e1df5c41b3cfeb37a324adbee4c72392e2721dc662656a73e6e0d751b062030",
    "_py3dna.pyd": "dc494978ff8a6a43f07aef7605ff14a5e95f21a1cb0657bbc34cafd72cdcb892",
    "dnacalib.dll": "b9c55f96a9045b5df88ffec800d43fe4226c294fae9b2dda112742135059a112",
}
MAPS = {
    "eyelashes_color_map": "06e24bd8b1efa0a7266e3a9223f5c29179542b471db235737f7074916722bdc4",
    "eyes_color_map": "9f7e00bacfa2bcccc343127054c3e2a942ffb3074d627e77ef98afaab7ed12d6",
    "head_color_map": "d4d12d38b3fd1f4a833a0e6a75f0f4e8d226928b0c3dfcc1484a07f08d045ec3",
    "head_micro_normal_map": "a71d7e8b75327115bd9fe101738d930a0ece42a0f81d6bc4c4265c5b452802f2",
    "head_normal_map": "0d2ae899799ba278a68d309deb11650ab5eeee292cd20b694b76055c66d75f44",
    "head_roughness_map": "5bd757e898cbb70c93ba06baa8782f94850ab85756f433370b93a6f5bb77224c",
    "teeth_color_map": "5f069b9779cb9a8d5fe3f0ea7148a821cb90054b6c5a004f7707eb4cd1ac4bca",
}


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def fetch(path, url, sha):
    if path.is_file() and digest(path) == sha:
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as out:
        tmp = Path(out.name)
    try:
        with urllib.request.urlopen(url, timeout=120) as src, tmp.open("wb") as out:
            shutil.copyfileobj(src, out)
        if digest(tmp) != sha:
            raise ValueError("Incorrect digest for " + path.name)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def prepare(project):
    art = project / "Art/Wayfarer"
    cache = project / "Saved/DigitalHuman"
    cache.mkdir(exist_ok=True, parents=True)
    with (cache / "prepare.lock").open("a+b") as lock:
        lock.seek(0)
        lock.write(b"0")
        lock.flush()
        for _ in range(240):
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                time.sleep(1)
        else:
            raise TimeoutError("Another face bake is running")
        script = project / "Scripts/bake_digital_head.py"
        stamp = cache / "bake.sha256"
        signature = " ".join(
            digest(f)
            for f in (
                script,
                Path(__file__),
                art / "portrait-open.jpg",
                art / "sculpt-profile.jpg",
                art / "digital-sculpt.json",
                art / "digital-pigment.json",
            )
        )
        outputs = (
            "face.json",
            "HaitangDiffuse.jpg",
            "HaitangEye.jpg",
            "HaitangTeeth.jpg",
            "HaitangLashes.png",
            "HaitangNormal.png",
            "HaitangRough.png",
        )
        if (
            stamp.exists()
            and stamp.read_text() == signature
            and all((cache / f).is_file() for f in outputs)
        ):
            return
        runtime = cache / "py310"
        runtime.mkdir(exist_ok=True)
        for name, (url, sha) in RUNTIME.items():
            path = cache / name
            fetch(path, url, sha)
            with zipfile.ZipFile(path) as bundle:
                bundle.extractall(runtime)
        for name, sha in SDK.items():
            fetch(runtime / name, EPIC + "lib/Maya2024/windows/" + name, sha)
        fetch(
            cache / "Ada.dna",
            EPIC + "data/dna_files/Ada.dna",
            "e764cfab938283231bcb3e5af1c7bcbec5154bab4804aafa1b5b7dc6e400ca5e",
        )
        for name, sha in MAPS.items():
            fetch(cache / (name + ".tga"), EPIC + "data/maps/" + name + ".tga", sha)
        subprocess.run(
            [str(runtime / "python.exe"), str(script), str(cache), str(art)],
            check=True,
            cwd=cache,
        )
        stamp.write_text(signature)


if __name__ == "__main__":
    prepare(Path(sys.argv[1]).resolve())
