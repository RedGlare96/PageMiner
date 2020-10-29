import json
import os
from os import path


def check_create_dir(dirname):
    '''
    Checks if directory exists and if it doesn't creates a new directory
    :param dirname: Path to directory
    '''
    if not path.exists(dirname):
        if '/' in dirname:
            os.makedirs(dirname)
        else:
            os.mkdir(dirname)


if __name__ == '__main__':
    instances = int(input('Instances: '))
    input_file = input('Target: ')
    pstrings = input('Priority Strings: ')
    with open(input_file, 'r') as f:
        input_json = json.load(f)
    num_sites = len(input_json['runURL'])
    print('Total sites: {}'.format(num_sites))
    output_template = {key: value for key, value in input_json.items() if key != 'runURL' and key != 'limit'}
    output_template['runURL'] = list()
    output_template['pstrings'] = pstrings
    num_files = int(num_sites/instances)
    instance_index = 1
    prev_index = 0
    check_create_dir('run-instances')
    while instance_index <= instances:
        render_template = output_template
        if instance_index == instances:
            render_template['runURL'] = input_json['runURL'][prev_index:]
        else:
            render_template['runURL'] = input_json['runURL'][prev_index: prev_index + num_files]
        with open(path.join('run-instances', 'run{}.json'.format(instance_index)), 'w') as f:
            json.dump(render_template, f)
        prev_index += num_files
        instance_index += 1
