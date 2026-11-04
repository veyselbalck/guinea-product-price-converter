from __future__ import annotations

import argparse
import sys
import unicodedata
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Mapping, Sequence

import pandas as pd


DEFAULT_CLOTHING_CATEGORIES = ("erkek giyim", "kadın giyim", "çocuk giyim")
DEFAULT_ACCESSORY_CATEGORIES = ("aksesuar",)
PRICE_OUTPUT_COLUMN = "price_gnf"
MULTIPLIER_OUTPUT_COLUMN = "category_multiplier"
TRY_RATE_OUTPUT_COLUMN = "try_per_usd"
GNF_RATE_OUTPUT_COLUMN = "gnf_per_usd"


def _normalize_category(category: str) -> str:
    normalized = unicodedata.normalize("NFKC", category).translate(
        str.maketrans({"I": "ı", "İ": "i"})
    )
    return normalized.strip().casefold()


def _parse_positive_decimal(value: str) -> Decimal:
    try:
        number = Decimal(value)
    except InvalidOperation as error:
        raise argparse.ArgumentTypeError("Enter a valid decimal number.") from error
    if not number.is_finite() or number <= 0:
        raise argparse.ArgumentTypeError("Value must be a finite number greater than zero.")
    return number


def _to_decimal(value: object, *, field: str, row_number: int) -> Decimal:
    if pd.isna(value):
        raise ValueError(f"{field} is empty at data row {row_number}.")
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as error:
        raise ValueError(
            f"{field} must be a number at data row {row_number}; got {value!r}."
        ) from error
    if not number.is_finite() or number < 0:
        raise ValueError(
            f"{field} must be a finite, non-negative number at data row {row_number}."
        )
    return number


def calculate_prices(
    products: pd.DataFrame,
    *,
    price_column: str,
    category_column: str,
    try_per_usd: Decimal,
    gnf_per_usd: Decimal,
    category_multipliers: Mapping[str, Decimal],
) -> pd.DataFrame:
    if products.empty:
        raise ValueError("The selected input sheet has no product rows.")
    if price_column == category_column:
        raise ValueError("Price and category columns must be different.")

    missing_columns = [
        column
        for column in (price_column, category_column)
        if column not in products.columns
    ]
    if missing_columns:
        raise ValueError(
            "Missing required column(s): "
            + ", ".join(repr(column) for column in missing_columns)
            + ". Use --price-column and --category-column to select the right columns."
        )

    for rate_name, rate in (
        ("try_per_usd", try_per_usd),
        ("gnf_per_usd", gnf_per_usd),
    ):
        if not rate.is_finite() or rate <= 0:
            raise ValueError(f"{rate_name} must be a finite number greater than zero.")

    normalized_multipliers: dict[str, Decimal] = {}
    for category, multiplier in category_multipliers.items():
        normalized = _normalize_category(category)
        if not normalized:
            raise ValueError("Category names in the multiplier map cannot be empty.")
        if not multiplier.is_finite() or multiplier <= 0:
            raise ValueError(f"Multiplier for {category!r} must be greater than zero.")
        if normalized in normalized_multipliers:
            raise ValueError(f"Duplicate category mapping for {category!r}.")
        normalized_multipliers[normalized] = multiplier

    output_columns = {
        PRICE_OUTPUT_COLUMN,
        MULTIPLIER_OUTPUT_COLUMN,
        TRY_RATE_OUTPUT_COLUMN,
        GNF_RATE_OUTPUT_COLUMN,
    }
    collisions = output_columns.intersection(products.columns)
    if collisions:
        raise ValueError(
            "Input already contains output column(s): "
            + ", ".join(sorted(collisions))
            + ". Rename those columns before processing."
        )

    prices_gnf: list[int] = []
    applied_multipliers: list[Decimal] = []
    unknown_categories: set[str] = set()

    for row_number, (_, row) in enumerate(products.iterrows(), start=2):
        raw_category = row[category_column]
        if pd.isna(raw_category) or not str(raw_category).strip():
            raise ValueError(f"{category_column} is empty at data row {row_number}.")
        category = str(raw_category).strip()
        normalized_category = _normalize_category(category)
        if normalized_category not in normalized_multipliers:
            unknown_categories.add(category)
            continue

        price_try = _to_decimal(
            row[price_column], field=price_column, row_number=row_number
        )
        multiplier = normalized_multipliers[normalized_category]
        price_gnf = (
            price_try / try_per_usd * gnf_per_usd * multiplier
        ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        prices_gnf.append(int(price_gnf))
        applied_multipliers.append(multiplier)

    if unknown_categories:
        categories = ", ".join(repr(name) for name in sorted(unknown_categories))
        raise ValueError(
            f"No multiplier is configured for category/categories: {categories}. "
            "Add --category-multiplier 'CATEGORY=VALUE'."
        )

    result = products.copy()
    result[PRICE_OUTPUT_COLUMN] = prices_gnf
    result[MULTIPLIER_OUTPUT_COLUMN] = applied_multipliers
    result[TRY_RATE_OUTPUT_COLUMN] = try_per_usd
    result[GNF_RATE_OUTPUT_COLUMN] = gnf_per_usd
    return result


def _read_products(path: Path, sheet: str | None) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Input file does not exist: {path}")

    suffix = path.suffix.casefold()
    if suffix == ".csv":
        return pd.read_csv(path, encoding="utf-8-sig")
    if suffix == ".xlsx":
        return pd.read_excel(path, sheet_name=sheet or 0, engine="openpyxl")
    raise ValueError("Input must be a UTF-8 CSV or .xlsx file. Convert .xls to .xlsx first.")


def _add_category_mappings(
    mappings: dict[str, Decimal],
    categories: Sequence[str],
    multiplier: Decimal,
) -> None:
    for category in categories:
        normalized = _normalize_category(category)
        if not normalized:
            raise ValueError("Configured category names cannot be empty.")
        if normalized in mappings:
            raise ValueError(f"Category {category!r} is configured more than once.")
        mappings[normalized] = multiplier


def _category_multiplier_argument(value: str) -> tuple[str, Decimal]:
    category, separator, raw_multiplier = value.rpartition("=")
    if not separator or not category.strip():
        raise argparse.ArgumentTypeError("Use CATEGORY=MULTIPLIER.")
    try:
        multiplier = Decimal(raw_multiplier.strip())
    except InvalidOperation as error:
        raise argparse.ArgumentTypeError("Multiplier must be a valid number.") from error
    if not multiplier.is_finite() or multiplier <= 0:
        raise argparse.ArgumentTypeError("Multiplier must be greater than zero.")
    return category.strip(), multiplier


def _comma_separated_categories(value: str) -> tuple[str, ...]:
    categories = tuple(category.strip() for category in value.split(","))
    if not categories or any(not category for category in categories):
        raise argparse.ArgumentTypeError("Provide non-empty category names separated by commas.")
    return categories


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert product prices from TRY to GNF using explicit exchange rates."
    )
    parser.add_argument("input", type=Path, help="Input .xlsx or UTF-8 .csv file.")
    parser.add_argument("--output", type=Path, help="Output .xlsx path.")
    parser.add_argument("--sheet", help="Excel sheet name; defaults to the first sheet.")
    parser.add_argument("--price-column", default="price_try")
    parser.add_argument("--category-column", default="category")
    parser.add_argument("--try-per-usd", required=True, type=_parse_positive_decimal)
    parser.add_argument("--gnf-per-usd", required=True, type=_parse_positive_decimal)
    parser.add_argument(
        "--clothing-categories",
        type=_comma_separated_categories,
        default=DEFAULT_CLOTHING_CATEGORIES,
        help="Comma-separated categories that use the clothing multiplier.",
    )
    parser.add_argument(
        "--clothing-multiplier",
        type=_parse_positive_decimal,
        default=Decimal("3"),
    )
    parser.add_argument(
        "--accessory-categories",
        type=_comma_separated_categories,
        default=DEFAULT_ACCESSORY_CATEGORIES,
        help="Comma-separated categories that use the accessory multiplier.",
    )
    parser.add_argument(
        "--accessory-multiplier",
        type=_parse_positive_decimal,
        default=Decimal("2.5"),
    )
    parser.add_argument(
        "--category-multiplier",
        action="append",
        type=_category_multiplier_argument,
        default=[],
        metavar="CATEGORY=VALUE",
        help="Add an exact category mapping; can be repeated.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing output file.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    output = args.output or args.input.with_name(f"{args.input.stem}_gnf.xlsx")

    if args.input.resolve() == output.resolve():
        parser.error("Output path must not be the same as the input path.")
    if output.suffix.casefold() != ".xlsx":
        parser.error("Output path must have the .xlsx extension.")
    if output.exists() and not args.overwrite:
        parser.error(f"Output file already exists: {output}. Use --overwrite to replace it.")

    try:
        multipliers: dict[str, Decimal] = {}
        _add_category_mappings(
            multipliers, args.clothing_categories, args.clothing_multiplier
        )
        _add_category_mappings(
            multipliers, args.accessory_categories, args.accessory_multiplier
        )
        for category, multiplier in args.category_multiplier:
            multipliers[_normalize_category(category)] = multiplier

        products = _read_products(args.input, args.sheet)
        result = calculate_prices(
            products,
            price_column=args.price_column,
            category_column=args.category_column,
            try_per_usd=args.try_per_usd,
            gnf_per_usd=args.gnf_per_usd,
            category_multipliers=multipliers,
        )

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            result.to_excel(writer, index=False, sheet_name="Prices")
            worksheet = writer.sheets["Prices"]
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
            for column_name, number_format in (
                (PRICE_OUTPUT_COLUMN, "#,##0"),
                (MULTIPLIER_OUTPUT_COLUMN, "0.00"),
                (TRY_RATE_OUTPUT_COLUMN, "#,##0.0000"),
                (GNF_RATE_OUTPUT_COLUMN, "#,##0.00"),
            ):
                column_index = result.columns.get_loc(column_name) + 1
                for row in worksheet.iter_rows(
                    min_row=2, min_col=column_index, max_col=column_index
                ):
                    row[0].number_format = number_format

    except (FileNotFoundError, OSError, ValueError, pd.errors.ParserError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    print(f"Processed {len(result)} products. Output: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
