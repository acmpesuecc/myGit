import hashlib
from pathlib import Path
from pathlib import PurePath


class MyGitFuncs:

    GIT_DIR = ".mygit"

    def __init__(self):
        self.cwd = Path.cwd()

    def init(self):
        if Path(self.GIT_DIR).exists():
            raise Exception(f"repository already exists")
        self.git_dir = self.cwd / self.GIT_DIR
        Path(self.git_dir).mkdir()
        Path(PurePath(self.GIT_DIR, "objects").joinpath()).mkdir()

    def hash_object(self, data, type_="blob"):
        obj = type_.encode() + b"\x00" + data
        oid = hashlib.sha256(obj).hexdigest()
        return oid


    def get_object(self, oid, expected="blob"):
        path = Path(self.GIT_DIR) / "objects" / oid
        if not path.exists():
            raise Exception(f"object {oid} not found")
        with path.open(mode="rb") as f:
            obj = f.read()
        type_, _, content = obj.partition(b"\x00")
        type_ = type_.decode()
        if expected is not None and type_ != expected:
            raise ValueError(f"Expected{expected}, got {type_}")
        return content

    def update_ref(self, ref, oid):
        ref_path = Path(self.GIT_DIR) / ref
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        ref_path.write_text(oid)

    def get_ref(self, ref):
        ref_path = Path(self.GIT_DIR) / ref
        if ref_path.is_file():
            return ref_path.read_text().strip()
