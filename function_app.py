import azure.functions as func
import logging

app = func.FunctionApp()

# Add auth_level=func.AuthLevel.ANONYMOUS to allow public access
@app.route(route="translate", auth_level=func.AuthLevel.ANONYMOUS)
def translate_function(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Minimal test: Python HTTP trigger function processed a request.')
    
    name = req.params.get('name', 'world')

    return func.HttpResponse(f"Hello, {name}!")
