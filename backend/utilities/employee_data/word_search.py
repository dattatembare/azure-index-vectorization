import re

from eds_util import PROJECT_ROOT_DIR, EMPLOYEE_DATA_DIR, employee_config, get_json


def search_json(query: str, employee_number=6004104):
    print(f'Query: {query}')
    employee_dict = get_json(f'{PROJECT_ROOT_DIR}/{EMPLOYEE_DATA_DIR}/{employee_number}.json')
    # remove special characters from query
    query = re.sub(r'[^a-z0-9 ]', '', query.strip().lower())
    result_list = dict_lookup(query, employee_dict, employee_config)
    # print(f'result_list: {result_list}')
    result_dict = {}
    if result_list is None or len(result_list) == 0:
        return result_dict
    elif len(result_list) > 0:
        result_list = sorted(result_list, key=lambda i: i['size'])
        last_dict = result_list[-1]
        matches = last_dict.get('size')
        final_result_list = []
        for d in result_list:
            if d.get('size') >= matches:
                del d['size']
                final_result_list.append(d)
        return final_result_list


def dict_lookup(query: str, employee_dict: dict, config: dict, result_list=None):
    if result_list is None:
        result_list = []
    _unprocessed_value_dict = []
    _search_words = [w.strip().lower() for w in query.split()]
    for key, value in employee_dict.items():
        if key in config:
            _config_key_words = [c.lower() for c in config.get(key) if type(config.get(key)) is not dict]
            if len(_search_words) == 1 and query in key.lower():
                if type(value) is not dict:
                    result_list.append({'size': 1, key: value})
                else:
                    _unprocessed_value_dict.append((query, value, config.get(key)))
            elif len(_search_words) == 1 and query in str(value).lower():
                if type(value) is not dict:
                    result_list.append({'size': 1, key: value})
                else:
                    _unprocessed_value_dict.append((query, value, config.get(key)))
            elif type(config.get(key)) is not dict and len(set(_search_words) & set(_config_key_words)) > 0:
                if type(value) is not dict:
                    # print(f'matches: {set(_search_words) & set(_config_key_words)} - {key}:{value}')
                    result_list.append({'size': len(set(_search_words) & set(_config_key_words)), key: value})
                else:
                    result_list.append({'size': 1, key: value})
            elif type(config.get(key)) is dict:
                _unprocessed_value_dict.append((query, value, config.get(key)))
            elif type(value) is not dict:
                res = find_in_value(_search_words, value)
                if len(res) > 0:
                    result_list.append({'size': 1, key: value})

    for tup in _unprocessed_value_dict:
        _que, _dic, _con = tup
        dict_lookup(_que, _dic, _con, result_list)

    return result_list


def find_in_value(_search_words, value):
    _search_words_boundary = [fr'\b{w}\b' for w in _search_words]
    r_str = fr"{'|'.join(_search_words_boundary)}"
    r = re.compile(r_str, flags=re.I | re.X)
    res = r.findall(str(value))
    return res

# if __name__ == '__main__':
#     questions = [
#         'What is plan 1?',
#         'What is my pto plan?',
#         'What is my pto balance?',
#         'Am I eligible to purchase pto?',
#         'Find my manager details',
#         'I want to talk to hr',
#         'What is my employment status?',
#         'How often I get paid?',
#         'What is my pay schedule?',
#         'What is my home address on records?'
#     ]
#     [print(f'Result: {search_json(question)} \n') for question in questions]
# _result = search_json(question)
# print(f'Result: {_result}')
