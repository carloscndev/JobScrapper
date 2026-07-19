"""Unit tests for secure CV validation and profile extraction (PROFILE-001).

The CV module intentionally keeps PDF/DOCX parsers optional.  Tests therefore
exercise validation with stdlib fixtures and skip parser-dependent paths with
an explicit reason when the optional libraries are not installed.
"""

from __future__ import annotations

from io import BytesIO
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest import mock
import zipfile


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"


def _load_cv_module():
    path = BACKEND / "app" / "cv_profile.py"
    spec = importlib.util.spec_from_file_location("jobscrapper_test_cv_profile", path)
    if spec is None or spec.loader is None:
        raise AssertionError("Unable to load CV profile module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


cv = _load_cv_module()


def _docx_bytes(*, member_name: str = "word/document.xml", content: bytes = b"<w:document/>") -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(member_name, content)
    return output.getvalue()


def _docx_with_members(*members: str) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("word/document.xml", b"<w:document/>")
        for member in members:
            archive.writestr(member, b"x")
    return output.getvalue()


class CVValidationTests(unittest.TestCase):
    def test_supported_extension_mime_and_magic_are_required(self) -> None:
        self.assertEqual(cv._validate(b"%PDF-1.7\nbody", "resume.pdf", "application/pdf", 100), "resume.pdf")
        self.assertEqual(
            cv._validate(_docx_bytes(), "resume.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 1000),
            "resume.docx",
        )
        with self.assertRaises(cv.CVValidationError):
            cv._validate(b"not a pdf", "resume.pdf", "application/pdf", 100)
        with self.assertRaisesRegex(cv.CVValidationError, "MIME"):
            cv._validate(b"%PDF-1.7", "resume.pdf", "text/plain", 100)
        with self.assertRaises(cv.CVValidationError):
            cv._validate(_docx_bytes(), "resume.txt", "text/plain", 1000)

    def test_size_and_filename_limits_are_enforced(self) -> None:
        with self.assertRaisesRegex(cv.CVValidationError, "exceeds"):
            cv._validate(b"%PDF-1.7" + b"x" * 20, "resume.pdf", "application/pdf", 10)
        for filename in ("../resume.pdf", "folder/resume.pdf", "resume\\.pdf", "", "a\n.pdf"):
            with self.subTest(filename=filename), self.assertRaises(cv.CVValidationError):
                cv._validate(b"%PDF-1.7", filename, "application/pdf", 100)

    def test_docx_zip_rejects_traversal_and_encrypted_members(self) -> None:
        with self.assertRaisesRegex(cv.CVValidationError, "unsafe"):
            cv._validate_docx(_docx_with_members("../evil"), 1000)

        class Info:
            def __init__(self, filename: str, *, flag_bits: int = 0, file_size: int = 1) -> None:
                self.filename = filename
                self.flag_bits = flag_bits
                self.file_size = file_size

        class Archive:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def namelist(self):
                return ["word/document.xml", "encrypted.bin"]

            def infolist(self):
                return [Info("word/document.xml"), Info("encrypted.bin", flag_bits=1)]

        with mock.patch.object(cv.zipfile, "ZipFile", return_value=Archive()):
            with self.assertRaisesRegex(cv.CVValidationError, "encrypted"):
                cv._validate_docx(b"zip", 1000)

        class ExpansionArchive(Archive):
            def infolist(self):
                return [Info("word/document.xml"), Info("expanded.bin", file_size=1000 * 20 + 1)]

        with mock.patch.object(cv.zipfile, "ZipFile", return_value=ExpansionArchive()):
            with self.assertRaisesRegex(cv.CVValidationError, "uncompressed"):
                cv._validate_docx(b"zip", 1000)

    def test_docx_zip_requires_document_xml(self) -> None:
        with self.assertRaisesRegex(cv.CVValidationError, "document.xml"):
            cv._validate_docx(_docx_bytes(member_name="word/styles.xml"), 1000)

    def test_unreadable_extracted_text_is_rejected(self) -> None:
        with mock.patch.object(cv, "_extract", return_value="too short"):
            with self.assertRaisesRegex(cv.CVValidationError, "unreadable"):
                cv.parse_cv(BytesIO(b"%PDF-1.7"), "resume.pdf", "application/pdf")

    def test_structured_profile_contains_editable_fields(self) -> None:
        parsed = cv._profile(
            "Ada Lovelace\nPython engineer\n\nSkills\nPython, FastAPI, SQL\n"
            "Experience\nBuilt APIs\nEducation\nBSc Mathematics\nLanguages\nEnglish, Spanish"
        )
        self.assertEqual(parsed["name"], "Ada Lovelace")
        self.assertIn("python", parsed["skills"])
        self.assertIn("fastapi", parsed["skills"])
        self.assertEqual(parsed["experience"], [{"text": "Built APIs"}])
        self.assertEqual(parsed["education"], [{"text": "BSc Mathematics"}])
        self.assertEqual(parsed["languages"], ["English, Spanish"])
        self.assertEqual(parsed["summary"], "Ada Lovelace Python engineer")

    def test_optional_extractors_raise_explicit_skip_exception(self) -> None:
        with mock.patch.dict(sys.modules, {"pypdf": None}):
            with self.assertRaises(cv.CVParserUnavailable):
                cv._extract(b"%PDF-1.7", ".pdf")
        with mock.patch.dict(sys.modules, {"docx": None}):
            with self.assertRaises(cv.CVParserUnavailable):
                cv._extract(_docx_bytes(), ".docx")

    def test_encrypted_pdf_is_rejected(self) -> None:
        fake_pypdf = types.ModuleType("pypdf")

        class EncryptedReader:
            def __init__(self, *_args, **_kwargs):
                pass

            is_encrypted = True

        fake_pypdf.PdfReader = EncryptedReader
        with mock.patch.dict(sys.modules, {"pypdf": fake_pypdf}):
            with self.assertRaisesRegex(cv.CVValidationError, "Encrypted"):
                cv._extract(b"%PDF-1.7", ".pdf")


class ProfileServiceTests(unittest.TestCase):
    def test_profile_service_ingest_contract_is_present(self) -> None:
        source = (BACKEND / "app" / "services.py").read_text()
        self.assertIn("class ProfileService", source)
        self.assertIn("def ingest_cv", source)
        self.assertIn("cv_text=parsed.text", source)
        self.assertIn("cv_filename=parsed.filename", source)

    def test_profile_service_ingests_structured_profile_when_dependencies_exist(self) -> None:
        if importlib.util.find_spec("sqlalchemy") is None:
            self.skipTest("SQLAlchemy is not installed; runtime ProfileService test is optional")
        backend_path = str(BACKEND)
        if backend_path not in sys.path:
            sys.path.insert(0, backend_path)
        from app.services import ProfileService

        class Repository:
            def add(self, profile):
                return profile

        parsed = cv.ParsedCV("resume.pdf", "application/pdf", "Ada Lovelace\nPython", {"name": "Ada Lovelace", "skills": ["Python"], "experience": [], "education": [], "languages": [], "summary": ""})
        with mock.patch("app.services.parse_cv", return_value=parsed):
            profile, returned = ProfileService(Repository()).ingest_cv(BytesIO(b"ignored"), "resume.pdf", "application/pdf")
        self.assertEqual(profile.name, "Ada Lovelace")
        self.assertEqual(profile.cv_filename, "resume.pdf")
        self.assertEqual(profile.skills, ["Python"])
        self.assertIs(returned, parsed)


if __name__ == "__main__":
    unittest.main()
