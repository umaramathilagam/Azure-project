import pyspark.sql.functions
from pyspark.sql import Row, SQLContext, SparkContext
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from salesforce_bulk import SalesforceBulk, CsvDictsAdapter
import sys
import pandas as pd
import time
import json
from salesforce_bulk.util import IteratorBytesIO
import findspark
from cryptography.fernet import Fernet
import os
os.environ['SPARK_HOME']="/Users/suren/PycharmProjects/Azureproject/lib/python3.7/site-packages/pyspark"

def performBatchInsert(tablename,spark,sqlsUrl,userName,password):
    print("Inserting Data into Batch Table: Started")
    batchTableName="[VBC].[VBC_Extern].VBC_SFHC_To_DW_Batches"
    from datetime import datetime
    Created_On_Date = str(datetime.now())
    data = [{'ObjectName': tablename, 'Created_On_Date': Created_On_Date,
             'Is_Merged_To_DW': 0 }]

    # creating a dataframe
    batchDF = spark.createDataFrame(data).selectExpr("ObjectName","cast(Created_On_Date as timestamp) as Created_On_Date","Is_Merged_To_DW")
    batchDF.write.format("jdbc") \
        .mode("append") \
        .option("url", sqlsUrl) \
        .option("dbtable", batchTableName) \
        .option("user", userName) \
        .option("password", password) \
        .save()

    query = "select max(batch_id) as batchid from {0} where objectname='{1}'".format(batchTableName,tablename)
    batchID = spark.read.format('jdbc') \
        .option('url', sqlsUrl) \
        .option('driver', 'com.microsoft.sqlserver.jdbc.SQLServerDriver') \
        .option('query', query) \
        .option("user", userName) \
        .option("password", password) \
        .load()
    print("Inserting Batch Records finished")
    return batchID.collect()[0].batchid

def getAuditTime(spark,sqlsUrl,userName,password,logTable,objectname):
    query="select max(SFHC_Latest_Created_Or_Updated_Date) as max_created_on_date from {0} where Object_Name='{1}'".format(logTable,objectname)
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


#Main Function
#if __name__ == '__main__':
def mainFunction():

    userName=""
    password=""
    salesforceUsername=""
    salesforcePassword=""
    #key=os.environ['encKey']
    securityToken = ""
    print("Fetching Credentials from File")
    from datetime import datetime

    startTime = str(datetime.now())

    #credFile = pd.read_csv("extracredentials.csv", header='infer')
    csvfile = pd.read_csv("/Users/suren/Desktop/func-vbc-sfhc/codeArea/user.csv", header='infer')

    #for index, col in credFile.iterrows():
    userName='Uma_AgileNautics'
    password='Ki#$dney341@'
    salesforceUsername='integrationuser@panoramichealth.com'
    salesforcePassword='API2PHintegration'
    securityToken='7qil2roT7gYh3Ngm6qhdtV76'
    sqljarpath="/Users/suren/Desktop/func-vbc-sfhc/codeArea/lib/mssql-jdbc-10.2.1.jre8.jar"

    print(salesforceUsername)
    print(salesforcePassword)

    #f = Fernet(str.encode(key))
    #userName = f.decrypt(str.encode(userName)).decode()
    #password = f.decrypt(str.encode(password)).decode()
    #salesforceUsername = f.decrypt(str.encode(salesforceUsername)).decode()
    #salesforcePassword = f.decrypt(str.encode(salesforcePassword)).decode()
    #securityToken = f.decrypt(str.encode(securityToken)).decode()
    print("Credentials Fetched from File")

    findspark.init()

    # Spark Session Intailization
    spark = SparkSession \
        .builder \
        .master('local[*]') \
        .appName('Connection-Test') \
        .config("spark.sql.session.timezone", "America/New_York") \
        .config('spark.driver.extraClassPath', sqljarpath) \
        .config('spark.executor.extraClassPath', sqljarpath) \
        .getOrCreate()
       

    # Variable Declarations
    sqlsUrl = 'jdbc:sqlserver://dataserver.sandbox.rcoanalytics.com:1433'
    sqlServerSnapShotTable = "VBC.[VBC_Extern].VBC_SFHC_User"
    salesforceTableName ="User"
    logTable = "VBC.[VBC_Extern].[VBC_SFHC_To_DW_Daily_Log]"
    auditDateDF = getAuditTime(spark, sqlsUrl, userName, password, logTable, "User")
    auditDateDF.createOrReplaceTempView('auditTable')
    auditDate = str(auditDateDF.select("max_created_on_date").collect()[0].max_created_on_date)
    auditDate = auditDate[0:23]
    print(auditDate)

    sfCol = []
    sqlCol = []
    print("Fetching Column and Datatype Mapping from csv File")
    for index, col in csvfile.iterrows():
        sfCol.append(str(col.DW_Column))
        sqlCol.append(str(col.DW_Column) + "^" + str(col.SQL_Column) + "^" + str(col.Datatypes))

    try:
        print("Getting data from salesforce")

        bulk = SalesforceBulk(username=salesforceUsername, password=salesforcePassword, security_token=securityToken,
                              sandbox=False
                              )
        job = bulk.create_query_job(salesforceTableName, contentType='JSON')
        print("select {0} from {1} ".format(",".join(sfCol), salesforceTableName))
        batch = bulk.query(job, "select {0} from {1} ".format(",".join(sfCol), salesforceTableName))
        while not bulk.is_batch_done(batch):
            print("Getting Records from SalesForce")
            time.sleep(6)

        salesforceData = ""
        salesforceList = []
        for result in bulk.get_all_results_for_query_batch(batch, job):
            salesforceData = json.load(IteratorBytesIO(result))
            for slData in salesforceData:
                salesforceDict = {}
                for slcols in sfCol:
                    salesforceDict[slcols] = str(slData[slcols])
                    # salesforceDict['Patient_BK__c'] = str(slData['Patient_BK__c'])
                salesforceList.append(salesforceDict)

        salesForceDF = spark.createDataFrame(Row(**x) for x in salesforceList)
        print("Records Fetched from Salesforce")
        fetchDwCol = []
        for dw in sqlCol:
            sCol = dw.split("^")[0]
            dwCol = dw.split("^")[1]
            datatype = dw.split("^")[2]
            salesForceDF = salesForceDF.withColumnRenamed(sCol, dwCol)
            fetchDwCol.append("CAST(" + dwCol + " as " + datatype + ") as " + dwCol)

        fetchDwCol.append("cast(current_timestamp() as string) as time_stamp")
        salesForceDF = salesForceDF.selectExpr(fetchDwCol)


        fetchDwCol.remove("CAST(LastModifiedDate as bigint) as LastModifiedDate")
        fetchDwCol.remove("CAST(CreatedDate as bigint) as CreatedDate")
        fetchDwCol.append("from_unixtime(cast((LastModifiedDate DIV 1000) as bigint)) as LastModifiedDate")
        fetchDwCol.append("from_unixtime(cast((CreatedDate DIV 1000) as bigint)) as CreatedDate")
        fetchDwCol.remove("CAST(LastLoginDate as bigint) as LastLoginDate")
        fetchDwCol.append("from_unixtime(cast((LastLoginDate DIV 1000) as bigint)) as LastLoginDate")
        salesForceDF = salesForceDF.selectExpr(fetchDwCol)
        whereQuery = "(cast(LastModifiedDate as timestamp)>cast('{0}' as timestamp) or cast(CreatedDate as timestamp)>cast('{0}' as timestamp)) and IsActive='True' ".format(
            auditDate)
        salesForceDF = salesForceDF.where(whereQuery)
        recCount = salesForceDF.count()
        print(recCount)

        if recCount == 0:
            print("No Records to Process")
            print("Writing logs into {0} table: {1}".format(logTable, str(datetime.now())))
            auditQuery = "select cast('{0}' as timestamp) as execution_start_time,cast(current_timestamp() as timestamp)" \
                         "as execution_end_time,cast('{1}' as int) as is_success, cast({3} as int) as Record_Count,cast('{2}' as timestamp) as SFHC_Latest_Created_Or_Updated_Date,cast('User' as string) as object_name from auditTable limit 1".format(
                startTime, 2, auditDate, 0)

            auditTable = spark.sql(auditQuery)

            auditTable.write.format("jdbc") \
                .mode("append") \
                .option("url", sqlsUrl) \
                .option("dbtable", logTable) \
                .option("user", userName) \
                .option("password", password) \
                .save()
            print("Logs updated in {0} table:{1}".format(logTable, str(datetime.now())))
            sys.exit(0)
        lastmodified = salesForceDF.select(max("LastModifiedDate").alias("max_lastmodified")).collect()[
            0].max_lastmodified
        createdDate = salesForceDF.select(max("CreatedDate").alias("max_CreatedDate")).collect()[
            0].max_CreatedDate

        t1 = datetime.strptime(lastmodified, "%Y-%m-%d %H:%M:%S")
        t2 = datetime.strptime(createdDate, "%Y-%m-%d %H:%M:%S")

        difference = t1 - t2
        if difference.days > 0:
            created_on_date = lastmodified
        else:
            created_on_date = createdDate

        # sys.exit(0)
        batchId = performBatchInsert("User", spark, sqlsUrl, userName, password)
        salesForceDF = salesForceDF.withColumn("batch_id", lit(batchId))
        print("Writting Records into {0}".format(sqlServerSnapShotTable))
        salesForceDF.write.format("jdbc") \
            .mode("append") \
            .option("url", sqlsUrl) \
            .option("dbtable", sqlServerSnapShotTable) \
            .option("user", userName) \
            .option("password", password) \
            .save()
        bulk.close_job(job)
        print("Writing logs into {0} table: {1}".format(logTable, str(datetime.now())))

        auditQuery = "select cast('{0}' as timestamp) as execution_start_time,cast(current_timestamp() as timestamp)" \
                     "as execution_end_time,cast('{1}' as int) as is_success, cast({3} as int) as Record_Count,cast('{2}' as timestamp) as SFHC_Latest_Created_Or_Updated_Date,cast('User' as string) as object_name from auditTable limit 1".format(
            startTime, 1, created_on_date, recCount)

        auditTable = spark.sql(auditQuery)

        auditTable.write.format("jdbc") \
            .mode("append") \
            .option("url", sqlsUrl) \
            .option("dbtable", logTable) \
            .option("user", userName) \
            .option("password", password) \
            .save()
        print("Logs updated in {0} table:{1}".format(logTable, str(datetime.now())))

        print("Writting Records into {0} Finished".format(sqlServerSnapShotTable))
    except Exception as ex:
        print("Writing logs into {0} table: {1}".format(logTable, str(datetime.now())))

        auditQuery = "select cast('{0}' as timestamp) as execution_start_time,cast(current_timestamp() as timestamp)" \
                     "as execution_end_time,cast('{1}' as int) as is_success, cast({3} as int) as Record_Count,cast('{2}' as timestamp) as SFHC_Latest_Created_Or_Updated_Date,cast('User' as string) as object_name from auditTable limit 1".format(
            startTime, 0, auditDate, 0)

        auditTable = spark.sql(auditQuery)

        auditTable.write.format("jdbc") \
            .mode("append") \
            .option("url", sqlsUrl) \
            .option("dbtable", logTable) \
            .option("user", userName) \
            .option("password", password) \
            .save()
        print("Logs updated in {0} table:{1}".format(logTable, str(datetime.now())))
        raise ex