"""JSON read with positions kept, because a hook row needs `file:line`.

A hook definition is an entry inside a settings file. Its row carries the line
it sits on and the bytes it occupies, neither of which survives `json.loads`.
"""

import json
import unittest

from . import support  # noqa: F401

from orbit_context.jsonloc import JsonLocationError, parse

SAMPLE = '''{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {"type": "command", "command": "./run.sh"}
        ]
      }
    ]
  }
}
'''


class TestValuesMatchJsonLoads(unittest.TestCase):
    """Whatever the positions say, the values must be the standard library's."""

    def plain(self, node):
        if isinstance(node.value, dict):
            return {key: self.plain(child) for key, child in node.value.items()}
        if isinstance(node.value, list):
            return [self.plain(child) for child in node.value]
        return node.value

    def assertSame(self, text):
        self.assertEqual(self.plain(parse(text).root), json.loads(text))

    def test_the_sample(self):
        self.assertSame(SAMPLE)

    def test_scalars_and_escapes(self):
        self.assertSame('{"a": 1, "b": -2.5e3, "c": true, "d": null, "e": ""}')
        self.assertSame(r'{"quote": "a \" b", "slash": "a\\\\b", "unicode": "é"}')

    def test_empty_containers(self):
        self.assertSame('{"a": {}, "b": []}')

    def test_nesting_and_whitespace(self):
        self.assertSame('  {\n\t"a" :\r\n [ 1 , [ 2 ] ]\n}  ')

    def test_a_repeated_key_takes_the_last_value(self):
        self.assertSame('{"a": 1, "a": 2}')


class TestPositions(unittest.TestCase):
    def setUp(self):
        self.document = parse(SAMPLE)

    def command_entry(self):
        group = (
            self.document.root
            .get("hooks").get("PreToolUse")
            .elements()[0]
        )
        return group, group.get("hooks").elements()[0]

    def test_a_line_locator_points_at_the_entry(self):
        _, entry = self.command_entry()
        start, end = self.document.span_lines(entry)
        self.assertEqual((start, end), (7, 7))
        self.assertIn('"command"', SAMPLE.splitlines()[start - 1])

    def test_a_group_spans_several_lines(self):
        group, _ = self.command_entry()
        start, end = self.document.span_lines(group)
        self.assertEqual(start, 4)
        self.assertGreater(end, start)

    def test_size_is_the_bytes_of_the_entry_not_the_file(self):
        _, entry = self.command_entry()
        size = self.document.size_bytes(entry)
        self.assertEqual(size, len(self.document.slice(entry).encode("utf-8")))
        self.assertLess(size, len(SAMPLE.encode("utf-8")))

    def test_byte_size_counts_bytes_not_characters(self):
        document = parse('{"a": "éé"}')
        node = document.root.get("a")
        self.assertEqual(document.size_bytes(node), 6)     # 2 quotes + 2 x 2 bytes

    def test_line_numbers_are_one_based(self):
        self.assertEqual(self.document.line_of(0), 1)


class TestRefusals(unittest.TestCase):
    def test_unterminated_object(self):
        with self.assertRaises(JsonLocationError):
            parse('{"a": ')

    def test_unterminated_string(self):
        with self.assertRaises(JsonLocationError):
            parse('{"a": "b}')

    def test_trailing_text(self):
        with self.assertRaises(JsonLocationError):
            parse('{} {}')

    def test_a_comment_is_not_json(self):
        # JSONC is a real thing in editor settings; reading it is not guessed
        # at, it is reported.
        with self.assertRaises(JsonLocationError):
            parse('{\n  // a comment\n  "a": 1\n}')


if __name__ == "__main__":
    unittest.main()
