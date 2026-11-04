# Guinea Product Price Converter

A command-line tool that converts product prices from Turkish lira (TRY) to Guinean francs (GNF) using exchange rates and category multipliers you provide.

## Requirements

- Python 3
- A UTF-8 CSV file or an `.xlsx` workbook

## Installation

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Input format

The input must contain a header row and these columns by default:

| Column | Description |
|---|---|
| `category` | Product category |
| `price_try` | Numeric product price in TRY |

The tool accepts UTF-8 CSV and `.xlsx` files. For an Excel workbook, it reads the first worksheet unless you specify one. Convert `.xls` files to `.xlsx` before processing.

## Usage

```powershell
python price_converter.py products.xlsx `
  --try-per-usd 30 `
  --gnf-per-usd 9500 `
  --sheet "Products" `
  --output products_gnf.xlsx
```

Both exchange rates are required:

- `--try-per-usd`: TRY for 1 USD
- `--gnf-per-usd`: GNF for 1 USD

The example rates are for illustration only; they are not current-rate recommendations. The tool does not fetch or verify exchange rates.

By default, the clothing categories `erkek giyim`, `kadın giyim`, and `çocuk giyim` use a multiplier of `3`; `aksesuar` uses `2.5`. Category matching is case-insensitive and requires an exact name. Prices are calculated as:

```text
GNF price = (TRY price / TRY per USD) * GNF per USD * category multiplier
```

The result is rounded to the nearest whole GNF. To use different column names, pass `--category-column` and `--price-column`. To configure categories and multipliers, use options such as:

```powershell
python price_converter.py products.csv `
  --try-per-usd 30 `
  --gnf-per-usd 9500 `
  --clothing-categories "Men's clothing,Women's clothing" `
  --clothing-multiplier 3 `
  --accessory-categories "Accessories" `
  --accessory-multiplier 2.5 `
  --category-multiplier "Shoes=2"
```

Unmapped categories cause an error rather than producing a price. The source file is not modified. The output is an `.xlsx` file; by default it is written next to the input with `_gnf` appended to its name. Use `--output` to choose another path. If the output already exists, pass `--overwrite` to replace it.

The output includes the input columns plus `price_gnf`, `category_multiplier`, `try_per_usd`, and `gnf_per_usd`. For Excel input, only the selected worksheet's cell values are processed; source formatting, formulas, and other worksheets are not carried over.

## Tests

```powershell
python -m unittest discover -s tests -v
```

---

# Gine Ürün Fiyat Dönüştürücü

Kullanıcının sağladığı döviz kurları ve kategori çarpanlarıyla ürün fiyatlarını Türk lirasından (TRY) Gine frangına (GNF) dönüştüren bir komut satırı aracıdır.

## Gereksinimler

- Python 3
- UTF-8 kodlamalı bir CSV dosyası veya `.xlsx` çalışma kitabı

## Kurulum

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Girdi biçimi

Girdi dosyasında bir başlık satırı ve varsayılan olarak aşağıdaki sütunlar bulunmalıdır:

| Sütun | Açıklama |
|---|---|
| `category` | Ürün kategorisi |
| `price_try` | TRY cinsinden sayısal ürün fiyatı |

Araç UTF-8 CSV ve `.xlsx` dosyalarını kabul eder. Excel çalışma kitabında sayfa belirtilmezse ilk sayfa okunur. `.xls` dosyalarını işlemden önce `.xlsx` biçimine dönüştürün.

## Kullanım

```powershell
python price_converter.py products.xlsx `
  --try-per-usd 30 `
  --gnf-per-usd 9500 `
  --sheet "Products" `
  --output products_gnf.xlsx
```

İki döviz kurunun da girilmesi gerekir:

- `--try-per-usd`: 1 USD karşılığı TRY
- `--gnf-per-usd`: 1 USD karşılığı GNF

Örnek kur değerleri yalnızca kullanım örneğidir; güncel kur önerisi değildir. Araç internetten kur almaz ve girilen kurları doğrulamaz.

Varsayılan olarak `erkek giyim`, `kadın giyim` ve `çocuk giyim` kategorilerinde `3`; `aksesuar` kategorisinde `2.5` çarpanı kullanılır. Kategori eşleştirmesi büyük/küçük harfe duyarsızdır ve tam ad gerektirir. Fiyat şu formülle hesaplanır:

```text
GNF fiyatı = (TRY fiyatı / USD başına TRY) * USD başına GNF * kategori çarpanı
```

Sonuç en yakın tam GNF değerine yuvarlanır. Sütun adları farklıysa `--category-column` ve `--price-column` seçeneklerini kullanın. Kategori ve çarpanları değiştirmek için aşağıdaki gibi seçenekler verin:

```powershell
python price_converter.py products.csv `
  --try-per-usd 30 `
  --gnf-per-usd 9500 `
  --clothing-categories "Men's clothing,Women's clothing" `
  --clothing-multiplier 3 `
  --accessory-categories "Accessories" `
  --accessory-multiplier 2.5 `
  --category-multiplier "Shoes=2"
```

Eşleştirilmemiş kategorilerde fiyat üretmek yerine hata verilir. Kaynak dosya değiştirilmez. Çıktı `.xlsx` biçimindedir ve varsayılan olarak kaynak dosyanın yanına, adına `_gnf` eklenerek kaydedilir. Başka bir yol belirlemek için `--output` kullanın. Çıktı dosyası zaten varsa üzerine yazmak için `--overwrite` seçeneğini ekleyin.

Çıktıda girdi sütunlarına ek olarak `price_gnf`, `category_multiplier`, `try_per_usd` ve `gnf_per_usd` sütunları bulunur. Excel girdisinde yalnızca seçilen sayfanın hücre değerleri işlenir; kaynak biçimlendirmesi, formüller ve diğer çalışma sayfaları çıktıya aktarılmaz.

## Testler

```powershell
python -m unittest discover -s tests -v
```
