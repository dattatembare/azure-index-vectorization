import json
import os

PROJECT_ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
EMPLOYEE_DATA_DIR = 'data/employee'
EMPLOYEE_CONFIG_DIR = 'backend/utilities/employee_data'
USER_KEYS = ['me', 'my', 'myself', 'mine']
USER_DETAILS_KEYS = ['detail', 'details', 'detailed', 'info', 'information', 'more']


# _files = os.listdir(f'{PROJECT_ROOT_DIR}')

def get_json(file_path):
    with open(file_path) as f_in:
        employee_dict = json.load(f_in)
    return employee_dict


employee_config = get_json(f'{PROJECT_ROOT_DIR}/{EMPLOYEE_CONFIG_DIR}/employee.json')
