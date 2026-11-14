import ast
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from resume_extraction_claim_audit.audit import audit, module_evidence, claims
from resume_extraction_claim_audit.__main__ import main
from resume_extraction_claim_audit import phrases

EXPECTED_POS = ('resume extraction', 'extract resumes', 'extracts resumes', 'extracting resumes', 'extract resume', 'extracts resume', 'extracting resume', 'resume parsing', 'resume parser', 'parse resumes', 'parses resumes', 'parse resume', 'parses resume', 'resume scanning', 'resume scanner', 'scan resumes', 'scans resumes', 'scan resume', 'scans resume', 'cv extraction', 'extract cvs', 'extracts cvs', 'extracting cvs', 'extract cv', 'extracts cv', 'extracting cv', 'cv parsing', 'cv parser', 'parse cvs', 'parses cvs', 'parse cv', 'parses cv', 'curriculum vitae extraction', 'extract curriculum vitae', 'extracts curriculum vitae', 'extracting curriculum vitae', 'resume data extraction', 'extract resume data', 'resume field extraction', 'candidate extraction', 'extract candidates', 'extracts candidates', 'extracting candidates', 'extract candidate', 'extracts candidate', 'extracting candidate', 'candidate profile extraction', 'extract candidate profiles', 'extracts candidate profiles', 'extract candidate profile')
EXPECTED_NEG = ('no resume extraction', 'does not extract resumes', 'does not extract resume', 'does not support resume extraction', 'without resume extraction', 'no cv extraction', 'does not extract cvs', 'does not extract cv', 'does not support cv extraction', 'without cv extraction', 'no curriculum vitae extraction', 'does not extract curriculum vitae', 'does not support curriculum vitae extraction', 'without curriculum vitae extraction', 'no resume parser', 'does not parse resumes', 'does not parse resume', 'no resume scanner', 'does not scan resumes', 'does not scan resume', 'no candidate extraction', 'does not extract candidates', 'does not extract candidate', 'resume extraction not supported')
EXPECTED_GENERIC = ('extract_resume', 'extract_resumes', 'parse_resume', 'parse_resumes', 'extract_cv', 'extract_cvs', 'parse_cv', 'parse_cvs', 'extract_resume_data', 'parse_resume_data', 'resume_extraction', 'resume_extractor', 'resume_parser', 'cv_extraction', 'cv_extractor', 'cv_parser', 'extract_resume_info', 'parse_resume_info', 'resume_scan', 'resume_scanner', 'scan_resume', 'scan_resumes', 'extract_candidate_profile', 'parse_candidate_profile')

class AuditTests(unittest.TestCase):
    def fixture(self, doc='extract resumes', files=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / 'README.md').write_text(doc)
        for name, source in (files or {}).items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source)
        return root

    def cli(self, root, *options):
        with contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(io.StringIO()):
            code = main(['audit', str(root), *options])
        return code, output.getvalue()

    def test_phrase_oracle(self):
        tree = ast.parse(Path(phrases.__file__).read_text())
        parsed = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)}
        self.assertEqual(parsed['RESUMEEXTRACTION'], EXPECTED_POS)
        self.assertEqual(parsed['NORESUMEEXTRACTION'], EXPECTED_NEG)
        self.assertEqual(parsed['GENERIC_NAMES'], EXPECTED_GENERIC)
        self.assertEqual((len(EXPECTED_POS), len(EXPECTED_NEG), len(set(EXPECTED_GENERIC))), (50, 24, 24))

    def test_good(self):
        self.assertEqual(self.cli(self.fixture(files={'app.py': 'x.extract_resume()'}))[0], 0)

    def test_bad(self):
        code, output = self.cli(self.fixture(), '--json')
        self.assertEqual(code, 2)
        result = json.loads(output)
        self.assertEqual(result['verdict'], 'FAIL')
        self.assertEqual(result['findings'][0]['rule'], 'documented-resume-extraction-claim-false')
        self.assertEqual(result['findings'][0]['severity'], 'HIGH')
        self.assertTrue(result['findings'][0]['message'])

    def test_test_only(self):
        root = self.fixture(files={'tests/demo.py': 'x.extract_resume()'})
        self.assertEqual(self.cli(root)[0], 0)
        self.assertEqual(audit(root)['findings'][0]['severity'], 'MEDIUM')
        self.assertEqual(self.cli(root, '--fail-on', 'medium')[0], 2)

    def test_denial(self):
        root = self.fixture('does not extract resumes', {'app.py': 'x.extract_resume()'})
        self.assertEqual(self.cli(root)[0], 2)
        self.assertEqual(audit(root)['findings'][0]['rule'], 'documented-no-resume-extraction-claim-false')
        self.assertEqual(audit(root)['findings'][0]['severity'], 'HIGH')

    def test_no_claim_and_asymmetry(self):
        self.assertEqual(audit(self.fixture('neutral'))['verdict'], 'PASS')
        self.assertEqual(audit(self.fixture())['verdict'], 'FAIL')
        self.assertEqual(audit(self.fixture('no resume extraction'))['verdict'], 'PASS')

    def test_fences_inline_normalization(self):
        for delimiter in ('```', '~~~', '   ````'):
            self.assertEqual(claims(delimiter + '\nextract resumes\n' + delimiter), ([], []))
        self.assertEqual(claims('`extract resumes`')[0], ['extract resumes'])
        self.assertEqual(claims("Doesn't extract resumes"), ([], ['does not extract resumes']))
        self.assertEqual(claims('RESUME-EXTRACTION')[0], ['resume extraction'])
        self.assertEqual(claims('extract resumesuffix'), ([], []))
        self.assertEqual(claims('extract\n\nresumes'), ([], []))

    def test_all_phrases(self):
        for phrase in EXPECTED_POS:
            self.assertTrue(claims(phrase)[0], phrase)
        for phrase in EXPECTED_NEG:
            self.assertEqual(claims(phrase), ([], [phrase]))

    def test_exclusions_and_ignore(self):
        for name in ('tests/app.py', 'test_app.py', 'app_test.py', 'fixtures/app.py', 'docs/app.py', 'examples/app.py'):
            result = audit(self.fixture(files={name: 'x.extract_resume()'}))
            self.assertFalse(result['production_evidence'], name)
        root = self.fixture(files={'src/app.py': 'x.extract_resume()'})
        self.assertEqual(self.cli(root, '--ignore', 'src')[0], 2)
        self.assertEqual(self.cli(root, '--ignore', 'sr')[0], 0)

    def test_docs_selection(self):
        root = self.fixture('neutral', {'nested/docs/a.md': 'extract resumes', 'other.md': 'no resume extraction'})
        self.assertEqual(audit(root)['verdict'], 'FAIL')
        self.assertEqual(len(audit(root)['findings']), 1)

    def test_symlinks(self):
        root = self.fixture('neutral', {'outside/app.py': 'x.extract_resume()'})
        (root / 'link.py').symlink_to(root / 'outside/app.py')
        (root / 'linked').symlink_to(root / 'outside', target_is_directory=True)
        self.assertFalse(audit(root, ['outside'])['production_evidence'])
        (root / 'docs').symlink_to(root / 'outside', target_is_directory=True)
        self.assertEqual(audit(root, ['outside'])['verdict'], 'PASS')

    def test_split_modules(self):
        pairs = [('import mindee\nc=mindee.Client()', 'x.parse(product.ResumeV1)'), ('import affinda\naffinda.AffindaAPI()\naffinda.CollectionCreate(extractor="resume")', 'x.create_document()'), ('from pyresparser import ResumeParser\nResumeParser(f)', 'x.get_extracted_data()'), ('import resulex\nresulex.Parser()', 'x.parse()'), ('post("https://api.edenai.run/v3/universal-ai")', 'model="ocr/resume_parser/affinda"')]
        for a, b in pairs:
            self.assertEqual(audit(self.fixture(files={'a.py': a, 'b.py': b}))['verdict'], 'FAIL')

    def test_shadowing(self):
        cases = ['from sdk import extract_resume\ndef extract_resume(): pass\nextract_resume()', 'class C:\n def extract_resume(self): pass\nx.extract_resume()', 'from sdk import extract_resume as er\ner = other\ner()', 'from sdk import extract_resume as er\ner: object = other\ner()', 'from sdk import extract_resume as er\nwith ctx() as er:\n er()', 'from sdk import extract_resume as er\nasync def f():\n async with ctx() as er:\n  er()', 'import affinda\naffinda = other\naffinda.AffindaAPI()\naffinda.CollectionCreate(extractor="resume")\nx.create_document()', 'import mindee\ndef Client(): pass\nmindee.Client()\nx.parse(product.ResumeV1)']
        for source in cases:
            self.assertFalse(module_evidence(source), source)

    def test_usage_and_io(self):
        for args in ([], ['wrong'], ['audit', '--fail-on', 'HIGH'], ['audit', '--ignore'], ['audit', '/nonexistent-r201']):
            with contextlib.redirect_stderr(io.StringIO()):
                try:
                    code = main(args)
                except SystemExit as error:
                    code = error.code
            self.assertEqual(code, 1)

    def test_version_and_module(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as raised:
                main(['--version'])
        self.assertEqual(raised.exception.code, 0)
        self.assertEqual(output.getvalue().strip(), '0.1.0')
        result = subprocess.run([sys.executable, '-m', 'resume_extraction_claim_audit', '--version'], capture_output=True, text=True)
        self.assertEqual((result.returncode, result.stdout.strip()), (0, '0.1.0'))


POSITIVE_CASES = [
 'import mindee\nc=mindee.Client()\nc.parse(product.ResumeV1)',
 'from mindee import Client\nfrom mindee.product import ResumeV1\nClient()\nx.parse(ResumeV1)',
 'import mindee\nmindee.Client()\nx.parse(product=mindee.product.ResumeV1)',
 'from mindee import Client as C\nC()\nx.parse(mindee.v1.product.ResumeV1)',
 'import affinda\naffinda.AffindaAPI()\naffinda.models.CollectionCreate(extractor="resume")\nx.create_document()',
 'import affinda as a\na.AffindaAPI()\na.models.CollectionCreate(extractor="resume")\nx.create_document()',
 'from affinda import AffindaAPI as A\nfrom affinda.models import CollectionCreate as C\nA()\nC(extractor="resume")\nx.create_document()',
 'from resume_parser import resumeparse\nresumeparse(f)',
 'from resume_parser import resumeparse as rp\nrp(f)',
 'import resume_parser as rp\nrp.resumeparse(f)',
 'import resulex\nresulex.parse(text)',
 'import resulex\np=resulex.Parser()\np.parse(text)',
]
for module in ('pyresparser', 'pydparser', 'indegreeparser'):
    POSITIVE_CASES += ['from '+module+' import ResumeParser\nResumeParser(f).get_extracted_data()', 'import '+module+' as p\np.ResumeParser(f)\nx.get_extracted_data()']
for url in ('https://api.sovren.com/parser/resume', 'https://rest.rchilli.com/RChilliParser/Rchilli/parseResume', 'https://rest.rchilli.com/RChilliParser/Rchilli/parseResumeBinary'):
    POSITIVE_CASES += ['post('+repr(url)+')', 'post(url='+repr(url)+')']
for model in ('affinda', 'hireability'):
    POSITIVE_CASES += ['post("https://api.edenai.run/v3/universal-ai", json={"model":"ocr/resume_parser/'+model+'"})']
for name in EXPECTED_GENERIC:
    POSITIVE_CASES += ['x.'+name+'()', 'from sdk import '+name+' as f\nf()']

NEGATIVE_CASES = ['import '+module for module in ('mindee', 'veryfi', 'azure.ai.formrecognizer', 'azure.ai.documentintelligence', 'affinda', 'pyresparser', 'pydparser', 'indegreeparser', 'resume_parser', 'resulex', 'boto3', 'google.cloud.documentai')]
NEGATIVE_CASES += ['import mindee\nmindee.Client()', 'import azure.ai.documentintelligence\nx.DocumentIntelligenceClient()', 'import veryfi\nveryfi.Client()', 'import affinda\naffinda.AffindaAPI()', 'import affinda\naffinda.AffindaAPI()\nx.create_document()', 'import affinda\nx.create_resume_search()', 'import affinda\nx.search_resumes()', 'x.get_extracted_data()', 'resumeparse(f)', 'extract_resume(f)', '"extract resumes"', '# extract resumes', 'x.extract_resume', 'bad syntax !', 'text.parse("resume")', 'import resulex\nresulex.Parser()', '"ocr/resume_parser/affinda"', 'post("https://api.edenai.run/v3/universal-ai", json={"model":"ocr/invoice_parser/affinda"})', 'import re\nre.search("name", text)\nre.findall("skills", text)']
for product in ('InvoiceV4', 'ReceiptV5', 'PassportV1', 'FinancialDocumentV1', 'BankCheckV1', 'BankAccountDetailsV2', 'PayslipV2', 'PayslipV3', 'HealthcareCardV1', 'BusinessCardV1', 'CustomV1', 'GeneratedV1', 'Other'):
    NEGATIVE_CASES += ['import mindee\nmindee.Client()\nx.parse(product.'+product+')']
for model in ('invoice', 'receipt', 'layout', 'read', 'idDocument', 'check.us', 'tax.us', 'bankStatement.us', 'payStub.us', 'healthInsuranceCard.us', 'businessCard', 'creditCard', 'contract', 'mortgage.us.1003', 'resume'):
    NEGATIVE_CASES += ['import azure.ai.documentintelligence\nx.DocumentIntelligenceClient()\nx.begin_analyze_document("prebuilt-'+model+'")']
for name in ('process_any_document', 'process_any_document_url', 'process_document', 'process_document_url', 'process_w2_document', 'process_w9_document', 'process_w8_document', 'process_check', 'process_check_url', 'process_check_with_remittance', 'process_check_with_remittance_url', 'process_bank_statement_document', 'process_bank_statement_document_url', 'process_bussines_card_document', 'process_bussines_card_document_url', 'classify_document', 'get_business_cards', 'get_business_card', 'delete_business_card', 'process_resume_document', 'process_resume_document_url'):
    NEGATIVE_CASES += ['import veryfi\nveryfi.Client()\nx.'+name+'()']
for name in ('process_document', 'batch_process_documents', 'analyze_document', 'analyze_expense', 'start_document_analysis', 'get_expense_analysis', 'extract_text', 'image_to_string', 'read_csv', 'read_excel', 'read_pdf', 'convert_into', 'extract_table', 'extract_tables', 'find_table', 'find_tables'):
    NEGATIVE_CASES += ['x.'+name+'()']
for module in ('pyresparser', 'pydparser', 'indegreeparser'):
    NEGATIVE_CASES += ['from '+module+' import ResumeParser\nResumeParser(f)']
for extractor in ('invoice', 'receipt', 'job_description', 'Resume'):
    NEGATIVE_CASES += ['import affinda\naffinda.AffindaAPI()\naffinda.CollectionCreate(extractor='+repr(extractor)+')\nx.create_document()']
for url in ('https://api.sovren.com/parser/resume', 'https://rest.rchilli.com/RChilliParser/Rchilli/parseResume', 'https://rest.rchilli.com/RChilliParser/Rchilli/parseResumeBinary'):
    NEGATIVE_CASES += [repr(url)]
for url in ('https://api.sovren.com/parser/job', 'https://rest.rchilli.com/RChilliParser/Rchilli/parseJob', 'https://api.textkernel.com/resume'):
    NEGATIVE_CASES += ['post('+repr(url)+')']
for tool in ('mindee', 'veryfi', 'pyresparser', 'affinda'):
    NEGATIVE_CASES += ['import subprocess\nsubprocess.run(["'+tool+'", "resume.pdf"])']


def evidence_test(source, expected):
    def test(self):
        self.assertEqual(bool(module_evidence(source)), expected, source)
        result = audit(self.fixture(files={'app.py': source}))
        self.assertEqual(result['verdict'], 'PASS' if expected else 'FAIL')
    return test


for index, source in enumerate(POSITIVE_CASES):
    setattr(AuditTests, 'test_route_positive_%03d' % index, evidence_test(source, True))
for index, source in enumerate(NEGATIVE_CASES):
    setattr(AuditTests, 'test_route_negative_%03d' % index, evidence_test(source, False))

if __name__ == '__main__':
    unittest.main()
