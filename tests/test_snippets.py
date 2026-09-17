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


if __name__ == "__main__":
    unittest.main()
