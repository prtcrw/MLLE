import requests
import contextlib

def query(endpoint, query):
  with contextlib.closing(requests.Session()) as session:
    response = session.get(endpoint, params={
      'query': query,
    }, auth=requests.auth.HTTPBasicAuth('admin', 'admin'), verify=False)
    return response.json()
  
def to_dict(sparql_result):
    results_dict_list = []
    
    # Extract variable names
    vars_list = sparql_result.get('head', {}).get('vars', [])
    
    # Extract the bindings
    bindings = sparql_result.get('results', {}).get('bindings', [])
    
    # Process each binding
    for binding in bindings:
        parsed_result = {}
        for var in vars_list:
            if var in binding:
                parsed_result[var] = binding[var]['value']
            else:
                parsed_result[var] = None  # If the key is not present, set value as None
        results_dict_list.append(parsed_result)
    
    return results_dict_list

