import re
from datetime import datetime

from eds_util import PROJECT_ROOT_DIR, EMPLOYEE_DATA_DIR, employee_config, get_json, tlc_data, REPLACE_KEYS


def search_json(query: str, employee_number=None):
    print(f'Query: {query}')
    employee_dict = get_json(f'{PROJECT_ROOT_DIR}/{EMPLOYEE_DATA_DIR}/{employee_number}.json')
    # remove special characters from query
    query = re.sub(r'[^a-z0-9 ]', '', query.strip().lower())
    query = replace_words(query)
    result_list = dict_lookup(query, employee_dict, employee_config)
    if len(result_list) > 0:
        result_list = sorted(result_list, key=lambda i: i['score'])
        last_dict = result_list[-1]
        score = last_dict.get('score')
        high_score_result_list = []
        for d in result_list:
            if d.get('score') >= score:
                high_score_result_list.append(d)

        pto_balance_keywords = employee_config.get("absence").get("ptoBalance").get("keywords")
        is_balance_exist = True if len({w.strip().lower() for w in query.split()} & set(pto_balance_keywords)) > 1 else False
        return get_final_result(employee_number, high_score_result_list, is_balance_exist)
    else:
        return {}


def replace_words(query):
    for k, v in REPLACE_KEYS.items():
        query = query.replace(v, k)

    return query


def get_final_result(employee_number, high_score_result_list, is_balance_exist):
    _tlc = {}
    if is_balance_exist:
        _tlc = tlc_data.get(str(employee_number))
        _tlc_details = "\n\n"
        if _tlc:
            _tlc_details = "as per information available in TLC system"
        if _tlc and int(_tlc.get('floating_holiday')) > 0:
            _tlc_details = f"{_tlc_details}, Floating Holidays {_tlc.get('floating_holiday')}"
        if _tlc and int(_tlc.get('reward_time')) > 0:
            _tlc_details = f"{_tlc_details}, Reward time is {_tlc.get('reward_time')}"
        if _tlc and int(_tlc.get('caregiver')) > 0:
            _tlc_details = f"{_tlc_details}, Caregiver is {_tlc.get('caregiver')}"
        if _tlc and int(_tlc.get('unpaid_protected_time')) > 0:
            _tlc_details = f"{_tlc_details}, Unpaid Protected Time is {_tlc.get('unpaid_protected_time')}"
        if _tlc and int(_tlc.get('pay_continuation')) > 0:
            _tlc_details = f"{_tlc_details}, pay continuation is {_tlc.get('pay_continuation')}"
        if _tlc and int(_tlc.get('mandated_time')) > 0:
            _tlc_details = f"{_tlc_details}, mandated time is {_tlc.get('mandated_time')}"

    is_printable = False
    final_result_list = []
    for d in high_score_result_list:
        if 'miscellaneous' not in d and not (len(high_score_result_list) > 1
                                             and 'sickPlanEligibility' in d
                                             and 'not eligible' == d.get('sickPlanEligibility').lower()):
            final_result_list.append(d)

            # Add TLC data
            if is_balance_exist:
                if 'sickPlanBalance' in d:
                    is_printable = True
                    _sick_balance = 0
                    if _tlc and int(_tlc.get('sick')) > 0:
                        _sick_balance = _tlc.get('sick')
                    elif _tlc and int(_tlc.get('sick_leave')) > 0:
                        _sick_balance = _tlc.get('sick_leave')
                    _tlc_details = f"{_tlc_details}, sick leave balance is {_sick_balance} " \
                                   f"and sick bank (carry forward sick leave) balance is {_tlc.get('sickb')}"
                if 'ptoBalance' in d:
                    is_printable = True
                    _tlc_details = f"{_tlc_details}, PTO balance is {_tlc.get('pto')}"
                if 'vacationBalance' in d:
                    is_printable = True
                    _tlc_details = f"{_tlc_details}, Vacation balance is {_tlc.get('vacation')}"

    if is_balance_exist and is_printable:
        final_result_list.append({'description': _tlc_details})

    return final_result_list


def dict_lookup(query: str, employee_dict: dict, config: dict, result_list=None):
    if result_list is None:
        result_list = []

    _search_words = {w.strip().lower() for w in query.split()}
    _search_words.add(query)

    # check if miscellaneous have more matches
    if 'miscellaneous' in config:
        miscellaneous_keywords = {c.lower() for c in config.get('miscellaneous').get('keywords')}
        mis_count = len(_search_words & miscellaneous_keywords)
        if mis_count > 0:
            result_list.append(create_dict(config, 'miscellaneous', 'miscellaneous', _search_words, mis_count))

    _unprocessed_value_dict = []

    for key, value in employee_dict.items():
        if key in config:
            if 'keywords' not in config.get(key):
                _unprocessed_value_dict.append((query, value, config.get(key)))
            else:
                _keywords = {c.lower() for c in config.get(key).get('keywords')}
                if len(_search_words & _keywords) > 0:
                    result_list.append(create_dict(config, key, value, _search_words, len(_search_words & _keywords)))
                elif type(value) is not dict and len(find_in_value(_search_words, value)) > 0:
                    result_list.append(create_dict(config, key, value, _search_words))

    for tup in _unprocessed_value_dict:
        _que, _dic, _con = tup
        get_absence_data(_dic)
        dict_lookup(_que, _dic, _con, result_list)

    return result_list


def get_absence_data(_dic):
    # this condition checks if this is absence dictionary
    if 'eligibleToPurchasePto' in _dic:
        if 'eligible' != _dic.get('eligibleToPurchasePto', '').strip().lower():
            del _dic['purchasedPtoBalance']
        if 'not eligible' == _dic.get('sickPlanEligibility', '').strip().lower():
            del _dic['sickPlanBalance']
        if 'vacation' in _dic.get('timeOffPlanType', '').strip().lower():
            del _dic['ptoBalance']
        else:
            del _dic['vacationBalance']
        # Change date format to Month dd, YYYY
        _r_date = _dic.get('ptoRefreshDate')
        _r_date = datetime.strptime(_r_date[:_r_date.rfind('-')], '%Y-%m-%d')
        _dic['ptoRefreshDate'] = _r_date.strftime('%B %d, %Y')


def score_calculation(key_config, search_words, score):
    for score_word in key_config.get('score'):
        is_match_found = False
        if score_word in search_words:
            is_match_found = True
        else:
            for word in search_words:
                if score_word in word:
                    is_match_found = True

        if is_match_found:
            score = score + 1
        else:
            score = score - 1

    return score


def create_dict(config, key, value, search_words, score=1):
    score = score_calculation(config.get(key), search_words, score) if 'score' in config.get(key) else score
    # TODO - if score = 0 then check if we can not add that dictionary
    _new_dict = {'score': score, key: value}
    _config_dict = config.get(key)
    aggr_dict = {**_config_dict, **_new_dict}

    _desc = aggr_dict.get('description')
    if 'isResponseMultiple' in config.get(key):
        _val = '_'.join([v for v in str(value).strip().lower().split()])
        if 'sickPlanEligibility' == key:
            is_eligibility_check = len(search_words & {'eligible', 'eligibility'}) > 0
            if 'not_eligible' == _val:
                _desc = f"{_desc.get('no')}" if is_eligibility_check else _desc.get('not_eligible')
            else:
                _desc = f"{_desc.get('yes')}" if is_eligibility_check else f"{_desc.get('eligible')}"
        else:
            _desc = _desc.get(_val)
    else:
        if type(value) == dict:
            value = ' '.join([str(v) for v in value.values()])
    aggr_dict['description'] = _desc.format(value=value)

    return aggr_dict


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
