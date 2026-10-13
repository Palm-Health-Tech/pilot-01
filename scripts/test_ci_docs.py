from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from ci_docs import changed_paths, docs_only, scan
import subprocess


class DocsCITests(unittest.TestCase):
    def test_prose_paths(self):
        self.assertTrue(docs_only(["README.md"]))
        for paths in ([], ["SECURITY.md"], ["AGENTS.md"], ["README.md", "package-lock.json"], [".github/workflows/ci.yml"], ["app/page.tsx"]):
            with self.subTest(paths=paths):
                self.assertFalse(docs_only(paths))

    def test_complete_range_rename_and_deletion(self):
        with TemporaryDirectory(dir=Path.cwd()) as temp:
            root = Path(temp)
            def git(*args):
                return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=True).stdout.strip()
            git("init")
            git("config", "user.email", "ci@example.invalid")
            git("config", "user.name", "CI")
            (root / "source.ts").write_text("source", encoding="utf-8")
            git("add", ".")
            git("commit", "-m", "base")
            base = git("rev-parse", "HEAD")
            git("mv", "source.ts", "README.md")
            git("commit", "-am", "rename")
            self.assertIsNone(changed_paths(root, "push", base))
            self.assertIsNone(changed_paths(root, "push", "0" * 40))
            git("rm", "README.md")
            git("commit", "-m", "delete")
            self.assertIsNone(changed_paths(root, "push", git("rev-parse", "HEAD^")))
            (root / "README.md").write_text("# Readme\n", encoding="utf-8")
            git("add", ".")
            git("commit", "-m", "new prose")
            self.assertEqual(changed_paths(root, "push", git("rev-parse", "HEAD^")), ["README.md"])

    def test_content_scan(self):
        with TemporaryDirectory(dir=Path.cwd()) as temp:
            root = Path(temp)
            doc = root / "README.md"
            doc.write_text("okay\n", encoding="utf-8")
            scan(["README.md"], root)
            doc.write_text("Title\n=======\n", encoding="utf-8")
            scan(["README.md"], root)
            doc.write_text("<<<<<<< HEAD\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                scan(["README.md"], root)


if __name__ == "__main__":
    unittest.main()
