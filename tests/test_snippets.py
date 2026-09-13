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


if __name__ == "__main__":
    unittest.main()
