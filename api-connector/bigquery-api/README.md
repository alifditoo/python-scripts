
# BigQuery Connector

The `bigquery-connector.py` script is designed to facilitate seamless interaction with Google BigQuery, making it an essential tool for data scientists and engineers who need to manage and analyze large datasets efficiently. This script leverages the `google-cloud-bigquery` library, providing a robust interface for executing queries, retrieving data, and updating tables in BigQuery.

## Key Features

### 1. Initialization
The script allows users to initialize a BigQuery client using a service account JSON file, ensuring secure access to BigQuery resources.

### 2. Date Retrieval
Users can retrieve the latest created or updated date from a specified column in a BigQuery table, which is crucial for tracking data changes over time.

### 3. Table Updates
The script provides functionality to update BigQuery tables by executing SQL queries with customizable write and create dispositions, allowing for flexible data management.

### 4. Data Insertion
Users can insert data from a Pandas DataFrame into BigQuery tables, making it easy to transfer data from local environments to the cloud.

## How to Use
1. **Install Dependencies**: Ensure you have the `google-cloud-bigquery` library installed. You can install it using pip:
   ```bash
   pip install google-cloud-bigquery
   ```

2. **Set Up Service Account**: Obtain a service account JSON file from the Google Cloud Console and save it in your project directory.

3. **Create an Instance**: Instantiate the `BigQuery` class with your service account path:
   ```python
   bigquery_client = BigQuery('path/to/service_account.json')
   ```

4. **Retrieve Latest Date**: Use the `getBQLastDate` method to get the latest date from a specific table:
   ```python
   last_date = bigquery_client.getBQLastDate('your_table_name', 'your_date_column')
   ```

5. **Update Table**: Execute a query to update a BigQuery table:
   ```python
   query = "YOUR SQL QUERY"
   bigquery_client.updateTableBQ(query, 'your_destination_table')
   ```

6. **Insert DataFrame**: Insert a Pandas DataFrame into a BigQuery table:
   ```python
   bigquery_client.insert_dataframe_to_bigquery(your_dataframe, 'your_destination_table')
   ```

## Example Output
The output of the `getBQLastDate` method will return the latest date found in the specified column, while the `updateTableBQ` method will execute the provided SQL query and update the specified table accordingly.

## Conclusion
In summary, `bigquery-connector.py` is a powerful tool for data professionals looking to integrate Google BigQuery functionalities into their data workflows. It simplifies the process of managing and analyzing large datasets, making it an invaluable resource for any data-driven project.

## License
This project is licensed under the MIT License, allowing for free use and modification of the code, provided that proper credit is given to the original authors.




