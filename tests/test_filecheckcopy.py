import io
import os
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import filecheckcopy


class FileCheckCopyTests(unittest.TestCase):
    def test_copy_only_changed_files(self):
        with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
            src = Path(src_dir)
            dst = Path(dst_dir)

            (src / "a.txt").write_text("same", encoding="utf-8")
            (src / "b.txt").write_text("changed", encoding="utf-8")
            (dst / "a.txt").write_text("same", encoding="utf-8")
            (dst / "b.txt").write_text("old", encoding="utf-8")

            filecheckcopy.copy_tree(str(src), str(dst), skip_same_mtime=False)

            self.assertEqual((dst / "a.txt").read_text(encoding="utf-8"), "same")
            self.assertEqual((dst / "b.txt").read_text(encoding="utf-8"), "changed")

    def test_skip_same_mtime_option_skips_existing_same_file(self):
        with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
            src = Path(src_dir)
            dst = Path(dst_dir)

            src_file = src / "a.txt"
            dst_file = dst / "a.txt"
            src_file.write_text("same", encoding="utf-8")
            dst_file.write_text("same", encoding="utf-8")

            old_mtime = 1_700_000_000.0
            os.utime(src_file, (old_mtime, old_mtime))
            os.utime(dst_file, (old_mtime, old_mtime))

            filecheckcopy.copy_tree(str(src), str(dst), skip_same_mtime=True)

            self.assertEqual(dst_file.read_text(encoding="utf-8"), "same")

    def test_dry_run_does_not_create_target_file(self):
        with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
            src = Path(src_dir)
            dst = Path(dst_dir)

            src_file = src / "new.txt"
            src_file.write_text("abc", encoding="utf-8")

            filecheckcopy.copy_tree(str(src), str(dst), dry_run=True)

            self.assertFalse((dst / "new.txt").exists())

    def test_dry_run_does_not_create_target_directory(self):
        with tempfile.TemporaryDirectory() as src_dir:
            src = Path(src_dir)
            target = src / "target" / "nested"
            source_file = src / "source.txt"
            source_file.write_text("abc", encoding="utf-8")

            filecheckcopy.copy_tree(str(src), str(target), dry_run=True)

            self.assertFalse(target.exists())

    def test_log_file_records_copy_activity(self):
        with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
            src = Path(src_dir)
            dst = Path(dst_dir)
            log_file = dst / "copy.log"

            src_file = src / "new.txt"
            src_file.write_text("abc", encoding="utf-8")

            copied, skipped = filecheckcopy.copy_tree(str(src), str(dst), log_file=str(log_file), parallel=1)

            self.assertEqual(copied, 1)
            self.assertEqual(skipped, 0)
            self.assertTrue(log_file.exists())
            self.assertIn("Copying:", log_file.read_text(encoding="utf-8"))

    def test_parallel_mode_executes_without_error(self):
        with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
            src = Path(src_dir)
            dst = Path(dst_dir)

            (src / "one.txt").write_text("one", encoding="utf-8")
            (src / "two.txt").write_text("two", encoding="utf-8")

            copied, skipped = filecheckcopy.copy_tree(str(src), str(dst), parallel=2)

            self.assertEqual(copied, 2)
            self.assertEqual(skipped, 0)
            self.assertTrue((dst / "one.txt").exists())
            self.assertTrue((dst / "two.txt").exists())

    def test_progress_shows_source_path_and_copy_or_skip(self):
        with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
            src = Path(src_dir)
            dst = Path(dst_dir)

            same_file = src / "same.txt"
            changed_file = src / "changed.txt"
            same_file.write_text("same", encoding="utf-8")
            changed_file.write_text("new", encoding="utf-8")
            (dst / "same.txt").write_text("same", encoding="utf-8")

            output = io.StringIO()
            with redirect_stdout(output):
                filecheckcopy.copy_tree(str(src), str(dst), skip_same_mtime=True, progress=True)

            text = output.getvalue()
            self.assertIn(str(same_file), text)
            self.assertIn(str(changed_file), text)
            self.assertIn("SKIP", text)
            self.assertIn("COPY", text)

    def test_log_file_contains_timestamp_and_elapsed_time(self):
        with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
            src = Path(src_dir)
            dst = Path(dst_dir)
            log_file = dst / "copy.log"

            (src / "one.txt").write_text("one", encoding="utf-8")

            copied, skipped = filecheckcopy.copy_tree(str(src), str(dst), log_file=str(log_file), parallel=1)

            self.assertEqual(copied, 1)
            self.assertEqual(skipped, 0)
            log_text = log_file.read_text(encoding="utf-8")
            self.assertIn("Operation started:", log_text)
            self.assertIn("Operation completed:", log_text)
            self.assertIn("Elapsed:", log_text)
            self.assertRegex(log_text, r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]")
            self.assertIn("Result:", log_text)


if __name__ == "__main__":
    unittest.main()
