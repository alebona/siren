import shutil
import tempfile
import unittest
from unittest import mock

from siren import snippets


class TestSnippets(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, True)
        patcher = mock.patch.object(snippets, "_snippets_dir", return_value=self.tmpdir)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_save_and_show_round_trip(self):
        snippets.save("my-snippet", "print('hello')\n")
        self.assertEqual(snippets.show("my-snippet"), "print('hello')\n")

    def test_show_missing_snippet_returns_none(self):
        self.assertIsNone(snippets.show("nope"))

    def test_list_snippets(self):
        snippets.save("b", "content")
        snippets.save("a", "content")
        self.assertEqual(snippets.list_snippets(), ["a", "b"])

    def test_remove_snippet(self):
        snippets.save("temp", "content")
        self.assertTrue(snippets.remove("temp"))
        self.assertIsNone(snippets.show("temp"))

    def test_remove_missing_snippet_returns_false(self):
        self.assertFalse(snippets.remove("nope"))

    def test_save_refuses_to_overwrite_without_force(self):
        snippets.save("dup", "first")
        with self.assertRaises(IOError):
            snippets.save("dup", "second")
        self.assertEqual(snippets.show("dup"), "first")

    def test_save_overwrites_with_force(self):
        snippets.save("dup", "first")
        snippets.save("dup", "second", force=True)
        self.assertEqual(snippets.show("dup"), "second")

    def test_save_records_tags_and_timestamps(self):
        snippets.save("tagged", "content", tags=["sql", "reporting"])
        meta = snippets.metadata("tagged")
        self.assertEqual(sorted(meta["tags"]), ["reporting", "sql"])
        self.assertIsNotNone(meta["created_at"])
        self.assertIsNotNone(meta["updated_at"])

    def test_metadata_for_untagged_snippet_has_empty_tags(self):
        snippets.save("plain", "content")
        meta = snippets.metadata("plain")
        self.assertEqual(meta["tags"], [])

    def test_list_snippets_filters_by_tag(self):
        snippets.save("a", "content", tags=["sql"])
        snippets.save("b", "content", tags=["python"])
        self.assertEqual(snippets.list_snippets(tag="sql"), ["a"])
        self.assertEqual(snippets.list_snippets(), ["a", "b"])

    def test_remove_clears_tags_from_index(self):
        snippets.save("temp", "content", tags=["x"])
        snippets.remove("temp")
        snippets.save("temp", "content")
        self.assertEqual(snippets.metadata("temp")["tags"], [])

    def test_search_matches_name(self):
        snippets.save("my-query", "SELECT 1")
        self.assertEqual(snippets.search("query"), ["my-query"])

    def test_search_matches_content(self):
        snippets.save("a", "SELECT * FROM users")
        snippets.save("b", "print('hi')")
        self.assertEqual(snippets.search("select"), ["a"])

    def test_search_matches_tag(self):
        snippets.save("a", "content", tags=["docker"])
        snippets.save("b", "content", tags=["sql"])
        self.assertEqual(snippets.search("docker"), ["a"])

    def test_search_no_match_returns_empty_list(self):
        snippets.save("a", "content")
        self.assertEqual(snippets.search("nope"), [])

    def test_copy_calls_clipboard_with_content(self):
        snippets.save("clip-me", "hello clipboard")
        with mock.patch.object(snippets, "copy_to_clipboard") as mock_copy:
            result = snippets.copy("clip-me")
        self.assertTrue(result)
        mock_copy.assert_called_once_with("hello clipboard")

    def test_copy_missing_snippet_returns_false(self):
        with mock.patch.object(snippets, "copy_to_clipboard") as mock_copy:
            result = snippets.copy("nope")
        self.assertFalse(result)
        mock_copy.assert_not_called()

    def test_copy_renders_variables_before_copying(self):
        snippets.save("templated", "SELECT * FROM {{table}}")
        with mock.patch.object(snippets, "copy_to_clipboard") as mock_copy:
            snippets.copy("templated", {"table": "users"})
        mock_copy.assert_called_once_with("SELECT * FROM users")

    def test_render_leaves_unfilled_placeholders_untouched(self):
        result = snippets.render("SELECT * FROM {{table}}", {"other": "x"})
        self.assertEqual(result, "SELECT * FROM {{table}}")

    def test_render_with_no_variables_returns_content_unchanged(self):
        self.assertEqual(snippets.render("plain text", None), "plain text")

    def test_rename_moves_content_and_metadata(self):
        snippets.save("old-name", "content", tags=["x"])
        self.assertTrue(snippets.rename("old-name", "new-name"))
        self.assertIsNone(snippets.show("old-name"))
        self.assertEqual(snippets.show("new-name"), "content")
        self.assertEqual(snippets.metadata("new-name")["tags"], ["x"])

    def test_rename_missing_snippet_returns_false(self):
        self.assertFalse(snippets.rename("nope", "whatever"))

    def test_rename_refuses_to_overwrite_without_force(self):
        snippets.save("a", "content-a")
        snippets.save("b", "content-b")
        with self.assertRaises(IOError):
            snippets.rename("a", "b")
        self.assertEqual(snippets.show("b"), "content-b")

    def test_all_tags_counts_usage(self):
        snippets.save("a", "content", tags=["sql", "reporting"])
        snippets.save("b", "content", tags=["sql"])
        self.assertEqual(snippets.all_tags(), [("reporting", 1), ("sql", 2)])

    def test_all_tags_empty_when_nothing_tagged(self):
        snippets.save("a", "content")
        self.assertEqual(snippets.all_tags(), [])

    def test_edit_opens_editor_and_updates_timestamp(self):
        snippets.save("editable", "content")
        before = snippets.metadata("editable")["updated_at"]
        with mock.patch.dict("os.environ", {"EDITOR": "myeditor"}), \
                mock.patch.object(snippets.subprocess, "call") as mock_call:
            result = snippets.edit("editable")
        self.assertTrue(result)
        mock_call.assert_called_once()
        called_cmd = mock_call.call_args[0][0]
        self.assertEqual(called_cmd[0], "myeditor")
        self.assertTrue(called_cmd[1].endswith("editable.txt"))
        self.assertIsNotNone(snippets.metadata("editable")["updated_at"])

    def test_edit_missing_snippet_returns_false(self):
        with mock.patch.dict("os.environ", {"EDITOR": "myeditor"}):
            self.assertFalse(snippets.edit("nope"))

    def test_edit_without_editor_env_raises(self):
        snippets.save("editable", "content")
        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(RuntimeError):
                snippets.edit("editable")

    def test_export_and_import_round_trip(self):
        snippets.save("a", "content-a", tags=["x"])
        snippets.save("b", "content-b")

        export_path = self.tmpdir + "/backup.json"
        count = snippets.export_snippets(export_path)
        self.assertEqual(count, 2)

        snippets.remove("a")
        snippets.remove("b")
        self.assertEqual(snippets.list_snippets(), [])

        result = snippets.import_snippets(export_path)
        self.assertEqual(result["imported"], 2)
        self.assertEqual(result["skipped"], [])
        self.assertEqual(snippets.show("a"), "content-a")
        self.assertEqual(snippets.metadata("a")["tags"], ["x"])
        self.assertEqual(snippets.show("b"), "content-b")

    def test_import_skips_existing_snippets_without_force(self):
        snippets.save("a", "original")
        export_path = self.tmpdir + "/backup.json"
        snippets.export_snippets(export_path)

        snippets.save("a", "changed-locally", force=True)
        result = snippets.import_snippets(export_path)

        self.assertEqual(result["imported"], 0)
        self.assertEqual(result["skipped"], ["a"])
        self.assertEqual(snippets.show("a"), "changed-locally")

    def test_import_overwrites_with_force(self):
        snippets.save("a", "original")
        export_path = self.tmpdir + "/backup.json"
        snippets.export_snippets(export_path)

        snippets.save("a", "changed-locally", force=True)
        result = snippets.import_snippets(export_path, force=True)

        self.assertEqual(result["imported"], 1)
        self.assertEqual(snippets.show("a"), "original")


if __name__ == "__main__":
    unittest.main()
