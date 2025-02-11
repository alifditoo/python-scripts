import pandas as pd
import datetime
import os
import time
import threading
import psutil
import queue

from google.cloud import bigquery
from google.oauth2 import service_account
from pyspark.sql import SparkSession

class BigQuery:
    def __init__(self, service_account_path):
        '''
        Initializes the BigQuery client with the provided service account path.

        Parameters:
        service_account_path (str): The file path to the service account JSON file.
        '''
        self.service_account_path = service_account_path
        self.client = bigquery.Client.from_service_account_json(json_credentials_path=self.service_account_path)
        self.credentials = service_account.Credentials.from_service_account_file(self.service_account_path)

    #-- This will get the latest created/updated date in database --#
    def getBQLastDate(self, table_name, column_parameter, date_format='%Y-%m-%d'):
        '''
        Retrieves the latest created or updated date from a specified column in a BigQuery table.

        Parameters:
        table_name (str): The name of the BigQuery table to query.
        column_parameter (str): The column from which to retrieve the maximum date.
        date_format (str): The format to return the date in (default is '%Y-%m-%d').

        Returns:
        datetime: The latest date found in the specified column, or an empty string if no date is found.
        '''
        job_config = bigquery.QueryJobConfig()
        job_config.use_legacy_sql = True
        query = (r'''
            SELECT MAX({column}) FROM [{project}.{dataset}.{table}]''').format(project=self.bq_metadata['project_id'], dataset=self.bq_metadata['dataset_name'], table=table_name, column=column_parameter)
        job = self.client.query(query, job_config=job_config)
        try:
            return datetime.datetime.strptime((job.to_dataframe().values[0][0])[:10], date_format)
        except TypeError:
            return ''

    #-- This will apply append/overwrite table in bigquery --#
    def updateTableBQ(self, query, destination_table, dataset_name=None, write_disposition='WRITE_APPEND', create_disposition='CREATE_IF_NEEDED', legacy_sql=True):
        '''
        Updates a BigQuery table by executing a query with specified write and create dispositions.

        Parameters:
        query (str): The SQL query to execute.
        destination_table (str): The destination table to update.
        dataset_name (str, optional): The dataset name where the table resides. Defaults to None.
        write_disposition (str): Specifies the action to take on the destination table (default is 'WRITE_APPEND').
        create_disposition (str): Specifies the action to take if the table does not exist (default is 'CREATE_IF_NEEDED').
        legacy_sql (bool): Whether to use legacy SQL syntax (default is True).

        Returns:
        job: The job object representing the query execution.
        '''
        if dataset_name is None:
            dataset_name = self.bq_metadata['dataset_name']
        job_config = bigquery.QueryJobConfig()
        destination_dataset = self.client.dataset(dataset_name)
        destination_table = destination_dataset.table(destination_table)
        job_config.destination = destination_table
        job_config.use_legacy_sql = legacy_sql
        job_config.create_disposition = create_disposition
        job_config.write_disposition = write_disposition
        job = self.client.query(query, job_config=job_config)
        job.result()
        return job
    
    #-- This will insert dataframe to bigquery --#
    def insert_dataframe_to_bigquery(self, df, destination_table, write_disposition='WRITE_TRUNCATE'):
        '''
        Inserts a pandas DataFrame into a specified BigQuery table.

        Parameters:
        df (DataFrame): The DataFrame containing the data to insert.
        destination_table (str): The destination table where the data will be inserted.
        write_disposition (str): Specifies the action to take on the destination table (default is 'WRITE_TRUNCATE').

        Returns:
        bool: Returns True if the data is successfully inserted; raises an exception if there is no data to insert.
        '''
        if not df.empty:
            job_config = bigquery.LoadJobConfig(
                write_disposition=write_disposition
            )
            print(f'Inserting data into {destination_table} table..')
            job = self.client.load_table_from_dataframe(df, destination_table, job_config=job_config)
            job.result()
            print(f'''{'{:,}'.format(job.output_rows)} rows inserted into {destination_table}.''')
            return True
        else:
            raise Exception(f'No data to insert into {destination_table}.')

        
    #- This will run query in BigQuery then return it to dataframe -#
    def BigQueryToDF(self, query_text, print_update=False):
        '''
        Executes a query in BigQuery and returns the result as a pandas DataFrame.

        Parameters:
        query_text (str): The SQL query to execute.
        print_update (bool): Whether to print updates during the execution (default is False).

        Returns:
        DataFrame: The result of the query as a pandas DataFrame.
        '''
        if print_update:
            print('Setting up BigQuery...')
        job_config = bigquery.QueryJobConfig()
        job_config.use_legacy_sql = False
        job_config.maximum_bytes_billed = 2 * 1024 * 1024 * 1024  # 2GB
        job_config.allow_large_results = True
        
        if print_update:
            print('Start Query...')
        job = self.client.query(query_text, job_config=job_config)
        
        if print_update:
            print('Fetching Data...')
        df_result = job.result().to_dataframe()
        
        if print_update:
            print(f'Data Fetched. Rows found: {df_result.shape[0]:,}')
        return df_result

    #- This will run query in BigQuery using spark -#
    def BigQuery_Spark(self, query_text, project_id, dataset_name, table_name):
        '''
        Executes a query in BigQuery using Spark and returns the result as a pandas DataFrame.

        Parameters:
        query_text (str): The SQL query to execute.
        project_id (str): The Google Cloud project ID.
        dataset_name (str): The dataset name where the table resides.
        table_name (str): The name of the table to query.

        Returns:
        DataFrame: The result of the query as a pandas DataFrame, or [None] if an error occurs.
        '''
        jar_file = os.path.join(os.getcwd(), 'spark-bigquery-with-dependencies_2.12-0.41.1.jar')
        spark = SparkSession.builder \
                .appName("BigQuerySparkApp") \
                .config("spark.sql.catalogImplementation", "hive") \
                .config("spark.ui.enabled", "false") \
                .config("spark.sql.catalogImplementation", "in-memory") \
                .config("spark.bigquery.project", self.bq_metadata['project_id']) \
                .config("spark.jars", jar_file) \
                .config("spark.bigquery.credentialsFile", self.service_account_path) \
                .config("spark.driver.extraJavaOptions", "-XX:ReservedCodeCacheSize=256m") \
                .config("spark.executor.extraJavaOptions", "-XX:ReservedCodeCacheSize=256m") \
                .getOrCreate()

        spark.sparkContext.setLogLevel("ERROR")

        try:
            spark.sql(f'''
                CREATE OR REPLACE TEMPORARY VIEW bigquery_view
                USING bigquery
                OPTIONS (
                    table '{project_id}.{dataset_name}.{table_name}'
                )          
            ''')

            df = spark.sql(query_text)
            df_result = df.toPandas()
            return df_result
        except Exception as e:
            print(f"An error occurred while querying BigQuery: {e}")
            return [None]
        finally:
            spark.stop()

    #-- This will execute query with timeout --#
    def execute_query_with_timeout(self, query, timeout_minutes=10, is_print_update=False):
        '''
        Executes a query with a specified timeout and monitors memory usage.

        Parameters:
        query (str): The SQL query to execute.
        timeout_minutes (int): The maximum time in minutes to allow for the query execution (default is 10).
        is_print_update (bool): Whether to print updates during the execution (default is False).

        Returns:
        result: The result of the query execution.
        '''
        timeout_seconds = timeout_minutes * 60
        stop_monitoring = threading.Event()
        start_time = time.time()

        def run_query(query_text, result_queue):
            temp_data = self.BigQueryToDF(query_text)
            result_queue.put(temp_data)
        
        def monitor_memory():
            while not stop_monitoring.is_set():
                memory_used = psutil.Process().memory_info().rss / (1024 * 1024)
                elapsed_time = time.time() - start_time
                
                hours = int(elapsed_time // 3600)
                minutes = int((elapsed_time % 3600) // 60)
                seconds = int(elapsed_time % 60)

                if hours > 0:
                    elapsed_time_str = f"{hours} Hours {minutes} Minutes {seconds} Seconds"
                elif minutes > 0:
                    elapsed_time_str = f"{minutes} Minutes {seconds} Seconds"
                else:
                    elapsed_time_str = f"{seconds} Seconds"

                print(f"Memory used: {memory_used:.2f} MB, Elapsed time: {elapsed_time_str}", end='\r')
                time.sleep(1)

        result_queue = queue.Queue()

        query_thread = threading.Thread(target=run_query, args=(query, result_queue))
        monitor_thread = threading.Thread(target=monitor_memory, daemon=True)
        
        try:
            monitor_thread.start()
            query_thread.start()
            
            query_thread.join(timeout=timeout_seconds)
            
            if query_thread.is_alive():
                TimeOutText = f'Query execution timed out after {timeout_minutes} minutes.'
                raise Exception(TimeOutText)
            else:
                return result_queue.get()
        except Exception as e:
            errorText = f'Error executing query: {str(e)}'
            raise Exception(errorText)
        finally:
            stop_monitoring.set()
            query_thread.join(timeout=1)
            if monitor_thread.is_alive():
                monitor_thread.join(timeout=1)