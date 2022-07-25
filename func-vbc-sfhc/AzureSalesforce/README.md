# Introduction 
This project is based on the point to point integration between Azure database and salesforce. It uploads and creates the records in salesforce. It works on the following logic:
o	The data is filtered through the audit date (This date is fetched from the log table created_on column). 
o	The records having time stamp above the audit date are qualified for insertion or update.
o	We take the records which are greater than CreatedDate and LastModifiedDate and upsert them.
o	Once the records are successfully pushed into salesforce, maximum date from created_on_date and Updated_on_date is selected as a entry for log table column.SFHC_Latest_Created_Or_Updated_Date. Which is considered as a filter for next run.
o	If the records are not updated properly then the log table will give an error and send out an email to respective participants and update failure logs in the table. 
o	If there are no records to process then it will have entry and keep the old SFHC_Created_on_date only.


# Getting Started
Pre-requsites:
1) Require following packages. (They are specified with specific versions in requirement.txt as well)
    azure-functions
    cryptography==36.0.1
    cygrpc
    grpcio
    azure-functions
    boto3==1.21.27
    botocore==1.24.27
    FindSpark==2.0.0
    Numpy
    pandas
    pyspark==3.2.0
    python-dateutil==2.8.2
    pytz==2021.3
    requests==2.26.0
    salesforce-bulk==2.2.0
    Unicodecsv==0.14.1
    Urllib3==1.26.7

2) Following Environmental variables are used:
        #SPARK_HOME (When running locally the environmental variable is sparthome is commented but on running it through Azure you need to specify the path.)
        sqluserName 
        sqlpassword
        salesforceusername  
        salesforcepassword  
        securitytoken 
        sourcetablename 
        targettablename 
        sqljarpath
        sqlurl 
        logtable  
        sqlserverfailedtable 
3) Mappings.csv file
4) JDBC JARS


# Build and Test
The code runs in 5 stages. They are as follows:
    1. Fetching the latest records creation time from Log table
    2. Fetching data from the Underlying Azure database
    3. Identifying the records to be inserted and updated
    4. Pushing the records to salesforce
    5. Updating the log tables. If there are any errors updating the failed log table and sending out email notification.

