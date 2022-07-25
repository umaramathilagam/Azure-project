import datetime
import logging

from codeArea import User

import azure.functions as func


def main(mytimer: func.TimerRequest) -> None:
    print("hello")
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()

    print(utc_timestamp)

    logging.info('Python HTTP trigger function processed a request.')
    #Main_Production.mainFunction()
    User.mainFunction()

    logging.info('Python timer trigger function ran at %s', utc_timestamp)
    