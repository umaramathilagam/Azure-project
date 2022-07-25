from codeArea import Main_Production,User

import azure.functions as func
import logging

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    #Main_Production.mainFunction()
    User
    
    return func.HttpResponse(f"Hello, Ashwini This HTTP triggered function executed successfully.")