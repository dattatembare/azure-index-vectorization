import json
import os

PROJECT_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
EMPLOYEE_DATA_DIR = 'data/employee'
EMPLOYEE_CONFIG_DIR = 'backend/utilities/employee_data'
USER_KEYS_1 = ['my', 'myself', 'mine', "I'm", 'am']
USER_KEYS_2 = ['am I', 'do I', 'have I', 'PTO balance', 'PTO policy balance', 'time-off balance', 'timeoff balance',
               'PTO Plan', 'PTO policy', 'time-off plan', 'timeoff plan']
USER_DETAILS_KEYS = ['detail', 'details', 'detailed', 'info', 'information', 'more', 'best', 'buy', 'change', 'bestbuy']
EXCLUSION_KEYS_1 = ["my", "manager's", "managers", "colleague's", "colleagues", "co-worker's", "coworker's",
                    "co-workers", "coworkers", "all", "available", "best", "buy", "bestbuy"]
EXCLUSION_KEYS_2 = ["pto", "balance", "timeoff", "time", "time-off", "off"]
REPLACE_KEYS = {"time-off": "time off", "who's": "who is"}


# _files = os.listdir(f'{PROJECT_ROOT_DIR}')

def get_json(file_path):
    with open(file_path) as f_in:
        employee_dict = json.load(f_in)
    return employee_dict


employee_config = get_json(f'{PROJECT_ROOT_DIR}/{EMPLOYEE_CONFIG_DIR}/employee.json')
tlc_data = get_json(f'{PROJECT_ROOT_DIR}/{EMPLOYEE_DATA_DIR}/tlc_data.json')