# Tokopedia Scrapper
This folder contains scripts and modules used for data mining, specifically for retrieving detailed data based on product details from Tokopedia. The scripts in this folder are designed to facilitate data extraction from Tokopedia. By using this folder, users can quickly integrate Tokopedia functionality into their Python projects, thereby enhancing efficiency and productivity in data science and analysis. *The search parameter is by keyword, which will perform a keyword search in the Tokopedia search box.*

## Features
- Automatically retrieve product information from Tokopedia.
- Supports various product categories.
- Saves the extracted data in an easily usable format.

## Sample Result
| Keyword      | Title          | Variant     | Rating | Price   | Sold | Description      | Item Condition | Shop Name  | Store Location | Product Site | Updated At          |
|--------------|----------------|-------------|--------|---------|------|------------------|----------------|------------|----------------|---------------|----------------------|
| product_keyword | product_title | variant_selected_if_any | product_rating | product_price | product_sold_count | product_description | new_or_secondhand | shop_name | shop_location | product_link | updated_at |

## How to Use
1. Make sure you have **Python** installed on your system.
2. Install the required packages by running the following command:
   ```
   pip install pandas selenium beautifulsoup4 requests
   ```
3. Modify the `list_of_products` variable in the `main_pull.py` script to include the product names you want to search for. For example:
   ```python
   list_of_products = ['product1', 'product2']
   ```
4. Execute the script by running:
   ```
   python main_pull.py
   ```
5. The data will be saved in the specified file format, such as CSV or XLSX, as defined by modifying the `save_to_file` function, which only supports CSV and XLSX formats.

## Contribution
Contributions are welcome! Please **create a pull request** or **open an issue** if you have suggestions or improvements.

## License
This project is licensed under the MIT License.