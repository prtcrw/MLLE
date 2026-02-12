# from typing import Optional, List, Dict, Any
# import os
# import re
# import json
# import logging

# from fastapi import APIRouter, HTTPException, Request
# from pydantic import BaseModel

# import rdflib
# try:
#     import pandas as pd
# except Exception:
#     pd = None

# logger = logging.getLogger(__name__)

# router = APIRouter()


# class ConvertRequest(BaseModel):
#     input: str


# def load_rdf(path: Optional[str] = None) -> rdflib.Graph:
#     g = rdflib.Graph()
#     if path is None:
#         path = os.environ.get('MLLO_RDF_PATH', '/Ontology/MLLO.rdf')

#     if os.path.exists(path):
#         try:
#             g.parse(path)
#             logger.info(f"Loaded RDF from {path}")
#         except Exception as e:
#             logger.exception(f"Failed to parse RDF {path}: {e}")
#     else:
#         logger.warning(f"RDF file not found at {path}; entity linking disabled")

#     return g


# _RDF_GRAPH = load_rdf()


# def build_label_map(g: rdflib.Graph):
#     from rdflib.namespace import RDFS, SKOS
#     label_map = {}  # label (lower) -> set(uris)
#     uri_set = set()

#     for s in set(g.subjects()):
#         uri_set.add(str(s))
#         for p in [RDFS.label, SKOS.prefLabel, RDFS.comment]:
#             for o in g.objects(s, p):
#                 text = str(o).strip()
#                 if text:
#                     label_map.setdefault(text.lower(), set()).add(str(s))

#     return label_map, uri_set


# LABEL_MAP, URI_SET = build_label_map(_RDF_GRAPH)


# def entity_link(input_text: str):
#     found = {}
#     lower = input_text.lower()
#     # exact label match
#     for label, uris in LABEL_MAP.items():
#         if label in lower:
#             found[label] = list(uris)
#     return found


# def validate_sparql(sparql: str):
#     # Find URIs in <...> or prefixed names like ml:Something
#     uris = set(re.findall(r"<([^>]+)>", sparql))
#     prefixed = set(re.findall(r"([a-zA-Z0-9_-]+):([A-Za-z0-9_\-]+)", sparql))

#     # For simplicity, ensure any full URIs are in URI_SET
#     for u in uris:
#         if u not in URI_SET:
#             return False, f"Unknown URI used: {u}"

#     # Prefixed names validation skipped (requires prefix resolution)
#     return True, "OK"


# def normalize_sparql(sparql: str) -> str:
#     """Normalize common prefix/term mismatches produced by LMs.

#     - Rewrites `schema:Model` -> `ml:MachineLearningModel` (project ontology)
#     - Injects `PREFIX ml:` declaration when `ml:` is used but no PREFIX present
#     """
#     try:
#         import re
#         s = sparql

#         # Common LM output mapping -> prefer ml:MachineLearningModel
#         s = re.sub(r"\bschema:Model\b", "ml:MachineLearningModel", s)
#         # Map generic dataset mentions to the project's dataset class
#         s = re.sub(r"\bschema:Dataset\b", "ml:MachineLearningDataSet", s)
#         s = re.sub(r"http://example\.org/Dataset", "http://www.semanticweb.org/mnd14/ml/MachineLearningDataSet", s)
#         s = re.sub(r"<http://example\.org/Dataset>", "<http://www.semanticweb.org/mnd14/ml/MachineLearningDataSet>", s)

#         # If ml: is used and no PREFIX ml: present, add it at the top
#         if "ml:" in s and not re.search(r"PREFIX\s+ml:\s*<", s, flags=re.IGNORECASE):
#             prefix = "PREFIX ml: <http://www.semanticweb.org/mnd14/ml/>\n"
#             s = prefix + s

#         return s
#     except Exception:
#         return sparql


# class QueryGenerator:
#     """Wraps calls to the local LM/LM Studio instance and builds strict prompts
#     that force the model to use only the provided MLLO RDF URIs.
#     """

#     def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
#         self.base_url = base_url or os.environ.get('LM_API_URL', os.environ.get('LM_STUDIO_URL', 'http://127.0.0.1:1234'))
#         self.api_key = api_key or os.environ.get('LM_API_KEY')

#     def generate(self, text: str, allowed_uris: List[Dict[str, str]]) -> str:
#         if not text or not text.strip():
#             raise ValueError('Empty input')

#         prompt_parts = []
#         prompt_parts.append("You are a translator from natural language to SPARQL. ONLY use the provided URIs below. If no provided URI fits, respond with EXACTLY: NO_SPARQL")
#         prompt_parts.append("Include the following prefix declaration and use it for model classes:" \
#                             "\nPREFIX ml: <http://www.semanticweb.org/mnd14/ml/>. " \
#                             "When referring to the model class use ml:MachineLearningModel. " \
#                             "Do NOT use schema:Model or other unrelated vocabularies.")
#         if allowed_uris:
#             prompt_parts.append("Allowed URIs:")
#             for a in allowed_uris:
#                 prompt_parts.append(f"- {a['label']} -> <{a['uri']}>")

#         prompt_parts.append('\nUser request:')
#         prompt_parts.append(text)
#         prompt_parts.append('\nOutput: Provide ONLY the SPARQL query text, no explanation.')

#         prompt = "\n".join(prompt_parts)

#         # reuse existing call_lm helper which already handles multiple LM Studio shapes
#         out = call_lm(prompt)
#         sparql = out.strip()
#         return sparql


# class QueryExecutor:
#     """Execute SPARQL against an rdflib.Graph and return JSON-friendly results.

#     Handles SELECT, ASK, and simple CONSTRUCT/DESCRIBE (returns list of triples).
#     """

#     def __init__(self, graph: rdflib.Graph):
#         self.graph = graph

#     def _row_to_dict(self, row, vars_):
#         d = {}
#         for i, v in enumerate(vars_):
#             val = row[i]
#             d[str(v)] = None if val is None else str(val)
#         return d

#     def execute(self, sparql: str, as_dataframe: bool = False) -> Any:
#         try:
#             res = self.graph.query(sparql)
#         except Exception as e:
#             raise RuntimeError(f"SPARQL execution error: {e}")

#         # ASK query -> boolean
#         if isinstance(res, bool):
#             return {'boolean': res}

#         # CONSTRUCT/DESCRIBE -> graph-like (iterator of triples or a Graph)
#         if hasattr(res, 'triples') or isinstance(res, rdflib.Graph):
#             triples = []
#             # Some engines return a Graph
#             try:
#                 for t in res:
#                     s, p, o = t
#                     triples.append({'s': str(s), 'p': str(p), 'o': str(o)})
#             except Exception:
#                 # res may be an iterator of triple bindings
#                 for t in list(res):
#                     s, p, o = t
#                     triples.append({'s': str(s), 'p': str(p), 'o': str(o)})

#             if as_dataframe and pd is not None:
#                 return pd.DataFrame(triples)
#             return triples

#         # SELECT-like result: rows with named vars
#         vars_ = getattr(res, 'vars', None)
#         results_list: List[Dict[str, Any]] = []
#         if vars_:
#             for row in res:
#                 results_list.append(self._row_to_dict(row, vars_))

#         if as_dataframe:
#             if pd is None:
#                 raise RuntimeError('pandas not available to convert results to DataFrame')
#             try:
#                 return pd.DataFrame(results_list)
#             except Exception as e:
#                 raise RuntimeError(f'Failed to build DataFrame: {e}')

#         return results_list


# def call_lm(prompt: str) -> str:
#     base_url = os.environ.get('LM_API_URL', os.environ.get('LM_STUDIO_URL', 'http://127.0.0.1:1234'))
#     import requests

#     headers_base = {'Content-Type': 'application/json'}
#     api_key = os.environ.get('LM_API_KEY')
#     if api_key:
#         headers_base['Authorization'] = f'Bearer {api_key}'

#     # Try a few common LM endpoints and payload shapes to be flexible with LM Studio instances
#     tried = []
#     base = base_url.rstrip('/')
#     # prefer specific chat/generate endpoints first; try bare root last
#     candidate_paths = ["/v1/chat/completions", "/api/v1/chat", "/api/v1/generate", "/api/generate", "/v1/generate", "/generate", "/api/rest/generate", ""]

#     # If the provided base_url already contains a path (e.g. http://host:port/api/v1/chat)
#     # try that full URL first to avoid sending incompatible payload shapes to the server root.
#     try:
#         from urllib.parse import urlparse
#         parsed = urlparse(base_url)
#         if parsed.path and parsed.path not in ('', '/'):
#             candidate_paths.insert(0, '')
#     except Exception:
#         pass

#     # include model/system_prompt shapes used by some LM Studio/chat endpoints
#     model = os.environ.get('LM_MODEL', 'local-model')
#     system_prompt = os.environ.get('LM_SYSTEM_PROMPT')

#     payload_variants = [
#         {"input": prompt},
#         {"prompt": prompt},
#         {"text": prompt},
#         {"messages": [{"role": "user", "content": prompt}]},
#         {"data": {"input": prompt}},
#     ]

#     # Only include model/system_prompt when provided (avoid sending null)
#     optional_payload: Dict[str, Any] = {}
#     if model:
#         optional_payload['model'] = model
#     if system_prompt:
#         optional_payload['system_prompt'] = system_prompt
#     # always include the input text
#     optional_payload['input'] = prompt

#     payload_variants.append(optional_payload)

#     def extract_text_from_json(j):
#         if isinstance(j, str):
#             return j
#         if isinstance(j, dict):
#             # top-level simple keys
#             for k in ('text', 'result', 'output', 'answer', 'response', 'generated_text'):
#                 v = j.get(k)
#                 if isinstance(v, str) and v.strip():
#                     return v

#             # common nested shapes
#             if 'results' in j and isinstance(j['results'], list) and j['results']:
#                 first = j['results'][0]
#                 if isinstance(first, dict):
#                     for k in ('text', 'output', 'content', 'answer'):
#                         if k in first and isinstance(first[k], str):
#                             return first[k]
#                 if isinstance(first, str):
#                     return first

#             if 'outputs' in j and isinstance(j['outputs'], list) and j['outputs']:
#                 out = j['outputs'][0]
#                 if isinstance(out, dict):
#                     if 'content' in out and isinstance(out['content'], str):
#                         return out['content']

#             if 'choices' in j and isinstance(j['choices'], list) and j['choices']:
#                 ch = j['choices'][0]
#                 if isinstance(ch, dict):
#                     if 'text' in ch and isinstance(ch['text'], str):
#                         return ch['text']
#                     if 'message' in ch and isinstance(ch['message'], dict):
#                         msg = ch['message']
#                         if 'content' in msg and isinstance(msg['content'], str):
#                             return msg['content']

#         return None

#     errors = []
#     for path in candidate_paths:
#         url = base + path

#         # Build path-specific payloads to match common LM Studio endpoints
#         path_payloads: List[Dict[str, Any]] = []

#         # If this path looks like a chat endpoint, prefer messages+model shape
#         if path.endswith('/v1/chat/completions') or path.endswith('/api/v1/chat') or (path == '' and base_url.rstrip('/').endswith('/api/v1/chat')) or '/api/v1/chat' in base_url or '/v1/chat/completions' in base_url:
#             chat_payload: Dict[str, Any] = {}
#             chat_payload['model'] = model
#             msgs = []
#             if system_prompt:
#                 msgs.append({'role': 'system', 'content': system_prompt})
#             msgs.append({'role': 'user', 'content': prompt})
#             chat_payload['messages'] = msgs
#             path_payloads.append(chat_payload)

#         # Otherwise try the generic payload variants we built earlier
#         path_payloads.extend(payload_variants)

#         for payload in path_payloads:
#             try:
#                 headers = headers_base.copy()
#                 resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
#                 tried.append({'url': url, 'payload': list(payload.keys()), 'status': resp.status_code})
#                 # Accept 200-299
#                 if resp.status_code >= 200 and resp.status_code < 300:
#                     # Try JSON parse
#                     text_out = None
#                     try:
#                         j = resp.json()
#                         text_out = extract_text_from_json(j)
#                         if text_out:
#                             return text_out
#                         # fallback to json string; ignore generic server messages
#                         lower_json = json.dumps(j).lower()
#                         if 'unexpected endpoint' in lower_json or 'unexpected endpoint or method' in lower_json:
#                             errors.append(f"Rejected JSON response from {url}: {str(j)[:200]}")
#                             continue
#                         if '<html' in lower_json:
#                             errors.append(f"Rejected HTML-like JSON from {url}")
#                             continue
#                         return json.dumps(j)
#                     except Exception:
#                         # not json, try raw text
#                         body = resp.text.strip()
#                         if body:
#                             low = body.lower()
#                             if ('unexpected endpoint' in low or 'unexpected endpoint or method' in low
#                                     or '<html' in low or 'not found' in low or 'method not allowed' in low):
#                                 errors.append(f"Rejected body response from {url}: {body[:200]}")
#                                 continue
#                             return body
#                         else:
#                             errors.append(f"Empty response from {url}")
#                 else:
#                     # capture body for debugging
#                     body = resp.text.strip()
#                     errors.append(f"{resp.status_code} from {url}: {body}")
#             except Exception as e:
#                 errors.append(f"Error calling {url} with payload keys {list(payload.keys())}: {e}")

#     logger.error('LM call attempts: %s', tried)
#     logger.error('LM call errors: %s', errors)
#     raise RuntimeError(f"LM call failed; attempts: {tried}; errors: {errors}")


# @router.post('/convert-sparql')
# async def convert_sparql(req: ConvertRequest):
#     text = req.input.strip()
#     if not text:
#         raise HTTPException(status_code=400, detail='Empty input')

#     # Entity linking
#     linked = entity_link(text)

#     # Build prompt with strict instructions
#     allowed_uris = []
#     for lbl, uris in linked.items():
#         for u in uris:
#             allowed_uris.append({'label': lbl, 'uri': u})

#     prompt_parts = []
#     prompt_parts.append("You are a translator from natural language to SPARQL. ONLY use the provided URIs below. If no provided URI fits, respond with EXACTLY: NO_SPARQL")
#     prompt_parts.append("Include the following prefix declaration and use it for model classes:\nPREFIX ml: <http://www.semanticweb.org/mnd14/ml/>. When referring to the model class use ml:MachineLearningModel. Do NOT use schema:Model or other unrelated vocabularies.")
#     if allowed_uris:
#         prompt_parts.append("Allowed URIs:")
#         for a in allowed_uris:
#             prompt_parts.append(f"- {a['label']} -> <{a['uri']}>")

#     prompt_parts.append('\nUser request:')
#     prompt_parts.append(text)
#     prompt_parts.append('\nOutput: Provide ONLY the SPARQL query text, no explanation.')

#     prompt = "\n".join(prompt_parts)

#     try:
#         lm_out = call_lm(prompt)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f'LM call failed: {e}')

#     sparql = lm_out.strip()
#     # Normalize common LM output (e.g., schema:Model -> ml:MachineLearningModel)
#     sparql = normalize_sparql(sparql)

#     if sparql == 'NO_SPARQL':
#         raise HTTPException(status_code=422, detail='No suitable URIs found to construct SPARQL')

#     ok, msg = validate_sparql(sparql)
#     if not ok:
#         raise HTTPException(status_code=422, detail=f'Validation failed: {msg}')

#     return {'sparql': sparql}


# @router.post('/generate-and-execute')
# async def generate_and_execute(request: Request, req: ConvertRequest):
#     text = req.input.strip()
#     if not text:
#         raise HTTPException(status_code=400, detail='Empty input')

#     # Entity linking
#     linked = entity_link(text)

#     allowed_uris = []
#     for lbl, uris in linked.items():
#         for u in uris:
#             allowed_uris.append({'label': lbl, 'uri': u})

#     gen = QueryGenerator()
#     try:
#         sparql = gen.generate(text, allowed_uris)
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f'LLM generation failed: {e}')

#     if sparql == 'NO_SPARQL':
#         raise HTTPException(status_code=422, detail='No suitable URIs found to construct SPARQL')

#     # Normalize generated SPARQL before validation/execution
#     sparql = normalize_sparql(sparql)

#     ok, msg = validate_sparql(sparql)
#     if not ok:
#         raise HTTPException(status_code=422, detail=f'Validation failed: {msg}')

#     app = request.app

#     # Prefer executing the query against the configured SPARQL endpoint (GraphDB)
#     if hasattr(app, 'sparql_client') and app.sparql_client is not None:
#         try:
#             results = app.sparql_client.query(sparql)
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=f'Execution failed: {e}')
#     else:
#         execer = QueryExecutor(_RDF_GRAPH)
#         try:
#             results = execer.execute(sparql, as_dataframe=False)
#         except RuntimeError as e:
#             raise HTTPException(status_code=422, detail=str(e))
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=f'Execution failed: {e}')

#     return {'sparql': sparql, 'results': results}
