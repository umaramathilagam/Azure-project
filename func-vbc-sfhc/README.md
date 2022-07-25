# TimerTrigger - Python

The `TimerTrigger` makes it incredibly easy to have your functions executed on a schedule. This sample demonstrates a simple use case of calling your function every 5 minutes.

## How it works

For a `TimerTrigger` to work, you provide a schedule in the form of a [cron expression](https://en.wikipedia.org/wiki/Cron#CRON_expression)(See the link for full details). A cron expression is a string with 6 separate expressions which represent a given schedule via patterns. The pattern we use to represent every 5 minutes is `0 */5 * * * *`. This, in plain text, means: "When seconds is equal to 0, minutes is divisible by 5, for any hour, day of the month, month, day of the week, or year".

## Learn more
Environmental Variables:

1) sqluserName = Database VBC Login username
2) sqlpassword  = Database  VBC login password
3) salesforceusername = Salesforce portal username   
4) salesforcePassword = Salesforce portal password
5) securityToken = Salesforce login security Token
6) sqljarpath = Relative path to be given by creating a lib folder inside codearea and pasting the Jar over there. "codeArea\\lib\\mssql-jdbc-10.2.1.jre8.jar"
7) sqlurl = SQL JDBC URL to login into the VBC Database , specify the port number along with the database name 
eg. jdbc:sqlserver://ba-use1-sandbox-ass-data.database.windows.net:1433;database=ba-use1-sbx-sqd-VBC
8) Sender = Sender AWS SES email service registered email address
9) accessid = Access id used in AWS SES email service console
10) accessKey = Access key used in AWS SES email service console
11) awsregion = Region through which the AWS SES service is running

- To get the salesforce account created, please contact Marty Bremer from Cloudnerd team @marty@cloudnerd.com