"""Reproduce the Docker layout: /gallery/elp_lib.py has only two parents.

The live Windows container bind-mounts apps/gallery at /gallery. That path
raises IndexError on Path.parents[2], which crashed Studio Console on import.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import unittest
from pathlib import Path

GALLERY_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(GALLERY_DIR))
from elp_lib import resolve_repo_root  # noqa: E402


def _shallow_elp_lib_path() -> Path:
    """A file with the same parent depth as /gallery/elp_lib.py inside Docker."""
    for dest in (Path("/tmp/elp_lib.py"), Path("/gallery/elp_lib.py")):
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.resolve().parents[2]
        except IndexError:
            return dest
        except OSError:
            continue
    raise unittest.SkipTest("Cannot write a two-parent path like /gallery/elp_lib.py")


class ContainerPathTests(unittest.TestCase):
    def test_docker_gallery_path_has_no_parents_2(self):
        path = Path("/gallery/elp_lib.py")
        self.assertEqual(list(path.parents), [Path("/gallery"), Path("/")])
        with self.assertRaises(IndexError):
            path.parents[2]

    def test_resolve_repo_root_does_not_index_parents_2(self):
        root = resolve_repo_root(Path("/gallery/elp_lib.py"))
        self.assertIsInstance(root, Path)
        self.assertEqual(resolve_repo_root(GALLERY_DIR / "elp_lib.py"), REPO_ROOT)

    def test_import_elp_lib_from_shallow_container_path(self):
        dest = _shallow_elp_lib_path()
        created_gallery_dir = dest.parent == Path("/gallery") and not (Path("/gallery") / "elp_lib.py").exists()
        prev = {
            key: os.environ.get(key)
            for key in ("ELP_REPO_ROOT", "ELP_BRANDS_DIR", "ELP_STYLES_DIR", "ELP_GALLERY_DIR")
        }
        module_name = "elp_lib_container_shallow"
        try:
            shutil.copyfile(GALLERY_DIR / "elp_lib.py", dest)
            self.assertLess(len(dest.resolve().parents), 3)
            with self.assertRaises(IndexError):
                dest.resolve().parents[2]
            os.environ.pop("ELP_REPO_ROOT", None)
            os.environ["ELP_BRANDS_DIR"] = str(REPO_ROOT / "brands")
            os.environ["ELP_STYLES_DIR"] = str(REPO_ROOT / "styles")
            spec = importlib.util.spec_from_file_location(module_name, dest)
            self.assertIsNotNone(spec)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = mod
            spec.loader.exec_module(mod)
            self.assertEqual(mod.BRANDS_DIR, REPO_ROOT / "brands")
            self.assertEqual([b["id"] for b in mod.load_brands()], ["mini-momentz", "katha-films", "tattva-weddings"])
        finally:
            sys.modules.pop(module_name, None)
            if dest.exists() and dest != GALLERY_DIR / "elp_lib.py":
                try:
                    dest.unlink()
                except OSError:
                    pass
            if created_gallery_dir:
                shutil.rmtree("/gallery", ignore_errors=True)
            for key, value in prev.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_import_without_env_from_temp_shallow_copy_does_not_crash(self):
        dest = Path("/tmp/elp_lib.py")
        prev_root = os.environ.pop("ELP_REPO_ROOT", None)
        prev_brands = os.environ.pop("ELP_BRANDS_DIR", None)
        prev_styles = os.environ.pop("ELP_STYLES_DIR", None)
        module_name = "elp_lib_container_noenv"
        try:
            shutil.copyfile(GALLERY_DIR / "elp_lib.py", dest)
            spec = importlib.util.spec_from_file_location(module_name, dest)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = mod
            spec.loader.exec_module(mod)
            self.assertTrue(mod.GALLERY_DIR.is_dir() or str(mod.GALLERY_DIR) == "/tmp")
            self.assertEqual(mod.GALLERY_DIR, dest.parent)
        finally:
            sys.modules.pop(module_name, None)
            if dest.exists():
                dest.unlink()
            if prev_root is not None:
                os.environ["ELP_REPO_ROOT"] = prev_root
            if prev_brands is not None:
                os.environ["ELP_BRANDS_DIR"] = prev_brands
            if prev_styles is not None:
                os.environ["ELP_STYLES_DIR"] = prev_styles


class RepoLayoutStillWorksTests(unittest.TestCase):
    def test_host_import_still_finds_brands(self):
        from elp_lib import BRANDS_DIR, REPO_ROOT as live_root, load_brands

        self.assertEqual(live_root, REPO_ROOT)
        self.assertTrue(BRANDS_DIR.is_dir())
        self.assertEqual(len(load_brands()), 3)


if __name__ == "__main__":
    unittest.main()
