from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from pyspark.sql.types import StructType, StructField, StringType, TimestampType
from kafka import KafkaConsumer
from aidetic_assesment_producer import topic,bootstrap_servers,postgres_connection_string,driver,table


def ingest_data_from_kafka(topic):
    consumer = KafkaConsumer(topic, bootstrap_servers=bootstrap_servers)
    spark = SparkSession.builder.getOrCreate()
    clickstream_schema = StructType([StructField("row_key", StringType(), nullable=False),
                                     StructField("user_id", StringType(), nullable=False),
                                     StructField("timestamp", TimestampType(), nullable=False),
                                     StructField("click_url", StringType(), nullable=False),
                                     StructField("country", StringType(), nullable=False),
                                     StructField("city", StringType(), nullable=False),
                                     StructField("browser", StringType(), nullable=False),
                                     StructField("os", StringType(), nullable=False),
                                     StructField("device", StringType(), nullable=False)
                                     ])
    while True:
        for msg in consumer:
            value = msg.value.decode("utf-8")
            clickstream_data = value.split(",")
            row_key = clickstream_data[0]
            user_id = clickstream_data[1]
            timestamp = clickstream_data[2]
            url = clickstream_data[3]
            country = clickstream_data[4]
            city = clickstream_data[5]
            browser = clickstream_data[6]
            os = clickstream_data[7]
            device = clickstream_data[8]
            # Storing the fetch data from kafka and store it into Postgres RDBMS.
            clickstream_df = spark.createDataFrame([(row_key, user_id, timestamp, url, country, city, browser, os, device)],schema=clickstream_schema)
            clickstream_df.write.format("jdbc").option("url", postgres_connection_string) \
                .option("dbtable", table).option('driver',driver).mode("append").save()

def main():
    topic = 'clickstream_data'
    print("starting consumer: ", topic)
    ingest_data_from_kafka(topic)

main()
