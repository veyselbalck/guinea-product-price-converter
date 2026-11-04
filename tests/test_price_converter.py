from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from price_converter import calculate_prices, main


class CalculatePricesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.products = pd.DataFrame(
            {
                "category": ["Erkek Giyim", "Aksesuar"],
                "price_try": [1000, 1000],
            }
        )
        self.multipliers = {
            "erkek giyim": Decimal("3"),
            "aksesuar": Decimal("2.5"),
        }

    def test_converts_prices_and_applies_category_multipliers(self) -> None:
        result = calculate_prices(
            self.products,
            price_column="price_try",
            category_column="category",
            try_per_usd=Decimal("30"),
            gnf_per_usd=Decimal("9500"),
            category_multipliers=self.multipliers,
        )

        self.assertEqual(result["price_gnf"].tolist(), [950000, 791667])
        self.assertEqual(
            result["category_multiplier"].tolist(),
            [Decimal("3"), Decimal("2.5")],
        )
        self.assertEqual(self.products.columns.tolist(), ["category", "price_try"])

    def test_rejects_unmapped_categories(self) -> None:
        products = pd.DataFrame({"category": ["Shoes"], "price_try": [100]})

        with self.assertRaisesRegex(ValueError, "No multiplier is configured"):
            calculate_prices(
                products,
                price_column="price_try",
                category_column="category",
                try_per_usd=Decimal("30"),
                gnf_per_usd=Decimal("9500"),
                category_multipliers=self.multipliers,
            )

    def test_rejects_non_numeric_prices(self) -> None:
        products = pd.DataFrame({"category": ["Aksesuar"], "price_try": ["unknown"]})

        with self.assertRaisesRegex(ValueError, "must be a number"):
            calculate_prices(
                products,
                price_column="price_try",
                category_column="category",
                try_per_usd=Decimal("30"),
                gnf_per_usd=Decimal("9500"),
                category_multipliers=self.multipliers,
            )

    def test_rejects_missing_columns(self) -> None:
        with self.assertRaisesRegex(ValueError, "Missing required column"):
            calculate_prices(
                self.products,
                price_column="missing",
                category_column="category",
                try_per_usd=Decimal("30"),
                gnf_per_usd=Decimal("9500"),
                category_multipliers=self.multipliers,
            )

    def test_matches_turkish_category_case_insensitively(self) -> None:
        products = pd.DataFrame(
            {"category": ["KADIN GİYİM"], "price_try": [1000]}
        )

        result = calculate_prices(
            products,
            price_column="price_try",
            category_column="category",
            try_per_usd=Decimal("30"),
            gnf_per_usd=Decimal("9500"),
            category_multipliers={"kadın giyim": Decimal("3")},
        )

        self.assertEqual(int(result.loc[0, "price_gnf"]), 950000)


class CommandLineTests(unittest.TestCase):
    def test_processes_csv_and_writes_xlsx(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "products.csv"
            output_path = root / "priced.xlsx"
            input_path.write_text(
                "category,price_try\nErkek Giyim,1000\n",
                encoding="utf-8",
            )

            exit_code = main(
                [
                    str(input_path),
                    "--try-per-usd",
                    "30",
                    "--gnf-per-usd",
                    "9500",
                    "--output",
                    str(output_path),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.is_file())
            output = pd.read_excel(output_path, engine="openpyxl")
            self.assertEqual(int(output.loc[0, "price_gnf"]), 950000)

    def test_reads_selected_xlsx_sheet(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "products.xlsx"
            output_path = root / "priced.xlsx"
            with pd.ExcelWriter(input_path, engine="openpyxl") as writer:
                pd.DataFrame({"category": ["Aksesuar"], "price_try": [1000]}).to_excel(
                    writer, index=False, sheet_name="Products"
                )

            exit_code = main(
                [
                    str(input_path),
                    "--sheet",
                    "Products",
                    "--try-per-usd",
                    "30",
                    "--gnf-per-usd",
                    "9500",
                    "--output",
                    str(output_path),
                ]
            )

            self.assertEqual(exit_code, 0)
            output = pd.read_excel(output_path, engine="openpyxl")
            self.assertEqual(int(output.loc[0, "price_gnf"]), 791667)


if __name__ == "__main__":
    unittest.main()
