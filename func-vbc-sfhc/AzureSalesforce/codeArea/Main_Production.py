from pyspark.sql import Row
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from salesforce_bulk import SalesforceBulk, CsvDictsAdapter
import sys
import pandas as pd
import time
import json
from salesforce_bulk.util import IteratorBytesIO
import findspark
import os
import boto3
from botocore.exceptions import ClientError
import logging
#os.environ['SPARK_HOME']="C:\\Users\\Ashwini\\PycharmProjects\\pythonProject\\venv\\Lib\\site-packages\\pyspark"


def getAuditTime(spark,sqlsUrl,userName,password,logTable):
    query="select max(created_on_date) as max_created_on_date from {0}".format(logTable)
    data = [{'max_created_on_date': '1970-01-01 00:00:00.000'}]
    auditDate = spark.read.format('jdbc') \
        .option('url', sqlsUrl) \
        .option('driver', 'com.microsoft.sqlserver.jdbc.SQLServerDriver') \
        .option('query', query) \
        .option("user", userName) \
        .option("password", password) \
        .load().where("max_created_on_date is not null")
    if auditDate.count()>0:
        return auditDate
    else:
        return spark.createDataFrame(data)

def generaetLogFile(batchResults,sqlsUrl,sqlServerFailedTable,userName,password,spark):
    logResults=[]
    for b in batchResults:
        batchDict={}
        batchDict['id']=b.id
        batchDict['error'] = b.error
        batchDict['success'] = b.success
        logResults.append(batchDict)

    logDF=spark.createDataFrame(Row(**x) for x in logResults)
    if logDF.count()!=0:
        logging.info("Getting Failed Records")
        logDF.withColumn("log_timestamp",current_timestamp().cast('timestamp')).createOrReplaceTempView("logdf")
        rownumberlogdf=spark.sql("select *,row_number() over (order by log_timestamp) as row_num from logdf").where("success!='true'")
        recordCount=rownumberlogdf.count()
        if recordCount>0:
            rownumberjoindata=spark.sql("select patient_bk,Created_On_Date,row_number() over (order by created_on_date) as row_num from joindata")
            finalDF=rownumberlogdf.join(rownumberjoindata,rownumberlogdf.row_num==rownumberjoindata.row_num,"inner").selectExpr("Patient_BK","error as Error_Message","Created_On_Date")
            logging.info("Storing failed records in {0}".format(sqlServerFailedTable))
            finalDF.write.format("jdbc") \
            .mode("append") \
            .option("truncate", "True") \
            .option("url", sqlsUrl) \
            .option("dbtable", sqlServerFailedTable) \
            .option("user", userName) \
            .option("password", password) \
            .save()
            logging.info("Storing failed records in {0}: Finished".format(sqlServerFailedTable))
            sendMail(recordCount)

def sendMail(recordCount):
    # Replace sender@example.com with your "From" address.
    # This address must be verified with Amazon SES.
    SENDER = "ashwini@cloudnerd.com"

    # Replace recipient@example.com with a "To" address. If your account
    # is still in the sandbox, this address must be verified.
    RECIPIENT = "ashwini@cloudnerd.com"

    # If necessary, replace us-west-2 with the AWS Region you're using for Amazon SES.
    AWS_REGION = "us-east-2"

    # The subject line for the email.
    SUBJECT = "Sql Server to SalesForce Migration: Failed"

    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = ("There is the failure is performing migration\n Total Records Failed: {0} ".format(recordCount)
                 )

    # The HTML body of the email.
    BODY_HTML = """<html>
    <head></head>
    <body>
      <h1><center>CloudNerd</center></h1>
      <p><h3>There is a failure in performing migration</br></br></h3><h2>Total Records Failed: <b>{0}</b>.</h2></br><h3>Please Check VBC.[VBC_Extern].VBC_SFHC_P2P_IncrementalUpload_FailureLog table in Sql server for failed records</h3</p>
    </body>
    </html>
                """.format(recordCount)

    # The character encoding for the email.
    CHARSET = "UTF-8"

    #AWS AccessID
    ACCESS_ID="AKIA5I37AKA7LDV4XL4L"

    #AWS AccessKey
    ACCESS_KEY="3x3iTDo/+8sI4wwmOjciUAKY6ulmPriOzinENhcY"

    # Create a new SES resource and specify a region.
    client = boto3.client('ses', region_name=AWS_REGION,aws_access_key_id=ACCESS_ID,aws_secret_access_key=ACCESS_KEY)

    # Try to send the email.
    try:
        # Provide the contents of the email.
        response = client.send_email(
            Destination={
                'ToAddresses': [
                    RECIPIENT,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': CHARSET,
                        'Data': BODY_HTML,
                    },
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': SUBJECT,
                },
            },
            Source=SENDER
        )
    # Display an error if something goes wrong.
    except ClientError as e:
        logging.error(e.response['Error']['Message'])
    else:
        logging.info("Email sent! Message ID:"),

def checkEmptyString(st):
    if st and len(st)>0:
        return False
    else:
        return True

def mainFunction():
    logging.info('Started Main Production python File')
    try:
        logging.info("Reading Envionment Variables")
       # os.environ['SPARK_HOME']  
        userName = os.environ['sqluserName']  
        password = os.environ['sqlpassword']  
        salesforceUsername = os.environ['salesforceusername']  
        salesforcePassword = os.environ['salesforcepassword']  
        securityToken = os.environ['securitytoken']  
        sourceTablename = os.environ['sourcetablename']  
        targettablename = os.environ['targettablename']  
        sqljarpath = os.environ['sqljarpath'] 
        sqlurl = os.environ['sqlurl']  
        logtable = os.environ['logtable']  
        sqlserverfailedtable = os.environ['sqlserverfailedtable']  
        logging.info(" Envionment Variables Loaded")
    except Exception as ex:
        logging.error("Please specify all the mandatory arguments in enviornment file")
        logging.error(str(ex))
        raise ex

    if checkEmptyString(userName) and checkEmptyString(password) and checkEmptyString(salesforceUsername) and checkEmptyString(salesforcePassword) and checkEmptyString(securityToken) and checkEmptyString(sourceTablename) and checkEmptyString(targettablename) and checkEmptyString(sqljarpath) and checkEmptyString(sqlurl) and checkEmptyString(logtable) and checkEmptyString(sqlserversnapshottable) and checkEmptyString(sqlserverfailedtable):
        logging.error("Please check the arguments no arguments should be empty")
        sys.exit(-1)

    csvfile = pd.read_csv("codeArea/mappings.csv", header='infer')

    findspark.init()
    from datetime import datetime
    startTime = str(datetime.now())




    logging.info("Loading data from Sql Server Table {0} to SalesForce {1} : {2}".format(sourceTablename,targettablename,str(datetime.now())))
    logging.info("Log Table:{0}".format(logtable))


    #Spark Session Intailization
    spark = SparkSession \
        .builder \
        .master('local[*]') \
        .appName('Connection-Test') \
        .config('spark.sql.session.timezone','UTC') \
        .config('spark.driver.extraClassPath', sqljarpath) \
        .config('spark.executor.extraClassPath', sqljarpath) \
        .getOrCreate()

    logging.info("Spark Object Created")
    auditDateDF=getAuditTime(spark,sqlurl,userName, password,logtable)
    auditDateDF.createOrReplaceTempView('auditTable')
    auditDate=str(auditDateDF.select("max_created_on_date").collect()[0].max_created_on_date)
    auditDate = auditDate[0:23]


    auditDate = "2022-02-02 00:00:00.000"
    logging.info("Audit timestamp:"+str(auditDate))
    predicateQuery = "select * from {1} where (created_on_date >'{0}' or updated_on_date >'{0}')".format(auditDate, sourceTablename)
    logging.info(predicateQuery)
    i = 0
    colList = []
    dwColList=[]
    dataMap = {}
    listDataMap = []


    newData = spark.read.format('jdbc') \
        .option('url', sqlurl) \
        .option('driver', 'com.microsoft.sqlserver.jdbc.SQLServerDriver') \
        .option('query', predicateQuery) \
        .option("user", userName) \
        .option("password", password) \
        .load().orderBy("created_on_date")

    newData=newData.cache()
    newData.createOrReplaceTempView("joindata")
    newData.show(10,False)

    recCount=newData.count()

    logging.info("Data Fetched from Sql Server:{0}".format(str(datetime.now())))

    if recCount == 0:
        logging.info("No Data to be inserted")
        #raise Exception("No New Record found for insertion")
        #sys.exit(-1)
        logging.info("Writing logs into {0} table ".format(logtable))
        auditQuery = "select cast('{0}' as timestamp) as execution_start_time,cast(current_timestamp() as timestamp)as execution_end_time,cast('{1}' as int) as is_success, cast({3} as int) as Patients_Processed_Count,cast('{2}' as timestamp) as created_on_date from auditTable limit 1".format(
            startTime, 0, auditDate, 0)

        auditTable = spark.sql(auditQuery)
        auditTable.write.format("jdbc") \
            .mode("append") \
            .option("url", sqlurl) \
            .option("dbtable", logtable) \
            .option("user", userName) \
            .option("password", password) \
            .save()
        logging.info("Logs updated in {0} table".format(logtable))
        sys.exit(0)

    created_on_date=newData.select(max("created_on_date").alias("max_created_on_date")).collect()[0].max_created_on_date
    # updated_on_date=newData.select(max("updated_on_date").alias("max_updated_on_date")).collect()[0].max_updated_on_date

    data=newData
    datacol=data.columns
    datacol.remove('VBC_Program_Name')

    datacol.append("CASE WHEN (ENROLLMENT_end_date is null) THEN VBC_Program_Name ELSE 'NA' END as VBC_Program_Name")
    data=data.selectExpr(datacol)

    logging.info("Renaming Data column to salesforce column: {0}".format(str(datetime.now())))

    sfColTemp=[]
    for index, col in csvfile.iterrows():
        #print("SQL Column:"+str(col.SQL_Column)+" Salesforce column:"+str(col.Salesforce_Column))
        data = data.withColumnRenamed(col.SQL_Column, col.Salesforce_Column)
        colList.append(col.Salesforce_Column)

    changedDataset = data.selectExpr(colList)
    logging.info("Renaming Data colum to salesforce column finished:{0}".format(str(datetime.now())))
    #changedDataset.show(10,False)

    config_map = map(lambda row: row.asDict(), changedDataset.collect())

    for key in config_map:
        dataMap = key
        listDataMap.append(dataMap)

    try:
        logging.info("Loading data into salesforce:{0}".format(str(datetime.now())))
        bulk = SalesforceBulk(username=salesforceUsername, password=salesforcePassword, security_token=securityToken,sandbox=True)
        job = bulk.create_upsert_job(targettablename, external_id_name='Patient_BK__c',contentType='CSV',concurrency='Parallel',pk_chunking=100000)
        csv_iter = CsvDictsAdapter(iter(listDataMap))
        batch = bulk.post_batch(job, csv_iter)
        bulk.wait_for_batch(job, batch)
        batchResults=bulk.get_batch_results(batch)
        generaetLogFile(batchResults,sqlurl,sqlserverfailedtable,userName, password,spark)
        bulk.close_job(job)

        logging.info("Done. {0} records uploaded in Accounts object in salesforce:{1}".format(recCount,str(datetime.now())))
        logging.info("Writing logs into {0} table: {1}".format(logtable,str(datetime.now())))

        auditQuery = "select cast('{0}' as timestamp) as execution_start_time,cast(current_timestamp() as timestamp)" \
                     "as execution_end_time,cast('{1}' as int) as is_success, cast({3} as int) as Patients_Processed_Count,cast('{2}' as timestamp) as created_on_date from auditTable limit 1".format(
            startTime, 1, created_on_date,recCount)

        auditTable = spark.sql(auditQuery)

        auditTable.write.format("jdbc") \
            .mode("append") \
            .option("url", sqlurl) \
            .option("dbtable", logtable) \
            .option("user", userName) \
            .option("password", password) \
            .save()
        logging.info("Logs updated in {0} table:{1}".format(logtable,str(datetime.now())))
    except Exception as ex:
        logging.info("Writing logs into {0} table ".format(logtable))
        auditQuery = "select cast('{0}' as timestamp) as execution_start_time,cast(current_timestamp() as timestamp)as execution_end_time,cast('{1}' as int) as is_success, cast({3} as int) as Patients_Processed_Count,cast('{2}' as timestamp) as created_on_date from auditTable limit 1".format(
            startTime, 0, created_on_date,0)

        auditTable = spark.sql(auditQuery)
        auditTable.write.format("jdbc") \
            .mode("append") \
            .option("url", sqlurl) \
            .option("dbtable", logtable) \
            .option("user", userName) \
            .option("password", password) \
            .save()
        logging.info("Logs updated in {0} table".format(logtable))
        logging.error(str(ex))
        raise ex
        sys.exit(-1)


