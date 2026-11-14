"""Offline document matching and module-local AST evidence."""
import ast
import os
from pathlib import Path
import re
from .phrases import RESUMEEXTRACTION, NORESUMEEXTRACTION, GENERIC_NAMES


def normalize(text):
    return ' '.join(text.lower().replace("n't", ' not').replace('-', ' ').split())


def pattern(phrases):
    return re.compile(r'\b(?:' + '|'.join(re.escape(p) for p in sorted(phrases, key=lambda p: (-len(p), p))) + r')\b')


POSITIVE = pattern(RESUMEEXTRACTION)
NEGATIVE = pattern(NORESUMEEXTRACTION)


def claims(text):
    lines = []
    fence = None
    for line in text.splitlines():
        match = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if fence:
            if match and match[1][0] == fence[0] and len(match[1]) >= len(fence) and not match[2].strip():
                fence = None
            lines.append('')
        elif match:
            fence = match[1]
            lines.append('')
        else:
            lines.append(line)
    positive, negative = [], []
    for paragraph in re.split(r'\n\s*\n', '\n'.join(lines)):
        value = normalize(paragraph)
        negative.extend(m.group() for m in NEGATIVE.finditer(value))
        positive.extend(m.group() for m in POSITIVE.finditer(NEGATIVE.sub(' ', value)))
    return positive, negative


def module_evidence(source):
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    nodes = list(ast.walk(tree))
    imports, gates, from_names = {}, set(), set()
    shadow = {n.name for n in nodes if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    bound = set()
    for node in nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports[alias.asname or alias.name.split('.')[0]] = alias.name if alias.asname else alias.name.split('.')[0]
                gates.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            gates.add(node.module.split('.')[0])
            for alias in node.names:
                name = alias.asname or alias.name
                imports[name] = node.module + '.' + alias.name
                from_names.add(name)
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            targets = [item.optional_vars for item in node.items if item.optional_vars]
        for target in targets:
            bound.update(n.id for n in ast.walk(target) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store))
    blocked = shadow | bound

    def resolve(node):
        if isinstance(node, ast.Name):
            return imports.get(node.id, '') if node.id not in blocked else ''
        if isinstance(node, ast.Attribute):
            base = resolve(node.value)
            return base + '.' + node.attr if base else ''
        return ''

    def attr(call, name):
        return isinstance(call.func, ast.Attribute) and call.func.attr == name and name not in shadow

    def literal(node):
        return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None

    calls = [n for n in nodes if isinstance(n, ast.Call)]
    def construction(call, module, name):
        if name in shadow:
            return False
        f = call.func
        if isinstance(f, ast.Name):
            allowed = {module + '.' + name}
            if module == 'affinda' and name == 'CollectionCreate':
                allowed.add('affinda.models.CollectionCreate')
            return f.id in from_names and resolve(f) in allowed
        return attr(call, name) and resolve(f.value).split('.')[0] == module

    routes = []
    for call in calls:
        f = call.func
        name = f.attr if isinstance(f, ast.Attribute) else resolve(f).split('.')[-1]
        if name in GENERIC_NAMES and name not in shadow:
            if isinstance(f, ast.Attribute) or (isinstance(f, ast.Name) and f.id in from_names and resolve(f)):
                routes.append('generic')
    if 'mindee' in gates:
        client = any(construction(c, 'mindee', 'Client') and (isinstance(c.func, ast.Name) or isinstance(c.func.value, ast.Name) and c.func.value.id == 'mindee') for c in calls)
        parse = any(attr(c, 'parse') and any((isinstance(a, ast.Name) and a.id == 'ResumeV1' and a.id not in blocked) or (isinstance(a, ast.Attribute) and a.attr == 'ResumeV1' and 'ResumeV1' not in shadow) for a in list(c.args) + [k.value for k in c.keywords]) for c in calls)
        if client and parse:
            routes.append('mindee')
    if 'affinda' in gates and any(construction(c, 'affinda', 'AffindaAPI') for c in calls) and any(construction(c, 'affinda', 'CollectionCreate') and any(k.arg == 'extractor' and literal(k.value) == 'resume' for k in c.keywords) for c in calls) and any(attr(c, 'create_document') for c in calls):
        routes.append('affinda')
    for module in ('pyresparser', 'pydparser', 'indegreeparser'):
        if module in gates and any(construction(c, module, 'ResumeParser') for c in calls) and any(attr(c, 'get_extracted_data') for c in calls):
            routes.append(module)
    if 'resume_parser' in gates and any(construction(c, 'resume_parser', 'resumeparse') for c in calls):
        routes.append('resume_parser')
    def resulex(call, name):
        return attr(call, name) and isinstance(call.func.value, ast.Name) and call.func.value.id == 'resulex' and 'resulex' not in blocked
    if 'resulex' in gates and (any(resulex(c, 'parse') for c in calls) or any(resulex(c, 'Parser') for c in calls) and any(attr(c, 'parse') for c in calls)):
        routes.append('resulex')
    urls = {literal(a) for c in calls for a in (list(c.args[:1]) + [k.value for k in c.keywords if k.arg == 'url'])}
    if urls & {'https://api.sovren.com/parser/resume', 'https://rest.rchilli.com/RChilliParser/Rchilli/parseResume', 'https://rest.rchilli.com/RChilliParser/Rchilli/parseResumeBinary'}:
        routes.append('endpoint')
    if 'https://api.edenai.run/v3/universal-ai' in urls and any(isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.startswith('ocr/resume_parser/') for n in nodes):
        routes.append('edenai')
    return sorted(set(routes))


def audit(root, ignore=(), fail_on='high'):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise OSError('Root must be a readable directory')
    positive, negative, production, tests = [], [], [], []
    prefixes = [Path(p).as_posix().rstrip('/') for p in ignore]
    def ignored(path):
        value = path.as_posix()
        return any(value == p or value.startswith(p + '/') for p in prefixes)
    for directory, dirs, files in os.walk(root, onerror=lambda error: (_ for _ in ()).throw(error), followlinks=False):
        base = Path(directory)
        dirs[:] = sorted(d for d in dirs if not (base / d).is_symlink() and not ignored((base / d).relative_to(root)))
        for name in sorted(files):
            path = base / name
            rel = path.relative_to(root)
            if path.is_symlink() or ignored(rel):
                continue
            if rel == Path('README.md') or path.suffix == '.md' and 'docs' in rel.parts:
                p, n = claims(path.read_text(encoding='utf-8'))
                positive.extend({'path': rel.as_posix(), 'phrase': x} for x in p)
                negative.extend({'path': rel.as_posix(), 'phrase': x} for x in n)
            if path.suffix != '.py' or set(rel.parts[:-1]) & {'fixtures', 'docs', 'examples'}:
                continue
            routes = module_evidence(path.read_text(encoding='utf-8'))
            if routes:
                target = tests if 'tests' in rel.parts[:-1] or name.startswith('test_') or name.endswith('_test.py') else production
                target.append({'path': rel.as_posix(), 'routes': routes})
    findings = []
    if positive and not production:
        findings.append({'rule': 'documented-resume-extraction-claim-false', 'severity': 'MEDIUM' if tests else 'HIGH', 'message': 'Documented promise has only test evidence.' if tests else 'Documented promise has no production evidence.', 'locations': positive})
    if negative and production:
        findings.append({'rule': 'documented-no-resume-extraction-claim-false', 'severity': 'HIGH', 'message': 'Documented denial contradicts production evidence.', 'locations': negative})
    failed = any(f['severity'] == 'HIGH' or fail_on.lower() == 'medium' for f in findings)
    return {'verdict': 'FAIL' if failed else 'PASS', 'findings': findings, 'production_evidence': production, 'test_evidence': tests}
