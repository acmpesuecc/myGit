from pathlib import Path
from pathlib import PurePath
from .data import MyGitFuncs
import itertools
import operator
from collections import namedtuple
import string


class MyGitHigherFuncs:
    def __init__(self):
        self.ll_funcs = MyGitFuncs()

    def _iter_tree_entries(self, oid):
        if not oid:
            return
        tree = self.ll_funcs.get_object(oid, "tree")
        for entry in tree.decode().splitlines():
            type_, oid, name = entry.split(" ", 2)

            yield type_, oid, name

    def _empty_current_directory(self):
        for path in sorted(
            Path(".").glob("**/*"), key=lambda p: len(p.parts), reverse=True
        ):
            if path.is_file():
                if not self.is_ignored(path):
                    path.unlink()
            elif path.is_dir():
                if not self.is_ignored(path):
                    try:
                        path.rmdir()
                    except OSError:
                        pass

    def write_tree(self, directory=Path(".")):
        entries = []
        oid = None
        type_ = None
        for entry in Path(directory).iterdir():
            if self.is_ignored(entry):
                continue
            if entry.is_file() and not entry.is_symlink():
                type_ = "blob"
                with entry.open(mode="rb") as f:
                    oid = self.ll_funcs.hash_object(f.read())
            elif entry.is_dir() and not entry.is_symlink():
                type_ = "tree"
                oid = self.write_tree(entry)
            entries.append((entry.name, oid, type_))
        tree = "".join(
            f"{type_} {oid} {name}\n" for name, oid, type_ in sorted(entries)
        )
        return self.ll_funcs.hash_object(tree.encode(), "tree")

    def get_tree(self, oid, base_path=""):
        result = {}
        for type_, oid, name in self._iter_tree_entries(oid):
            path = base_path + name
            path = Path(path)
            if type_ == "blob":
                result[path] = oid
            elif type_ == "tree":
                result.update(self.get_tree(oid, f"{path}/"))
            else:
                raise Exception(f"Unknown tree entry {type_}")
        return result

    def read_tree(self, tree_oid):
        self._empty_current_directory()
        for entry in self.get_tree(tree_oid, base_path="./").items():
            path = entry[0]
            oid = entry[1]
            path = Path(path)
            (path.parent).mkdir(exist_ok=True)
            with path.open(mode="wb") as f:
                f.write(self.ll_funcs.get_object(oid))

    def commit(self, message):
        commit = f"tree {self.write_tree()}\n"
        HEAD = self.ll_funcs.get_ref("HEAD")
        if HEAD:
            commit += f"parent {HEAD}\n"
        commit += "\n"
        commit += f"{message}\n"
        oid = self.ll_funcs.hash_object(commit.encode(), "commit")
        self.ll_funcs.update_ref("HEAD", oid)
        return oid

    Commit = namedtuple("Commit", ["tree", "parent", "message"])

    def get_commit(self, oid):
        parent = None
        commit = self.ll_funcs.get_object(oid, "commit").decode()
        lines = iter(commit.splitlines())
        for line in itertools.takewhile(operator.truth, lines):
            key, value = line.split(" ", 1)
            if key == "tree":
                tree = value
            elif key == "parent":
                parent = value
            else:
                raise Exception(f"Unknown field {key}")
        message = "\n".join(lines)
        return self.Commit(tree=tree, parent=parent, message=message)

    def is_ignored(self, path):
        return ".mygit" in Path(path).parts

    def checkout(self, oid):
        commit = self.get_commit(oid)
        self.read_tree(commit.tree)
        self.ll_funcs.update_ref("HEAD", oid)

    def create_tag(self, name, oid,annotated=False,message=None):
        self.ll_funcs.update_ref(f"rel/tags/{name}", oid)
        #lightweight tag - creation 
        if annotated: 
            tag_email = "mygit <user@example.com>"
            tag_obj= { 
                f"object {oid}\n"
                f"type commit\n"
                f"tag {name}\n"
                f"tagger {tag_email}\n\n"
                f"{message}\n"
            } 
            tag_oid = self.ll_funcs.hash_object(tag_obj.encode(), "tag")
            self.ll_funcs.update_ref(f"refs/tags/{name}", tag_oid)
        else:
            self.ll_funcs.update_ref(f"refs/tags/{name}", oid)
    def list_tags(self):
        tags_dir = Path(self.ll_funcs.GIT_DIR) / "refs" / "tags"
        if not tags_dir.exists():
            print("No tags found.")
            return
        for tag_file in sorted(tags_dir.iterdir()):
            oid = tag_file.read_text().strip()
            print(f"{tag_file.name}\t{oid[:8]}")

    def delete_tag(self, name):
        tag_path = Path(self.ll_funcs.GIT_DIR) / "refs" / "tags" / name
        if not tag_path.exists():
            print(f"Tag '{name}' not found.")
            return
        tag_path.unlink()
        print(f"Deleted tag '{name}'.")

    def checkout_tag(self, name):
        oid = self.ll_funcs.get_ref(f"refs/tags/{name}")
        if not oid:
            raise Exception(f"Tag '{name}' not found")

        tag_obj_path = Path(self.ll_funcs.GIT_DIR) / "objects" / oid[:2] / oid[2:]
        if tag_obj_path.exists():
            content = self.ll_funcs.get_object(oid, expected="tag").decode()
            for line in content.splitlines():
                if line.startswith("object "):
                    oid = line.split()[1]
                    break
        self.checkout(oid)
        print(f"Checked out tag '{name}' → {oid[:8]}")


def get_oid(self, name):
    if name == "@":
        name = "HEAD"

    refs_to_try = [
        f"{name}",
        f"refs/{name}",
        f"refs/tags/{name}",
        f"refs/heads/{name}",
    ]
    for ref in refs_to_try:
        oid = self.ll_funcs.get_ref(ref)
        if oid:
            return oid

    is_hex = all(c in string.hexdigits for c in name)
    if len(name) == 40 and is_hex:
        return name

    raise Exception(f"Uknown name {name}")
