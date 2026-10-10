import unittest

from textstats import average_word_length, word_count


class TextStatsTest(unittest.TestCase):
    def test_word_count_handles_extra_spaces(self):
        self.assertEqual(word_count("  hello   world  "), 2)

    def test_word_count_empty(self):
        self.assertEqual(word_count(""), 0)

    def test_average_ignores_punctuation(self):
        self.assertAlmostEqual(average_word_length("Hi, you!"), 2.5)

    def test_average_empty(self):
        self.assertEqual(average_word_length(""), 0)


if __name__ == "__main__":
    unittest.main()
