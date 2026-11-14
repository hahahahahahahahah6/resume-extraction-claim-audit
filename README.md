# Documentation claim auditor

An offline static audit tool comparing documentation promises with recognized source calls. It never executes project code. Requires Python 3.9 or newer and has no runtime dependencies.

## Installation and usage

```sh
python3 -m pip install .
resume-extraction-claim-audit audit .
resume-extraction-claim-audit audit . --json --verbose --ignore build --ignore dist --fail-on medium
python3 -m resume_extraction_claim_audit audit .
resume-extraction-claim-audit --version
```

The repository defaults to the current directory. Ignore prefixes are repeatable relative paths. Exit 0 means PASS at the threshold; 2 means findings at that threshold; 1 means usage or I/O error. The default threshold is high; medium also fails on test-only evidence. JSON reports verdict, findings with rule, severity, message and locations, and production and test evidence paths. Verbose text lists evidence paths.

## Matching rules

Root README.md and Markdown files with a docs path component are scanned. Fenced code blocks using backticks or tildes with up to three leading spaces are excluded; inline code counts. Paragraphs split on blank lines. Matching lowercases, expands contractions, replaces hyphens with spaces and collapses whitespace. Boundary matches prefer longest phrases with alphabetical ties. Denial spans are removed first. Each family produces at most one finding.

Source is parsed with AST. Symlinks are excluded. Files under fixtures, docs and examples supply no evidence; tests count separately. Invalid syntax supplies no evidence. Routes require a single module. Local function, method and class definitions shadow route names; assignment, annotated assignment and context manager bindings shadow imports. Generic attribute calls allow any base, while bare names require an imported recognized name. A positive promise without source fails; a denial without source passes.

## Reference vocabulary and evidence

The following reference data describes the checked capability.

```text
resume extraction
extract resumes
extracts resumes
extracting resumes
extract resume
extracts resume
extracting resume
resume parsing
resume parser
parse resumes
parses resumes
parse resume
parses resume
resume scanning
resume scanner
scan resumes
scans resumes
scan resume
scans resume
cv extraction
extract cvs
extracts cvs
extracting cvs
extract cv
extracts cv
extracting cv
cv parsing
cv parser
parse cvs
parses cvs
parse cv
parses cv
curriculum vitae extraction
extract curriculum vitae
extracts curriculum vitae
extracting curriculum vitae
resume data extraction
extract resume data
resume field extraction
candidate extraction
extract candidates
extracts candidates
extracting candidates
extract candidate
extracts candidate
extracting candidate
candidate profile extraction
extract candidate profiles
extracts candidate profiles
extract candidate profile
no resume extraction
does not extract resumes
does not extract resume
does not support resume extraction
without resume extraction
no cv extraction
does not extract cvs
does not extract cv
does not support cv extraction
without cv extraction
no curriculum vitae extraction
does not extract curriculum vitae
does not support curriculum vitae extraction
without curriculum vitae extraction
no resume parser
does not parse resumes
does not parse resume
no resume scanner
does not scan resumes
does not scan resume
no candidate extraction
does not extract candidates
does not extract candidate
resume extraction not supported

Generic names:
extract_resume, extract_resumes, parse_resume, parse_resumes, extract_cv, extract_cvs, parse_cv, parse_cvs, extract_resume_data, parse_resume_data, resume_extraction, resume_extractor, resume_parser, cv_extraction, cv_extractor, cv_parser, extract_resume_info, parse_resume_info, resume_scan, resume_scanner, scan_resume, scan_resumes, extract_candidate_profile, parse_candidate_profile

documented-resume-extraction-claim-false HIGH (MEDIUM for test-only evidence)
documented-no-resume-extraction-claim-false HIGH



mindee Client construction + parse call passing ResumeV1 (Name
exactly ResumeV1, or Attribute with attr exactly ResumeV1 such
as product.ResumeV1 / mindee.product.ResumeV1 /
mindee.v1.product.ResumeV1) as any argument; import gate
mindee. ResumeV1 exists in mindee 4.x only (4.22.0 wheel
inspected 2026-11-13); mindee 5.4.0 removed it (wheel inspected
2026-11-13: no resume product directory, zero "resume" hits in
any .py file). The tool detects the call in source, not the
installed SDK version. A parse call passing any other product
(InvoiceV4, ReceiptV5, PassportV1, FinancialDocumentV1,
BankCheckV1, BankAccountDetailsV2, PayslipV2, PayslipV3,
HealthcareCardV1, BusinessCardV1, CustomV1, GeneratedV1, or any
other) is NOT evidence.

## affinda names (implementation MUST match exactly)

AffindaAPI construction + CollectionCreate call with extractor
keyword exactly "resume" + create_document call (Attribute attr
exactly create_document, any base), all in the same module;
import gate affinda. Affinda Python SDK 4.26.0, v3 API, per the
PyPI quickstart verified 2026-11-13. A create_document call
with no CollectionCreate extractor="resume" in the same module
is NOT evidence; a CollectionCreate with any other extractor
value is NOT evidence; create_resume_search / search_resumes
alone is NOT evidence (search, not extraction).

## pyresparser / pydparser / indegreeparser names (implementation MUST match exactly)

ResumeParser construction (Name resolved by from-import from
pyresparser / pydparser / indegreeparser, or Attribute with attr
exactly ResumeParser on a base bound to one of those modules) +
get_extracted_data call (Attribute attr exactly
get_extracted_data, any base), same module; import gate the
respective module. pyresparser 1.0.5, pydparser 1.0.4,
indegreeparser, per their PyPI pages verified 2026-11-13:
`from pyresparser import ResumeParser; data =
ResumeParser('/path/to/resume/file').get_extracted_data()`.

## resume_parser names (implementation MUST match exactly)

Call to resumeparse: Name exactly resumeparse resolved by a
from-import from resume_parser, or Attribute with attr exactly
resumeparse whose value chain starts from a Name bound to
resume_parser; import gate resume_parser. resume-parser 0.8.4
wheel inspected 2026-11-13: `resume_parser/__init__.py` exports
`resumeparse` from `resume_parser.resumeparse`.

## resulex names (implementation MUST match exactly)

Call to resulex.parse (Attribute attr exactly parse whose value
is a Name exactly resulex); OR resulex.Parser construction
(Attribute attr exactly Parser on a Name exactly resulex) +
parse call (Attribute attr exactly parse, any base), same
module; import gate resulex. resulex 0.1.3, per its PyPI page
verified 2026-11-13: `result = resulex.parse(text)`.

## sovren / rchilli / eden ai names (implementation MUST match exactly)

Sovren / RChilli: a Call whose first positional argument, or
url keyword argument, is the string literal exactly one of
"https://api.sovren.com/parser/resume",
"https://rest.rchilli.com/RChilliParser/Rchilli/parseResume",
"https://rest.rchilli.com/RChilliParser/Rchilli/parseResumeBinary".
Sovren Resume Parser REST API (POST) and RChilli Resume Parser
v8.0.0 docs (POST), verified 2026-11-13.
Eden AI: a Call whose first positional argument, or url keyword
argument, is the string literal exactly
"https://api.edenai.run/v3/universal-ai", AND a string literal
in the same module whose value starts with
"ocr/resume_parser/". Eden AI v3 Universal AI endpoint,
verified 2026-11-13.

## azure names (implementation MUST match exactly)

NO azure route: Azure Document Intelligence has no resume model.
The Microsoft Learn model-overview page (v4.0 GA), opened and
searched 2026-11-13, contains zero hits for "resume". A
begin_analyze_document call with ANY model id is NOT evidence.

## veryfi names (implementation MUST match exactly)

NO veryfi route: veryfi has no resume method in the Python SDK.
The 5.1.0 wheel, inspected 2026-11-13, contains zero hits for
"resume" across all .py files, so a veryfi call of ANY kind is
NOT evidence. A call to the non-existent
process_resume_document / process_resume_document_url counts as
nothing.

```

## Honest limitations

These notes explain ambiguity and exclusions.

```text
- The bare phrases "resume extraction" / "extract resume" /
  "extract resumes" are deliberately RESUMEEXTRACTION phrases:
  in document-tool docs they almost always name resume
  extraction. But "resume" can also name a resume the tool
  merely stores, displays, or manages (a resume database, a
  resume builder, a resume template library) without extracting
  fields from a resume document: a doc that means storing,
  displaying, building, or templating resumes, not extracting
  fields from them, is a false positive; the tool flags the claim,
  only the code decides.
- "resume parsing" / "resume parser" are deliberately phrases:
  a doc can say "resume parser" about a tool that only renders a
  resume as formatted text, or a "resume parser" that is really a
  keyword highlighter over plain text. The tool flags the claim;
  only the code decides.
- "resume scanning" / "scan resume(s)" are deliberately
  phrases: "scanning" a resume can mean merely photographing it
  or OCRing it into raw text, with no structured field extraction.
  The tool flags the claim; only the code decides.
- "cv extraction" / "extract cv(s)" / "cv parsing" / "cv parser"
  are deliberately phrases: "CV" is also an abbreviation in
  other domains (coefficient of variation in statistics,
  curriculum vitae is the intended sense here). A doc that means
  a different "CV" is a false positive; the tool flags the claim,
  only the code decides.
- "candidate extraction" / "extract candidate(s)" are
  deliberately phrases: "candidate" can also name a candidate
  record the tool merely stores, ranks, or matches from an ATS
  database, without parsing any resume. A doc that means storing,
  ranking, or matching candidates, not extracting fields from a
  resume document, is a false positive; the tool flags the claim,
  only the code decides.
- "candidate profile extraction" / "extract candidate profile(s)"
  are deliberately phrases: a candidate profile can be assembled
  from a form the candidate filled in, not from a resume document.
  The tool flags the claim; only the code decides.
- "curriculum vitae extraction" / "extract curriculum vitae" are
  deliberately phrases: a doc can mention a curriculum vitae the
  tool merely displays or archives. The tool flags the claim;
  only the code decides.
- A generic `extract_resume(` / `parse_resume(` /
  `extract_cv(` call can name a string parser for text the user
  typed in rather than a document extractor: the tool counts the
  call, the claim plus the code decide — and a subprocess call
  invoking an external CLI is NOT evidence by design, so a thin
  wrapper that only calls subprocess fails.
- Mindee `parse` with ResumeV1 counts as evidence: ResumeV1
  exists in mindee 4.x (4.22.0 wheel inspected 2026-11-13). The
  tool detects the call in source, not whether the call succeeds
  against a current API version.
- Mindee `parse` with ResumeV1 is a 4.x-only fingerprint: mindee
  5.4.0 removed the off-the-shelf resume product (wheel inspected
  2026-11-13 — no resume product directory, zero "resume" hits in
  any .py file). Code written against mindee 5.x cannot use this
  route.
- Mindee `parse` with InvoiceV4 / ReceiptV5 / PassportV1 /
  FinancialDocumentV1 / BankCheckV1 / BankAccountDetailsV2 /
  PayslipV2 / PayslipV3 / HealthcareCardV1 / BusinessCardV1 /
  CustomV1 / GeneratedV1 is NOT detected: those are other
  document types, and mindee 5.x has no resume product at all.
 
- Affinda `create_document` with no CollectionCreate
  extractor="resume" in the same module is NOT detected: the
  collection could be an invoice, receipt, or other collection.
 
- Affinda `create_resume_search` / search over parsed resumes is
  NOT detected: search, not extraction.
- Azure `begin_analyze_document` with ANY model id is NOT
  detected: Azure Document Intelligence has no resume model (the
  Learn model-overview page, v4.0 GA, contains zero hits for
  "resume", verified 2026-11-13).
- Veryfi calls of ANY kind are NOT detected: veryfi has no resume
  method (5.1.0 wheel inspected 2026-11-13 — the word "resume"
  does not appear anywhere in the wheel).
- Google Document AI `process_document` / `batch_process_documents`
  with ANY processor is NOT detected: Document AI has no resume
  processor (the processors list page contains zero hits for
  "Resume Parser", verified 2026-11-13).
- Textkernel / HireAbility / Daxtra / Hirize / Klippa /
  Superparser / CVParser AI / SenseLoaf / Extracta REST calls are
  NOT detected: no exact endpoint URL for those providers is
  listed in this spec; only the Sovren, RChilli, and Eden AI
  URLs above count.
- Mindee v2 extraction API calls with a configurable model id are
  NOT detected: the model id is user-configured, not a fixed
  resume product fingerprint.
- Textract `analyze_document` / `analyze_expense` /
  `start_document_analysis` / `get_expense_analysis` are NOT
  detected: generic document and expense analysis are not
  resume extraction, and Textract has no resume operation.
 
- A hand-rolled extraction from OCR text (`re.search` /
  `re.findall` on extracted text plus manual field assembly, no
  listed call) is NOT detected: the tool requires a listed call.
 
- The mindee CLI, the veryfi CLI, the pyresparser CLI, the
  affinda CLI, and any other external resume tool invoked through
  subprocess are NOT detected: subprocess calls invoking an
  external CLI are NOT evidence by design.
- Azure Document Intelligence, Mindee, Veryfi, Affinda, Sovren,
  RChilli, and Eden AI are cloud APIs: the tool detects the
  client call in source, not whether credentials are configured
  or the call succeeds.
- "extract resume text" / "extract text from resume" claims are
  NOT in the phrase lists: extracting plain text from a resume is
  text extraction, not resume field extraction. Say so in the
  README.
- "resume builder" / "resume writer" / "resume template" claims
  are NOT in the phrase lists: building, writing, or templating a
  resume is creating one, not extracting fields from one. Say so
  in the README.
- "resume screening" / "resume ranking" / "resume matching"
  claims are NOT in the phrase lists: screening, ranking, or
  matching resumes is downstream of parsing, not parsing itself.
 
- "job description parsing" claims are NOT in the phrase lists:
  parsing a job description is a separate operation from parsing
  a resume.
- Invoice extraction claims ("extract invoices", "invoice
  extraction"), receipt extraction claims ("extract receipts",
  "receipt extraction"), ID document extraction claims ("extract
  passports", "passport extraction"), bank check extraction claims
  ("extract bank checks", "check extraction"), bank statement
  extraction claims ("extract bank statements", "statement
  extraction"), tax form extraction claims ("extract tax forms",
  "extract w2 forms", "1099 extraction"), pay stub extraction
  claims ("extract pay stubs", "payslip extraction"), health
  insurance card extraction claims ("extract health insurance
  cards", "health insurance card extraction"), business card
  extraction claims ("extract business cards", "business card
  extraction"), credit card extraction claims ("extract credit
  cards", "credit card extraction"), contract extraction claims
  ("extract contracts", "contract extraction"), and mortgage
  extraction claims ("extract mortgages", "mortgage extraction")
  are NOT in the phrase lists: this family covers resumes only.
 
- As with every family: static pattern matching, not semantic
  judgement; dead code counts; alias chains the tracer cannot follow
  are missed; exact phrases only, not semantics; denial handling
  depends on the denial phrase list; each route must sit in a single
  module.

```

## Differentiation

The checked capability concerns structured candidate, contact, experience, education and skills fields from documents. Adjacent families cover OCR text recognition, table structure and other document types. This tool validates neither returned fields nor service availability.

## Development

```sh
python3 -m unittest discover
python3 -m venv .venv
.venv/bin/python3 -m pip install build
.venv/bin/python3 -m build
```

Both distributions bundle the tests. The tool uses only the standard library, makes no network calls and writes only to standard output and standard error.
