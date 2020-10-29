import subprocess
import os
from os import path

if __name__ == '__main__':
    print('Running Instances...')
    try:
        for ele in os.listdir('run-instances'):
            print('Running: {}'.format(path.join('run-instances', ele)))
            subprocess.run(['nohup', 'python3', 'pageminer.py', path.join('run-instances', ele), '&'])
    except FileNotFoundError:
        print('File not found! Check directory')
        exit(-1)