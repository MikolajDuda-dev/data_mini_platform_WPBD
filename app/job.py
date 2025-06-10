import findspark
findspark.init()

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, FloatType, LongType # Usunięto DateType, bo 'order_date' jest stringiem

# Initialize Spark Session
spark = SparkSession.builder \
    .appName("KafkaToMinIODeltaLake") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# Define schemas for each table based on the expected JSON structure from Debezium
# (when schemas.enable=false, the 'value' column directly contains the row data)
customer_schema = StructType([
    StructField("id", IntegerType(), True),
    StructField("name", StringType(), True),
    StructField("email", StringType(), True)
])

product_schema = StructType([
    StructField("id", IntegerType(), True),
    StructField("product_name", StringType(), True),
    StructField("price", FloatType(), True)
])

order_schema = StructType([
    StructField("order_id", IntegerType(), True),
    StructField("customer_id", IntegerType(), True),
    StructField("product_id", IntegerType(), True),
    StructField("quantity", IntegerType(), True),
    StructField("order_date", StringType(), True) # Keep as StringType, as in data.csv
])

# Read from Kafka
kafka_options = {
    "kafka.bootstrap.servers": "kafka1:9092,kafka2:9092,kafka3:9092",
    "subscribePattern": "dbserver.public.(customers|products|orders)", # Subscribe to all relevant topics
    "startingOffsets": "earliest",
    "failOnDataLoss": "false" # Important for development
}

df_kafka = spark.readStream \
    .format("kafka") \
    .options(**kafka_options) \
    .load()

# Function to process each micro-batch
def process_data(df, epoch_id):
    if df.isEmpty():
        print(f"Batch {epoch_id}: No data to process.")
        return

    # To avoid re-computation and improve performance
    df.persist()

    # Process customers topic
    customers_stream = df.filter(col("topic") == "dbserver.public.customers") \
                         .select(from_json(col("value").cast("string"), customer_schema).alias("data")) \
                         .select(col("data.*")) \
                         .withColumn("processed_at", current_timestamp())

    if not customers_stream.isEmpty():
        print(f"Batch {epoch_id}: Processing {customers_stream.count()} customer records.")
        customers_stream.write \
            .format("delta") \
            .mode("append") \
            .save("s3a://spark-data/delta/customers")
        print(f"Batch {epoch_id}: Customer data written to MinIO Delta Lake.")

    # Process products topic
    products_stream = df.filter(col("topic") == "dbserver.public.products") \
                        .select(from_json(col("value").cast("string"), product_schema).alias("data")) \
                        .select(col("data.*")) \
                        .withColumn("processed_at", current_timestamp())

    if not products_stream.isEmpty():
        print(f"Batch {epoch_id}: Processing {products_stream.count()} product records.")
        products_stream.write \
            .format("delta") \
            .mode("append") \
            .save("s3a://spark-data/delta/products")
        print(f"Batch {epoch_id}: Product data written to MinIO Delta Lake.")

    # Process orders topic
    orders_stream = df.filter(col("topic") == "dbserver.public.orders") \
                      .select(from_json(col("value").cast("string"), order_schema).alias("data")) \
                      .select(col("data.*")) \
                      .withColumn("processed_at", current_timestamp())

    if not orders_stream.isEmpty():
        print(f"Batch {epoch_id}: Processing {orders_stream.count()} order records.")
        orders_stream.write \
            .format("delta") \
            .mode("append") \
            .save("s3a://spark-data/delta/orders")
        print(f"Batch {epoch_id}: Order data written to MinIO Delta Lake.")

    df.unpersist() # Unpersist after processing

# Start the streaming query
query = df_kafka.writeStream \
    .foreachBatch(process_data) \
    .outputMode("append") \
    .trigger(processingTime="10 seconds") \
    .option("checkpointLocation", "/opt/spark-jobs/checkpoints/main_stream_orchestrator") \
    .start()

query.awaitTermination()