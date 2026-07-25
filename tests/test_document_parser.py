import tempfile
import unittest
from pathlib import Path

from document_parser import DocumentParseError, parse_document, validate_file_signature


class DocumentParserTests(unittest.TestCase):
    def test_parse_markdown_preserves_searchable_text(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "实验一.md"
            path.write_text(
                "# 实验一\n\n使用 Wireshark 捕获 SMTP 数据包。",
                encoding="utf-8",
            )

            chunks = parse_document(path, "md")

        self.assertEqual(len(chunks), 1)
        self.assertIsNone(chunks[0].page_number)
        self.assertIn("Wireshark", chunks[0].content)
        self.assertIn("SMTP", chunks[0].content)

    def test_rejects_pdf_with_invalid_header(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "not-a-pdf.pdf"
            path.write_bytes(b"plain text, not a PDF")

            with self.assertRaisesRegex(DocumentParseError, "PDF 文件头无效"):
                validate_file_signature(path, "pdf")

    def test_rejects_docx_that_is_not_a_zip_archive(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "not-a-docx.docx"
            path.write_bytes(b"plain text, not a DOCX archive")

            with self.assertRaisesRegex(DocumentParseError, "DOCX 文件格式无效"):
                validate_file_signature(path, "docx")


if __name__ == "__main__":
    unittest.main()
