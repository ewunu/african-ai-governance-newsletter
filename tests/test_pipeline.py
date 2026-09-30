import os
import sys
import unittest
from unittest.mock import patch, Mock
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import classifier
import scraper
import sheets_handler

class PipelineTests(unittest.TestCase):
    def test_retired_model_is_not_default(self):
        self.assertNotIn('2.0', classifier.MODEL_NAME)

    def test_false_string_is_false(self):
        self.assertFalse(classifier.validate_classification({'is_africa_related': 'false'})['is_africa_related'])

    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test'})
    @patch('classifier.wait_for_rate_limit')
    @patch('classifier.get_client')
    def test_sdk_classifies_json(self, client, wait):
        client.return_value.models.generate_content.return_value = Mock(text='{"primary_category":"AI Governance","relevance_score":8,"is_africa_related":true}')
        result = classifier.classify_article('Kenya AI bill', '')
        self.assertEqual(result['relevance_score'], 8)
        self.assertEqual(client.return_value.models.generate_content.call_args.kwargs['model'], classifier.MODEL_NAME)

    @patch('sheets_handler.get_sheet', side_effect=ConnectionError('unavailable'))
    def test_sheet_read_failure_is_not_empty_database(self, sheet):
        with self.assertRaises(ConnectionError):
            sheets_handler.get_existing_urls()

    @patch('scraper.get_existing_urls', side_effect=ConnectionError('unavailable'))
    @patch('scraper.parse_all_feeds')
    def test_no_scrape_after_sheet_read_failure(self, parse, urls):
        with self.assertRaises(ConnectionError):
            scraper.main()
        parse.assert_not_called()

    @patch('scraper.fetch_feed', side_effect=TimeoutError('timeout'))
    def test_all_failed_feeds_fail_run(self, fetch):
        with self.assertRaises(RuntimeError):
            scraper.parse_all_feeds({'rss_feeds': [{'name': 'Test', 'url': 'https://example.com'}]}, set())

    @patch('scraper.fetch_feed', return_value=Mock(entries=[], bozo=False))
    def test_valid_empty_feed_is_success(self, fetch):
        self.assertEqual(scraper.parse_all_feeds({'rss_feeds': [{'name': 'Test', 'url': 'https://example.com'}]}, set()), [])

    @patch('scraper.get_existing_urls', return_value=set())
    @patch('scraper.parse_all_feeds', return_value=[{'title': 'x'}])
    @patch('scraper.process_and_save_articles', return_value={'processed': 1, 'classified': 1, 'skipped_fallback': 0, 'saved': 0, 'below_threshold': 0, 'errors': 1})
    def test_save_errors_fail_run(self, process, parse, urls):
        with self.assertRaises(RuntimeError):
            scraper.main()

    def test_configured_country_keywords_are_used(self):
        score, ai, africa = scraper.calculate_keyword_score('Lesotho AI bill advances', '', {'keywords_filter': {'primary_keywords': ['AI bill'], 'africa_keywords': ['Lesotho']}})
        self.assertTrue(ai and africa)
        self.assertGreaterEqual(score, 5)

    def test_short_keywords_do_not_match_inside_words(self):
        _, _, africa = scraper.calculate_keyword_score('AI policy author', '', {'keywords_filter': {'africa_keywords': ['AU']}})
        self.assertFalse(africa)

    @patch('sheets_handler.get_sheet')
    def test_article_metadata_written_as_literal_text(self, sheet):
        sheet.return_value.row_values.return_value = ['Title']
        self.assertTrue(sheets_handler.add_to_sheet({'title': '=1+1'}))
        self.assertEqual(sheet.return_value.append_row.call_args.kwargs['value_input_option'], 'RAW')

if __name__ == '__main__':
    unittest.main()
