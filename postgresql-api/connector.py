import pandas as pd
import psycopg2
import os
import subprocess
import time
from pyspark.sql import SparkSession
from sqlalchemy import create_engine

class PostgreSQL:
    def __init__(self, connection_details, vpn_file_path, path_to_jars=None):
        '''
        Initializes the PostgreSQL class.

        - connection_details: Dictionary containing connection details for PostgreSQL, including 'host', 'port', 'database', 'user', and 'key'.
        - vpn_file_path: (Optional) Path to the VPN configuration file to be used for the connection. this will be using openvpn as vpn client.
        - path_to_jars: (Optional) Path to the JAR files required for Spark.
        '''
        self.postgres_spark_jars = path_to_jars
        self.vpn_file_path = vpn_file_path
        self.connection_details = connection_details

    #-- This will get the data from postgres and transform it to dataframe --#
    def fetch_data_from_postgres(self, sql_text, with_vpn=False):
        '''
        Fetches data from PostgreSQL and transforms it into a DataFrame.

        - sql_text: SQL text to be executed to fetch data.
        - with_vpn: Boolean indicating whether the VPN connection should be activated before fetching data.
        '''
        vpn_process = None
        try:
            if with_vpn:
                if os.name == 'posix':
                    shell = os.environ.get('SHELL', '')
                    if 'zsh' in shell:
                        vpn_process = subprocess.Popen(
                            ["zsh", "-c", '''source ~/.zshrc && sudo openvpn --config "''' + self.vpn_file_path + '''"'''],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                    elif 'bash' in shell:
                        vpn_process = subprocess.Popen(
                            ["bash", "-c", '''source ~/.bash_profile && sudo openvpn --config "''' + self.vpn_file_path + '''"'''],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                    else:
                        raise Exception("Shell not recognized.")
                elif os.name == 'nt':
                    vpn_process = subprocess.Popen(
                        ["runas", "/user:Administrator", "openvpn", "--config", self.vpn_file_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                else:
                    vpn_process = subprocess.Popen(
                        ["sudo", "openvpn", "--config", self.vpn_file_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                try:
                    if vpn_process.poll() is None:
                        print("Activating VPN...")
                except:
                    raise Exception("Failed to start VPN.")

                for i in range(30):
                    time.sleep(1)
                    try:
                        test_conn = psycopg2.connect(
                            host=self.connection_details['host'],
                            port=self.connection_details['port'],
                            database=self.connection_details['database'],
                            user=self.connection_details['user'],
                            password=self.connection_details['key'],
                            connect_timeout=2
                        )
                        test_conn.close()
                        print("VPN is now active!")
                        break
                    except Exception:
                        pass
                else:
                    raise Exception("VPN failed to connect within 30 seconds.")

            conn = psycopg2.connect(
                host=self.connection_details['host'],
                port=self.connection_details['port'],
                database=self.connection_details['database'],
                user=self.connection_details['user'],
                password=self.connection_details['key'],
                sslmode='require'
            )

            if conn:
                try:
                    cursor = conn.cursor()
                    cursor.execute(sql_text)
                    result = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    df_result = pd.DataFrame(result, columns=columns)
                    cursor.close()
                    conn.close()
                    if not df_result.empty:
                        print(f'Data fetched, {df_result.shape[0]:,} rows found.')
                    else:
                        print('No data found.')
                    return df_result
                except psycopg2.DatabaseError as err:
                    raise Exception(f"Database error: {err}")
                except Exception as err:
                    raise Exception(f"An error occurred: {err}")
            else:
                raise Exception('Connection to Database failed.')
        except Exception as err:
            raise Exception(f"Failed to connect to PostgreSQL, error: {err}")
        finally:
            if vpn_process:
                print("Script execution completed. Shutting down VPN...")
                vpn_process.terminate()
                print("VPN is now deactivated!")

    #-- This will run query from postgres using spark and return it to dataframe --#
    def run_query_from_postgres(self, query_text):
        '''
        Executes a query from PostgreSQL using Spark and returns it as a DataFrame.

        - query_text: SQL query text to be executed.
        '''
        try:
            spark = SparkSession.builder \
                .appName("PostgreSQL Data") \
                .config("spark.jars", self.postgres_spark_jars) \
                .config("spark.ui.enabled", "false") \
                .config("spark.driver.extraJavaOptions", "-XX:ReservedCodeCacheSize=256m") \
                .config("spark.executor.extraJavaOptions", "-XX:ReservedCodeCacheSize=256m") \
                .getOrCreate()

            url = f"jdbc:postgresql://{self.connection_details['host']}:{self.connection_details['port']}/{self.connection_details['database']}"
            properties = {
                "user": self.connection_details['user'],
                "password": self.connection_details['key'],
                "driver": "org.postgresql.Driver"
            }

            spark.sparkContext.setLogLevel("ERROR")
            
            df = spark.read.jdbc(url=url, table=f"({query_text}) AS query_table", properties=properties)

            df_result = df.toPandas() 
        except Exception as e:
            print(f"An error occurred while querying BigQuery: {e}")
        finally:
            spark.stop()

        return df_result
    
    #-- This will update table in postgres --#
    def update_table_postgres(self, df_data, destination_table_name, with_vpn=False):
        '''
        Updates a table in PostgreSQL with new data.

        - df_data: DataFrame containing new data to be written to the table.
        - destination_table_name: Name of the target table in PostgreSQL to be updated.
        - with_vpn: Boolean indicating whether the VPN connection should be activated before updating the table.
        '''
        vpn_process = None
        try:
            if with_vpn:
                if os.name == 'posix':
                    shell = os.environ.get('SHELL', '')
                    if 'zsh' in shell:
                        vpn_process = subprocess.Popen(
                            ["zsh", "-c", '''source ~/.zshrc && sudo openvpn --config "''' + self.vpn_file_path + '''"'''],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                    elif 'bash' in shell:
                        vpn_process = subprocess.Popen(
                            ["bash", "-c", '''source ~/.bash_profile && sudo openvpn --config "''' + self.vpn_file_path + '''"'''],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                    else:
                        raise Exception("Shell not recognized.")
                elif os.name == 'nt':
                    vpn_process = subprocess.Popen(
                        ["runas", "/user:Administrator", "openvpn", "--config", self.vpn_file_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                else:
                    vpn_process = subprocess.Popen(
                        ["sudo", "openvpn", "--config", self.vpn_file_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                try:
                    if vpn_process.poll() is None:
                        print("Activating VPN...")
                except:
                    raise Exception("Failed to start VPN.")

                for i in range(30):
                    time.sleep(1)
                    try:
                        test_conn = psycopg2.connect(
                            host=self.connection_details['host'],
                            port=self.connection_details['port'],
                            database=self.connection_details['database'],
                            user=self.connection_details['user'],
                            password=self.connection_details['key'],
                            connect_timeout=2
                        )
                        test_conn.close()
                        print("VPN is now active!")
                        break
                    except Exception:
                        pass
                else:
                    raise Exception("VPN failed to connect within 30 seconds.")
            
            conn = psycopg2.connect(
                host=self.connection_details['host'],
                port=self.connection_details['port'],
                database=self.connection_details['database'],
                user=self.connection_details['user'],
                password=self.connection_details['key'],
                sslmode='require'
            )

            if conn:
                try:
                    cursor = conn.cursor()
                    print('Dropping Old Data...')
                    command_text = f'''
                        DELETE FROM {destination_table_name}
                    '''
                    cursor.execute(command_text)
                    conn.commit()
                    cursor.close()
                    conn.close()
                    try:
                        print(f'Writing new data to table {destination_table_name} in PostgreSQL...')
                        engine = create_engine(f"postgresql+psycopg2://{self.connection_details['user']}:{self.connection_details['key']}@{self.connection_details['host']}:{self.connection_details['port']}/{self.connection_details['database']}")
                        df_data.to_sql(destination_table_name, engine, if_exists='append', index=False)
                        print(f'New data successfully written to table {destination_table_name} in PostgreSQL. {df_data.shape[0]:,} rows affected.')
                    except Exception as err:
                        raise Exception(err)
                except psycopg2.DatabaseError as err:
                    raise Exception(err)
                except Exception as err:
                    raise Exception(err)
            else:
                raise Exception('Connection to Database failed.')
        except Exception as err:
            raise Exception(f"Failed to connect to PostgreSQL, error: {err}")
        finally:
            if vpn_process:
                print("Script execution completed. Shutting down VPN...")
                vpn_process.terminate()
                print("VPN is now deactivated!")
