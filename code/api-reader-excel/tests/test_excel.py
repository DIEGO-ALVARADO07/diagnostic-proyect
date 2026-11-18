import io
import unittest
import zipfile

import fastexcel

from excel_provider.service import SheetSelectionError, read_first_sheet


def make_workbook() -> bytes:
    files = {
        "[Content_Types].xml": (
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/worksheets/sheet2.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            "</Types>"
        ),
        "_rels/.rels": (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/>'
            "</Relationships>"
        ),
        "xl/workbook.xml": (
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            "<sheets><sheet name=\"First\" sheetId=\"1\" r:id=\"rId1\"/>"
            "<sheet name=\"Second\" sheetId=\"2\" r:id=\"rId2\"/></sheets>"
            "</workbook>"
        ),
        "xl/_rels/workbook.xml.rels": (
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet2.xml"/>'
            "</Relationships>"
        ),
        "xl/worksheets/sheet1.xml": (
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<dimension ref="A1:A2"/><sheetData>'
            '<row r="1"><c r="A1" t="inlineStr"><is><t>value</t></is></c></row>'
            '<row r="2"><c r="A2"><v>101</v></c></row>'
            "</sheetData></worksheet>"
        ),
        "xl/worksheets/sheet2.xml": (
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<dimension ref="A1:A2"/><sheetData>'
            '<row r="1"><c r="A1" t="inlineStr"><is><t>value</t></is></c></row>'
            '<row r="2"><c r="A2"><v>202</v></c></row>'
            "</sheetData></worksheet>"
        ),
    }
    workbook = io.BytesIO()
    with zipfile.ZipFile(workbook, "w") as archive:
        for path, content in files.items():
            archive.writestr(path, content)
    return workbook.getvalue()


class ExcelServiceTests(unittest.TestCase):
    def test_reads_first_sheet_and_reports_its_rows(self) -> None:
        result = read_first_sheet(make_workbook(), "scores.xlsx")

        self.assertEqual(result["available_sheets"], ["First", "Second"])
        self.assertEqual(result["sheet_read"], "First")
        self.assertEqual(result["data"], [{"value": 101.0}])
        self.assertEqual(result["total_rows"], 1)

    def test_reads_the_sheet_selected_by_name(self) -> None:
        result = read_first_sheet(make_workbook(), "scores.xlsx", "Second")

        self.assertEqual(result["sheet_read"], "Second")
        self.assertEqual(result["data"], [{"value": 202.0}])

    def test_rejects_a_sheet_name_not_in_the_workbook(self) -> None:
        with self.assertRaises(SheetSelectionError) as error:
            read_first_sheet(make_workbook(), "scores.xlsx", "Missing")

        self.assertEqual(error.exception.available_sheets, ["First", "Second"])

    def test_rejects_invalid_workbook(self) -> None:
        with self.assertRaises(fastexcel.FastExcelError):
            read_first_sheet(b"not an Excel file", "scores.xlsx")
