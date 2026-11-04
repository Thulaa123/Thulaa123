import importlib.util
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch
import xml.etree.ElementTree as ET
spec=importlib.util.spec_from_file_location('stats',Path(__file__).resolve().parents[1]/'scripts/update_stats.py')
stats=importlib.util.module_from_spec(spec);spec.loader.exec_module(stats)

class StatsTests(unittest.TestCase):
    def test_public_and_owned_filter(self):
        def repo(owner,private=False,fork=False):return {'owner':{'login':owner},'private':private,'fork':fork}
        rows=[repo('Thulaa123'),repo('THULAA123',fork=True),repo('Thulaa123',private=True),repo('other')]
        self.assertEqual(len(stats.public_owned(rows,'Thulaa123')),2)
        self.assertEqual(len(stats.public_owned(rows,'Thulaa123',True)),1)

    def test_languages_aggregate_without_losing_tail(self):
        result=stats.aggregate_languages([{'Python':80,'JS':50},{'Python':20,'A':10,'B':8,'C':6,'D':4,'E':2}])
        self.assertEqual(result[0],('Python',100))
        self.assertEqual(len(result),6)
        self.assertEqual(sum(v for _,v in result),180)
        self.assertEqual(result[-1],('Other',6))

    def test_reject_bad_language_counts(self):
        with self.assertRaises(ValueError):stats.aggregate_languages([{'Python':-1}])

    def test_language_card_escapes_names(self):
        svg=stats.render_languages({'languages':[('A&B <script>',100)]},'04 Nov 2026')
        ET.fromstring(svg)
        self.assertIn('A&amp;B &lt;script&gt;',svg)
        self.assertNotIn('<script>',svg)

    def test_empty_languages(self):
        svg=stats.render_languages({'languages':[]},'04 Nov 2026')
        ET.fromstring(svg);self.assertIn('No public language data yet',svg)

    def test_fetch_failure_preserves_published_cards(self):
        with tempfile.TemporaryDirectory() as folder:
            output=Path(folder)
            for filename in ['overview.svg','languages.svg']:
                (output/filename).write_text('last successful card')
            with patch('sys.argv',['update_stats.py','--output',folder]), patch.object(stats,'collect',side_effect=RuntimeError('API unavailable')):
                with self.assertRaises(RuntimeError):stats.main()
            for filename in ['overview.svg','languages.svg']:
                self.assertEqual((output/filename).read_text(),'last successful card')

    def test_collection_pagination_and_fork_exclusion(self):
        original={'private':False,'fork':False,'owner':{'login':'tester'},'full_name':'tester/a','stargazers_count':2,'forks_count':1}
        fork=dict(original,full_name='tester/fork',fork=True,stargazers_count=99)
        def api(endpoint,paginate=False):
            if endpoint=='users/tester':return {'followers':3}
            if '/repos?' in endpoint:
                self.assertTrue(paginate);return [[original],[fork]]
            if endpoint=='repos/tester/a/languages':return {'Python':10}
            if 'type%3Apr' in endpoint:return {'total_count':4,'incomplete_results':False}
            if 'type%3Aissue' in endpoint:return {'total_count':5,'incomplete_results':False}
            self.fail('Unexpected request: '+endpoint)
        with patch.object(stats,'api',side_effect=api):data=stats.collect('tester')
        self.assertEqual(data['repositories'],2);self.assertEqual(data['stars'],2)
        self.assertEqual(data['pull_requests'],4);self.assertEqual(data['languages'],[('Python',10)])
        ET.fromstring(stats.render_stats(data,'04 Nov 2026'))

if __name__=='__main__':unittest.main()
