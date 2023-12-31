from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from pyspark.sql.types import StructType, StructField, StringType, TimestampType
from kafka import KafkaProducer
import requests
import pandas as pd
from bs4 import BeautifulSoup
from configparser import ConfigParser
import datetime
import json
from elasticsearch import Elasticsearch

config = ConfigParser()
config.read('config.conf')

bootstrap_servers = config.get('kafka_producer', 'bootstrap_servers')
topic = config.get('kafka_producer', 'topic')
postgres_connection_string = config.get('postgres_db', 'postgres_connection_string')
table = config.get('postgres_db', 'dbtable')
driver = config.get('postgres_db', 'driver')
elastic_search = config.get('elasticsearch', 'elasticsearchurl')
bucket_name = config.get('aws_bucket', 'bucket_name')

producer = KafkaProducer(bootstrap_servers=bootstrap_servers)
topic = topic


# get the data from website.send to the kafka consumer using kafka producer.
def scrape_website(url):
    # Send a GET request to the URL
    response = requests.get(url)
    response.raise_for_status()
    combined_record = []

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')
    # Extract the required data from the parsed HTML
    # Modify this part according to your specific requirements
    row_key = soup.find('span', {'class': 'row-key'}).get_text()
    user_id = soup.find('span', {'class': 'user-id'}).get_text()
    timestamp = soup.find('span', {'class': 'timestamp'}).get_text()
    click_url = soup.find('span', {'class': 'click-url'}).get_text()
    country = soup.find('span', {'class': 'country'}).get_text()
    city = soup.find('span', {'class': 'city'}).get_text()
    browser = soup.find('span', {'class': 'browser'}).get_text()
    operating_system = soup.find('span', {'class': 'operating-system'}).get_text()
    device = soup.find('span', {'class': 'device'}).get_text()
    combined_record.append([row_key, user_id, timestamp, click_url, country, city, browser, operating_system, device])
    columns = [row_key, user_id, timestamp, click_url, country, city, browser, operating_system, device]
    df = pd.DataFrame(columns=columns, data=combined_record)
    current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Convert data frame to JSON string
    json_export = df.to_json(orient='records')
    return json.loads(json_export)

    # return {#'row_key': row_key,
    #   'user_id': user_id,
    #   'timestamp': timestamp,
    #   'click_url': click_url,
    #   'country': country,
    #   'city': city
    #   'browser': browser,
    #   'operating_system': operating_system,
    #   'device': device
    # }

    # read the data send to consumer


def kafka_send_data(data):
    # Convert the data to bytes
    message = str(data).encode('utf-8')
    # Send the data to the Kafka topic
    producer.send(topic, message)


producer.flush()

# receive the data from consumer. read that data and store it into postgres rdbms.# calculating the number of clicks, unique users, and average time spent on each URL by users from each country.
'''https://repo1.maven.org/maven2/org/apache/spark/spark-streaming-kafka_2.11/1.6.3/spark-streaming-kafka_2.11-1.6.3.jarbefore processing the place above dependencies in spark/jars folders'''


def process_data():
    spark = SparkSession.builder.getOrCreate()
    postgres_df = spark.read.format("jdbc").option("url", postgres_connection_string) \
        .option("dbtable", table).option('driver', driver).load()
    # Perform data processing using Spark DataFrame operations
    processed_df = postgres_df.groupBy("url", "country") \
        .agg({"url": "count", "user_id": "count", "timestamp": "avg"}) \
        .withColumnRenamed("count(url)", "click_count") \
        .withColumnRenamed("count(user_id)", "unique_users") \
        .withColumnRenamed("avg(timestamp)", "average_time")

    # Write the processed data to S3
    s3_output_path = "s3://{}/processed_data".format(bucket_name)
    processed_df.write.mode("overwrite").parquet(s3_output_path)
    return processed_df


def elastic_index(elastic_search):
    # Index the processed data in Elasticsearch
    # Connect to Elasticsearch
    es = Elasticsearch([elastic_search])
    # Define the Elasticsearch index name
    index_name = 'processed_clickstream_data'
    for item in process_data():
        index_columns = {'url': item['url'],
                         'country': item['country'],
                         'clicks': item['clicks']
                         }
        # Index the document
        es.index(index=index_name, body=index_columns)
        # Close the Elasticsearch connection
    es.close()
    return


def main():
    scrape_website('https://www.amazon.in/')


if __name__ == '__main__':
    main()
