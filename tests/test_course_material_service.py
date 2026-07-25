import unittest

from course_material_service import create_storage_name, sanitize_original_filename


class CourseMaterialServiceTests(unittest.TestCase):
    def test_filename_is_reduced_to_metadata_only_basename(self):
        filename, file_type = sanitize_original_filename(
            r"..\course\实验一指导书.MD"
        )

        self.assertEqual(filename, "实验一指导书.MD")
        self.assertEqual(file_type, "md")

    def test_unsupported_extension_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "仅支持 PDF、DOCX、TXT 和 MD"):
            sanitize_original_filename("unsafe.exe")

    def test_storage_name_is_random_and_has_expected_extension(self):
        first = create_storage_name("pdf")
        second = create_storage_name("pdf")

        self.assertTrue(first.endswith(".pdf"))
        self.assertTrue(second.endswith(".pdf"))
        self.assertNotEqual(first, second)
        self.assertNotIn("/", first)
        self.assertNotIn("\\", first)


if __name__ == "__main__":
    unittest.main()
