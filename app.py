import json
import logging
# Fixing MIME types for static files under Windows
import mimetypes
import os

import openai
import requests

from backend.utilities.employee_data.word_search import find_in_value, search_json
from backend.utilities.orchestrator.LangChainAgent import LangChainAgent
from eds_util import USER_DETAILS_KEYS, EXCLUSION_KEYS_1, EXCLUSION_KEYS_2, USER_KEYS_1, USER_KEYS_2

mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')

from flask import Flask, Response, request, jsonify
from dotenv import load_dotenv
from typing import List

from langchain.prompts import ChatPromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.schema import BaseOutputParser

load_dotenv()

app = Flask(__name__)
langchain_agent = LangChainAgent()

class CommaSeparatedListOutputParser(BaseOutputParser[List[str]]):
    """Parse the output of an LLM call to a comma-separated list."""
    def parse(self, text: str) -> List[str]:
        """Parse the output of an LLM call."""
        return text.strip().split(", ")

template = """
Hello, I'm your virtual assistance.
How can I help you?
"""
human_template = "{text}"

chat_prompt = ChatPromptTemplate.from_messages([
    ("system", template),
    ("human", human_template),
])

@app.route("/", defaults={"path": "index.html"})
@app.route("/<path:path>")
def static_file(path):
    return app.send_static_file(path)


# ACS Integration Settings
AZURE_SEARCH_SERVICE = os.environ.get("AZURE_SEARCH_SERVICE")
AZURE_SEARCH_INDEX = os.environ.get("AZURE_SEARCH_INDEX")
AZURE_SEARCH_KEY = os.environ.get("AZURE_SEARCH_KEY")
AZURE_SEARCH_USE_SEMANTIC_SEARCH = os.environ.get("AZURE_SEARCH_USE_SEMANTIC_SEARCH", False)
AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG = os.environ.get("AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG", "default")
AZURE_SEARCH_TOP_K = os.environ.get("AZURE_SEARCH_TOP_K", 5)
AZURE_SEARCH_ENABLE_IN_DOMAIN = os.environ.get("AZURE_SEARCH_ENABLE_IN_DOMAIN", "true")
AZURE_SEARCH_CONTENT_COLUMNS = os.environ.get("AZURE_SEARCH_CONTENT_COLUMNS")
AZURE_SEARCH_FILENAME_COLUMN = os.environ.get("AZURE_SEARCH_FILENAME_COLUMN")
AZURE_SEARCH_TITLE_COLUMN = os.environ.get("AZURE_SEARCH_TITLE_COLUMN")
AZURE_SEARCH_URL_COLUMN = os.environ.get("AZURE_SEARCH_URL_COLUMN")

# AOAI Integration Settings
AZURE_OPENAI_RESOURCE = os.environ.get("AZURE_OPENAI_RESOURCE")
AZURE_OPENAI_MODEL = os.environ.get("AZURE_OPENAI_MODEL")
AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY")
AZURE_OPENAI_TEMPERATURE = os.environ.get("AZURE_OPENAI_TEMPERATURE", 0)
AZURE_OPENAI_TOP_P = os.environ.get("AZURE_OPENAI_TOP_P", 1.0)
AZURE_OPENAI_MAX_TOKENS = os.environ.get("AZURE_OPENAI_MAX_TOKENS", 1000)
AZURE_OPENAI_STOP_SEQUENCE = os.environ.get("AZURE_OPENAI_STOP_SEQUENCE")
AZURE_OPENAI_SYSTEM_MESSAGE = os.environ.get("AZURE_OPENAI_SYSTEM_MESSAGE",
                                             "You are an AI assistant that helps people find information.")
AZURE_OPENAI_API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "2023-06-01-preview")
AZURE_OPENAI_STREAM = os.environ.get("AZURE_OPENAI_STREAM", "true")
AZURE_OPENAI_MODEL_NAME = os.environ.get("AZURE_OPENAI_MODEL_NAME",
                                         "gpt-35-turbo")  # Name of the model, e.g. 'gpt-35-turbo' or 'gpt-4'

SHOULD_STREAM = True if AZURE_OPENAI_STREAM.lower() == "true" else False


def is_chat_model():
    if 'gpt-4' in AZURE_OPENAI_MODEL_NAME.lower():
        return True
    return False


def should_use_data():
    if AZURE_SEARCH_SERVICE and AZURE_SEARCH_INDEX and AZURE_SEARCH_KEY:
        return True
    return False


def prepare_body_headers_with_data(request):
    request_messages = request.json["messages"]
    body = {
        "messages": request_messages,
        "temperature": AZURE_OPENAI_TEMPERATURE,
        "max_tokens": AZURE_OPENAI_MAX_TOKENS,
        "top_p": AZURE_OPENAI_TOP_P,
        "stop": AZURE_OPENAI_STOP_SEQUENCE.split("|") if AZURE_OPENAI_STOP_SEQUENCE else [],
        "stream": SHOULD_STREAM,
        "dataSources": [
            {
                "type": "AzureCognitiveSearch",
                "parameters": {
                    "endpoint": f"https://{AZURE_SEARCH_SERVICE}.search.windows.net",
                    "key": AZURE_SEARCH_KEY,
                    "indexName": AZURE_SEARCH_INDEX,
                    "fieldsMapping": {
                        "contentField": AZURE_SEARCH_CONTENT_COLUMNS.split("|") if AZURE_SEARCH_CONTENT_COLUMNS else [],
                        "titleField": AZURE_SEARCH_TITLE_COLUMN if AZURE_SEARCH_TITLE_COLUMN else None,
                        "urlField": AZURE_SEARCH_URL_COLUMN if AZURE_SEARCH_URL_COLUMN else None,
                        "filepathField": AZURE_SEARCH_FILENAME_COLUMN if AZURE_SEARCH_FILENAME_COLUMN else None
                    },
                    "inScope": True if AZURE_SEARCH_ENABLE_IN_DOMAIN.lower() == "true" else False,
                    "topNDocuments": AZURE_SEARCH_TOP_K,
                    "queryType": "semantic" if AZURE_SEARCH_USE_SEMANTIC_SEARCH.lower() == "true" else "simple",
                    "semanticConfiguration": AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG if AZURE_SEARCH_USE_SEMANTIC_SEARCH.lower() == "true" and AZURE_SEARCH_SEMANTIC_SEARCH_CONFIG else "",
                    "roleInformation": AZURE_OPENAI_SYSTEM_MESSAGE
                }
            }
        ]
    }

    chatgpt_url = f"https://{AZURE_OPENAI_RESOURCE}.openai.azure.com/openai/deployments/{AZURE_OPENAI_MODEL}"
    if is_chat_model():
        chatgpt_url += "/chat/completions?api-version=2023-03-15-preview"
    else:
        chatgpt_url += "/completions?api-version=2023-03-15-preview"

    headers = {
        'Content-Type': 'application/json',
        'api-key': AZURE_OPENAI_KEY,
        'chatgpt_url': chatgpt_url,
        'chatgpt_key': AZURE_OPENAI_KEY,
        "x-ms-useragent": "GitHubSampleWebApp/PublicAPI/1.0.0"
    }

    return body, headers


def stream_with_data(body, headers, endpoint, emp_data=None):
    s = requests.Session()
    response = {
        "id": "",
        "model": "",
        "created": 0,
        "object": "",
        "choices": [{
            "messages": []
        }]
    }
    try:
        # Added this block of code to resolve 400 - validation error.
        if 'stop' in body and not body.get('stop'):
            del body['stop']

        with s.post(endpoint, json=body, headers=headers, stream=True) as r:
            for line in r.iter_lines(chunk_size=10):
                if line:
                    lineJson = json.loads(line.lstrip(b'data:').decode('utf-8'))
                    # print(f'Print response: {lineJson}')
                    if 'error' in lineJson:
                        yield json.dumps(lineJson).replace("\n", "\\n") + "\n"
                    response["id"] = lineJson["id"]
                    response["model"] = lineJson["model"]
                    response["created"] = lineJson["created"]
                    response["object"] = lineJson["object"]

                    role = lineJson["choices"][0]["messages"][0]["delta"].get("role")
                    if role == "tool":
                        response["choices"][0]["messages"].append(lineJson["choices"][0]["messages"][0]["delta"])
                    elif role == "assistant":
                        print_msg = ""
                        if emp_data:
                            print_msg = f"As per the available data, {emp_data} \n\n"
                        response["choices"][0]["messages"].append({
                            "role": "assistant",
                            "content": f"{print_msg}"
                        })
                    else:
                        deltaText = lineJson["choices"][0]["messages"][0]["delta"]["content"]
                        if deltaText != "[DONE]":
                            response["choices"][0]["messages"][1]["content"] += deltaText

                    yield json.dumps(response).replace("\n", "\\n") + "\n"
    except Exception as e:
        yield json.dumps({"error": str(e)}).replace("\n", "\\n") + "\n"


def stream_static_content_data(result):
    print_msg = "No data found for requested information or you do not have access to the data."
    if result:
        print_msg = f"As per the available data, {result} \n\n"
    response = {
        "id": "e7d687d1-50ac-4d63-a782-5b3d755380d6",
        "model": "gpt-35-turbo-16k",
        "created": 1698938071,
        "object": "chat.completion.chunk",
        "choices": [
            {
                "messages": [
                    {
                        "role": "assistant",
                        "content": f"{print_msg}"
                    }
                ]
            }
        ]
    }
    return json.dumps(response).replace("\n", "\\n")


def conversation_with_data(request, employee_number=None):
    # Search json
    emp_data = ''
    request_messages = request.json["messages"]
    _query = request_messages[-1].get('content')
    _search_words = [w.strip().lower() for w in _query.split()]

    if not is_manager_personal_info(_search_words) and is_user(_query, _search_words):
        search_dicts = search_json(_query, employee_number)
        if search_dicts:
            search_results = []
            search_values = []
            open_ai_message = 'find more information for '
            for d in search_dicts:
                for k, v in d.items():
                    if 'description' == k:
                        search_results.append(v)
                        if 'messageToOpenAI' not in d:
                            open_ai_message = f"{open_ai_message}, {v} and"
                    elif 'messageToOpenAI' == k:
                        open_ai_message = v
                    elif 'keywords' != k and 'score' != k and 'isResponseMultiple' != k:
                        search_values.append(v)

            _result = ''
            if len(search_results) >= 1:
                first_val = str(search_results[0])
                if len(search_results) == 1:
                    _result = first_val
                else:
                    _result = f"{first_val.strip()}, {', '.join(search_results[1:-1])} and {search_results[-1].strip()}"
                # Added by Datta
                return Response(stream_static_content_data(_result.strip()), mimetype='text/event-stream')

            # if find_in_value(USER_DETAILS_KEYS, _search_words):
            #     emp_data = _result
            #     text = ''
            #     if len(search_values) >= 1:
            #         f_val = str(search_values[0])
            #         if len(search_values) == 1:
            #             text = f_val
            #         else:
            #             text = f"{f_val.strip()}, {', '.join(search_values[1:-1])} and {search_values[-1].strip()}"
            #
            #     request_messages[-1].update({'content': open_ai_message.format(text=text)})
            # else:
            #     return Response(stream_static_content_data(_result.strip()), mimetype='text/event-stream')

    body, headers = prepare_body_headers_with_data(request)
    endpoint = f"https://{AZURE_OPENAI_RESOURCE}.openai.azure.com/openai/deployments/{AZURE_OPENAI_MODEL}/extensions/chat/completions?api-version={AZURE_OPENAI_API_VERSION}"

    if not SHOULD_STREAM:
        r = requests.post(endpoint, headers=headers, json=body)
        status_code = r.status_code
        r = r.json()

        return Response(json.dumps(r).replace("\n", "\\n"), status=status_code)
    else:
        if request.method == "POST":
            return Response(stream_with_data(body, headers, endpoint, emp_data), mimetype='text/event-stream')
        else:
            return Response(None, mimetype='text/event-stream')


def is_manager_personal_info(_search_words):
    return len(find_in_value(EXCLUSION_KEYS_1, _search_words)) > 1 and len(
        find_in_value(EXCLUSION_KEYS_2, _search_words)) > 0


def is_user(query, _search_words):
    if len(find_in_value(USER_KEYS_1, _search_words)) > 0:
        return True
    else:
        for key in USER_KEYS_2:
            if key.lower() in query.lower():
                return True

    return False


def stream_without_data(response):
    response_text = ""
    for line in response:
        delta_text = line["choices"][0]["delta"].get('content')
        if delta_text and delta_text != "[DONE]":
            response_text += delta_text

        response_obj = {
            "id": line["id"],
            "model": line["model"],
            "created": line["created"],
            "object": line["object"],
            "choices": [{
                "messages": [{
                    "role": "assistant",
                    "content": response_text
                }]
            }]
        }
        yield json.dumps(response_obj).replace("\n", "\\n") + "\n"


def conversation_without_data(request):
    openai.api_type = "azure"
    openai.api_base = f"https://{AZURE_OPENAI_RESOURCE}.openai.azure.com/"
    openai.api_version = "2023-03-15-preview"
    openai.api_key = AZURE_OPENAI_KEY

    request_messages = request.json["messages"]
    messages = [
        {
            "role": "system",
            "content": AZURE_OPENAI_SYSTEM_MESSAGE
        }
    ]

    for message in request_messages:
        messages.append({
            "role": message["role"],
            "content": message["content"]
        })

    response = openai.ChatCompletion.create(
        engine=AZURE_OPENAI_MODEL,
        messages=messages,
        temperature=float(AZURE_OPENAI_TEMPERATURE),
        max_tokens=int(AZURE_OPENAI_MAX_TOKENS),
        top_p=float(AZURE_OPENAI_TOP_P),
        stop=AZURE_OPENAI_STOP_SEQUENCE.split("|") if AZURE_OPENAI_STOP_SEQUENCE else None,
        stream=SHOULD_STREAM
    )

    if not SHOULD_STREAM:
        response_obj = {
            "id": response,
            "model": response.model,
            "created": response.created,
            "object": response.object,
            "choices": [{
                "messages": [{
                    "role": "assistant",
                    "content": response.choices[0].message.content
                }]
            }]
        }

        return jsonify(response_obj), 200
    else:
        if request.method == "POST":
            return Response(stream_without_data(response), mimetype='text/event-stream')
        else:
            return Response(None, mimetype='text/event-stream')


@app.route("/api/conversation/azure_byod", methods=["GET", "POST"])
def conversation_azure_byod():
    try:
        use_data = should_use_data()
        if use_data:
            return conversation_with_data(request)
        else:
            return conversation_without_data(request)
    except Exception as e:
        logging.exception("Exception in /api/conversation/azure_byod")
        return jsonify({"error": str(e)}), 500


@app.route("/api/conversation/custom/<employee_number>", methods=["GET", "POST"])
def conversation_custom(employee_number):
    # try:
    #     use_data = should_use_data()
    #     if use_data:
    #         return conversation_with_data(request, employee_number)
    # except Exception as e:
    #     logging.exception("Exception in /api/conversation/azure_byod")
    #     return jsonify({"error": str(e)}), 500

    from backend.utilities.helpers.OrchestratorHelper import Orchestrator
    message_orchestrator = Orchestrator()

    try:
        user_message = request.json["messages"][-1]['content']
        _search_words = [w.strip().lower() for w in user_message.split()]
        employee_data = {'original_user_message': user_message}
        if not is_manager_personal_info(_search_words) and is_user(user_message, _search_words):
            search_dicts = search_json(user_message, employee_number)
            if search_dicts:
                search_results = []
                search_values = []
                questions_to_search_engine = []
                open_ai_message = 'find more information for '
                for d in search_dicts:
                    for key, value in d.items():
                        if 'description' == key:
                            search_results.append(value)
                            if 'messageToOpenAI' not in d:
                                open_ai_message = f"{open_ai_message}, {value} and"
                        elif 'messageToOpenAI' == key:
                            open_ai_message = value
                        elif 'keywords' != key and 'score' != key and 'isResponseMultiple' != key:
                            search_values.append(value)
                            questions_to_search_engine.append(f"What are the details of {value}?")

                if len(questions_to_search_engine) > 1:
                    employee_data['questions_to_search_engine'] = questions_to_search_engine

                _result = ''
                if len(search_results) >= 1:
                    first_val = str(search_results[0])
                    if len(search_results) == 1:
                        _result = first_val
                    else:
                        _result = f"{first_val.strip()}, {', '.join(search_results[1:-1])} and {search_results[-1].strip()}"

                if find_in_value(USER_DETAILS_KEYS, _search_words):
                    employee_data['employee_data'] = _result.strip()
                    # emp_data = _result
                    text = ''
                    if len(search_values) >= 1:
                        f_val = str(search_values[0])
                        if len(search_values) == 1:
                            text = f_val
                        else:
                            search_values = [s for s in search_values if type(s) is not dict]
                            text = f"{f_val.strip()}, {', '.join(search_values[1:-1])} and {search_values[-1].strip()}"
                    # request_messages[-1].update({'content': open_ai_message.format(text=text)})
                    if text:
                        user_message = open_ai_message.format(text=text)
                else:
                    return Response(stream_static_content_data(_result.strip()), mimetype='text/event-stream')

        conversation_id = request.json["conversation_id"]
        user_assistant_messages = list(
            filter(lambda x: x['role'] in ('user', 'assistant'), request.json["messages"][0:-1]))
        chat_history = []
        for i, k in enumerate(user_assistant_messages):
            if i % 2 == 0:
                chat_history.append((user_assistant_messages[i]['content'], user_assistant_messages[i + 1]['content']))
        from backend.utilities.helpers.ConfigHelper import ConfigHelper

        messages = message_orchestrator.handle_message(user_message=user_message, chat_history=chat_history,
                                                       conversation_id=conversation_id,
                                                       orchestrator=ConfigHelper.get_active_config_or_default().orchestrator,
                                                       **employee_data)

        response_obj = {
            "id": "response.id",
            "model": os.getenv("AZURE_OPENAI_MODEL"),
            "created": "response.created",
            "object": "response.object",
            "choices": [{
                "messages": messages
            }]
        }

        return jsonify(response_obj), 200

    except Exception as e:
        logging.exception("Exception in /api/conversation/custom")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run()
