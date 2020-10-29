import argparse
import logging
import json
import requests
import os
import csv
from os import path
from sys import stdout
from datetime import datetime
import tldextract
import timeout_decorator
from bs4 import BeautifulSoup


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


def get_domain(target):
    '''
    Extracts the domain of target url
    :param target: The url to extract the domain of
    :return: Extracted domain
    '''
    return tldextract.extract(target).domain


def get_base_url(target):
    tld_obj = tldextract.extract(target)
    if 'https' in target:
        return 'https://www.{0}.{1}/'.format(tld_obj.domain, tld_obj.suffix)
    else:
        return 'http://www.{0}.{1}/'.format(tld_obj.domain, tld_obj.suffix)


def get_elementdata(urlid, dataid, tagstring, soup):
    '''
    Gets data for specified element
    :param urlid: The urlid of the element
    :param dataid: The dataid of the element
    :param tagstring: The tagstring describing the element and the specific content of the element
    :param soup: Reference to BeautifulSoup object
    :return: List of dictionaries with element data
    '''
    logger = logging.getLogger(__name__ + '.get_elementdata')
    ret = []
    element_name = tagstring.split(':')[0]
    for item in soup.find_all(element_name):
        if ':' not in tagstring:
            logger.debug('Scanning: {}-text'.format(element_name))
            ret.append({'URLID': urlid, 'DataID': dataid, 'element': element_name, 'target': item.text})
        else:
            targets = tagstring.split(':')[-1]
            for target in targets.split(','):
                if target == 'text':
                    logger.debug('Scanning: {}-text'.format('a'))
                    ret.append({'URLID': urlid, 'DataID': i - 1, 'element': 'a', 'target': ele.text})
                    continue
                logger.debug('Scanning: {0}-{1}'.format(element_name, target))
                try:
                    ret.append({'URLID': urlid, 'DataID': dataid, 'element': element_name, 'target': item['target']})
                except KeyError:
                    logger.debug('Element error: Could not find element data. Omitting')
    return ret


def get_linkdata(urlid, elementlist, ele):
    '''
    Get element data exclusively for 'a' tags (links)
    :param urlid: The urlid of the element
    :param elementlist: The list of elements on the input json string
    :param ele: Reference to BeautifulSoup object
    :return: List of dictionaries with element data
    '''
    logger = logging.getLogger(__name__ + '.getlinkdata')
    ret = []
    for i, tagstring in enumerate(elementlist):
        if 'a:' in tagstring:
            if ':' not in tagstring:
                logger.debug('Scanning: {}-text'.format('a'))
                ret.append({'URLID': urlid, 'DataID': i, 'element': 'a', 'target': ele.text})
            else:
                targets = tagstring.split(':')[-1]
                for target in targets.split(','):
                    if target == 'text':
                        logger.debug('Scanning: {}-text'.format('a'))
                        ret.append({'URLID': urlid, 'DataID': i, 'element': 'a', 'target': ele.text})
                        continue
                    logger.debug('Scanning: {0}-{1}'.format('a', target))
                    try:
                        ret.append({'URLID': urlid, 'DataID': i, 'element': 'a', 'target': ele['href']})
                    except KeyError:
                        logger.debug('Element ERROR: Could not find element data. Omitting')
        else:
            logger.debug('Could not find tag')
    return ret


def connect_with_timeout(url, headers):
    return requests.get(url, headers=headers)


def update_csv(id, savedir, write_data, datatype, runcnt):
    logger = logging.getLogger(__name__ + '.update_csv')
    logger.debug('Writing to csv. Runcount = {0}, Type: {1}'.format(runcnt, datatype))
    if not isinstance(write_data, list):
        write_data = [write_data]
    if len(write_data) == 0:
        logger.warning('Nothing to write')
    else:
        if datatype == 'element':
            save_file = 'tempData-[{}].csv'.format(id)
        elif datatype == 'url':
            save_file = 'tempUrl-[{}].csv'.format(id)
        else:
            raise Exception('Unknown type')
        check_create_dir(savedir)
        with open(path.join(savedir, save_file), 'a') as writefile:
            writer = csv.DictWriter(writefile, fieldnames=list(write_data[0].keys()) + ['error'], restval='n/a')
            if runcnt == 0:
                logger.debug('Writing header')
                writer.writeheader()
            for ele in write_data:
                if ele.get('target', None) is not None and '\n' in ele['target']:
                    ele['target'] = ele['target'].replace('\n', 'N%%L')
                writer.writerow(ele)


def update_status(filename, dat):
    check_create_dir('status')
    if depth is not None:
        with open(path.join('status', filename), 'w') as f:
            json.dump(dat, f)


if __name__ == "__main__":
    print('PageMiner')
    # Init arguments
    parser = argparse.ArgumentParser(description='Scrape test')
    parser.add_argument('data', type=str)
    args = parser.parse_args()
    if '.json' in args.data:
        with open(args.data, 'r') as f:
            data = json.load(f)
    else:
        data = json.loads(args.data)

    # Init logging
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.DEBUG)
    consoleHandler = logging.StreamHandler(stdout)
    consoleHandler.setFormatter(logging.Formatter('[%(name)s] - %(levelname)s - %(message)s'))
    check_create_dir('logs')
    fileHandler = logging.FileHandler(
        path.join('logs', 'Scraper{0}.log'.format(datetime.now().strftime('%d-%m-%y-%H-%M-%S'))))
    fileHandler.setFormatter(logging.Formatter('%(asctime)s:-[%(name)s] - %(levelname)s - %(message)s'))
    consoleHandler.setLevel(logging.INFO)
    rootLogger.addHandler(consoleHandler)
    fileHandler.setLevel(logging.DEBUG)
    rootLogger.addHandler(fileHandler)

    # If some files already exist, find latest ID
    working_urls = []
    status = None
    contscrape = False
    contitem = False
    cont_depth = None
    cont_urls = None
    cont_urlid = None
    valid_ids = [ele['ID'] for ele in data['runURL']]
    present_ids = []
    try:
        for filename in os.listdir('status'):
            fileid = filename[int(filename.index('[') + 1): int(filename.index(']'))]
            present_ids.append(fileid)
        if len(present_ids) > 0:
            latest_id = max(present_ids)
            with open(path.join('status', 'status-[{}].json'.format(latest_id)), 'r') as f:
                status = json.load(f)
            if isinstance(status['urls'], list):
                # General case: Last or not last depth but not last entry
                rootLogger.info('Existing urls found, continuing scrape')
                working_urls = data['runURL'][int(status['id']):]
                cont_depth = status['depth']
                cont_urls = status['urls']
                cont_urlid = 1
            else:
                if status['urls'] == 'Full Complete':
                    if latest_id == int(data['runURL'][-1]['ID']):
                        # The entry with scraping completed is the last entry in the file
                        rootLogger.info('All entries complete. Exiting')
                        exit(0)
                    else:
                        # The entry with scraping completed is not the last entry in the file
                        working_urls = data['runURL'][status['id'] + 1:]
                        cont_depth = 0
                        cont_urls = 'init'
                        cont_urlid = 1
                else:
                    # Error case
                    raise Exception('Invalid value for urls in status file')
        else:
            raise FileNotFoundError
    except FileNotFoundError:
        rootLogger.info('No existing files found. Starting from the beginning')
        contscrape = False
        working_urls = data['runURL']

    for urlindex, item in enumerate(working_urls):
        rootLogger.info('Item level Index: {0}, Id: {1}'.format(urlindex, item['ID']))
        # Init variables
        eleruncnt = 0
        linkruncnt = 0
        start_time = datetime.now()
        priority_strings = data['pstrings'].split(',')
        urlid = 1
        urls = [(0, item['URL'])]
        depth = 0
        all_urls = []
        home_domain = get_domain(item['URL'])
        base_url = get_base_url(item['URL'])
        if contscrape:
            rootLogger.info('Contscrape triggered')
            depth = cont_depth
            if cont_urls == 'init':
                urls = [(0, item['URL'])]
            else:
                urls = cont_urls
            urlid = cont_urlid
            contscrape = False
        statusfile = 'status-[{}].json'.format(item['ID'])
        statusdict = {'depth': depth, 'urls': None}
        # Check for depth limit
        while depth <= data['depth']:
            rootLogger.info('Depth level depth: {0}, urls: {1}'.format(depth, urls))
            new_urls = []
            rootLogger.info('------------------------ Depth {} -------------------------'.format(depth))

            # Priority check: Find websites with specific keywords in them and push them to top of list
            rootLogger.info('Starting priority check...')
            for cnt, uele in enumerate(urls):
                if any(pstr in uele[1].lower() for pstr in priority_strings):
                    rootLogger.info('Priority link found: {}'.format(uele[1]))
                    rootLogger.info('Moving to top')
                    del urls[cnt]
                    urls.insert(0, uele)

            rootLogger.info('Starting scrape process')
            for urlno, (uid, url) in enumerate(urls):
                rootLogger.info('urls level urlno: {0}, ele: {1}'.format(urlno, (uid, url)))
                rootLogger.info('Connecting to: {}'.format(url))
                try:
                    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
                                             ' (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36'}
                    head_response = requests.head(url, headers=headers)
                    if head_response.headers['content-type'].split(';')[0] != 'text/html':
                        rootLogger.info(
                            'Skipping due to invalid mime type: {}'.format(head_response.headers['content-type']))
                        continue
                    response = connect_with_timeout(url, headers)
                    soup = BeautifulSoup(response.text, 'html.parser')
                except StopIteration:
                    rootLogger.error('Connection timeout error. Omitting')
                    ele_write_data = {'URLID': uid, 'url': url, 'depth': depth,
                         'Connection error': 'The website was connected to but it took too long to retrieve data.'}
                    update_csv(item['ID'], data['saveFileDir'], ele_write_data, 'element', eleruncnt)
                    eleruncnt += 1
                    continue
                except Exception as exc:
                    rootLogger.error('Connection error: {}  Omitting'.format(exc))
                    ele_write_data = {'URLID': uid, 'url': url, 'depth': depth, 'Connection error': str(exc)}
                    update_csv(item['ID'], data['saveFileDir'], ele_write_data, 'element', eleruncnt)
                    eleruncnt += 1
                    continue
                # Link search routine
                for ele in soup.find_all('a'):
                    if data.get('limit', None) is not None and len(new_urls) == data['limit']:
                        # 'limit' entry on the input json is used only for debug purposes.
                        # This part is omitted when not included.
                        break
                    # Make sure element points to valid link
                    if ele.get('href', None) is not None:
                        try:
                            raw_link = ele['href'].strip()
                            if 'http' not in raw_link:
                                if raw_link.startswith('/'):
                                    processed_url = (base_url + raw_link[1:]).strip()
                                    if processed_url not in all_urls:
                                        urlid += 1
                                        rootLogger.info('Adding to new_urls: {}'.format((urlid, processed_url)))
                                        new_urls.append((urlid, processed_url))
                                        all_urls.append(processed_url)
                                        url_write_data = {'URLID': urlid, 'depth': depth, 'url': processed_url}
                                        update_csv(item['ID'], data['saveFileDir'], url_write_data, 'url', linkruncnt)
                                        linkruncnt += 1
                                        # If 'a' is present in HTMLElementList, add its data onto element_data
                                        ele_write_data = get_linkdata(uid, data['HTMLElementList'], ele)
                                        update_csv(item['ID'], data['saveFileDir'], ele_write_data,
                                                   'element', eleruncnt)
                                        eleruncnt += 1

                                else:
                                    processed_url = (base_url + raw_link).strip()
                                    if processed_url not in all_urls:
                                        urlid += 1
                                        rootLogger.info('Adding to new_urls: {}'.format((urlid, processed_url)))
                                        new_urls.append((urlid, processed_url))
                                        all_urls.append(processed_url)
                                        url_write_data = {'URLID': urlid, 'depth': depth, 'url': processed_url}
                                        update_csv(item['ID'], data['saveFileDir'], url_write_data, 'url', linkruncnt)
                                        linkruncnt += 1
                                        ele_write_data = get_linkdata(uid, data['HTMLElementList'], ele)
                                        update_csv(item['ID'], data['saveFileDir'],
                                                   ele_write_data,
                                                   'element', eleruncnt)
                                        eleruncnt += 1
                            else:
                                processed_url = raw_link.strip()
                                if processed_url not in all_urls:
                                    urlid += 1
                                    all_urls.append(processed_url)
                                    if data['scrapeSameDomain']:
                                        if get_domain(raw_link) == home_domain:
                                            rootLogger.info('Adding to new_urls: {}'.format((urlid, processed_url)))
                                            new_urls.append((urlid, processed_url))
                                            url_write_data = {'URLID': urlid, 'depth': depth, 'url': processed_url}
                                            update_csv(item['ID'], data['saveFileDir'], url_write_data, 'url', linkruncnt)
                                            linkruncnt += 1
                                    else:
                                        rootLogger.info('Adding to new_urls: {}'.format((urlid, processed_url)))
                                        new_urls.append((urlid, processed_url))
                                        url_write_data = {'URLID': urlid, 'depth': depth, 'url': processed_url}
                                        update_csv(item['ID'], data['saveFileDir'], url_write_data, 'url', linkruncnt)
                                        linkruncnt += 1
                                    ele_write_data = get_linkdata(uid, data['HTMLElementList'], ele)
                                    update_csv(item['ID'], data['saveFileDir'],
                                               ele_write_data,
                                               'element', eleruncnt)
                                    eleruncnt += 1
                        except StopIteration:
                            rootLogger.error('Connection timeout error. Omitting')
                            element_write_data = {'URLID': uid, 'url': url, 'depth': depth, 'Connection error':
                                                  'The website was connected to but it took too long to retrieve data.'}
                            update_csv(item['ID'], data['saveFileDir'], element_write_data, 'element', eleruncnt)
                            eleruncnt += 1
                            continue
                # Find other elements
                for i, element in enumerate(data['HTMLElementList']):
                    # 'a' is omitted here since it is handled with the previous routine
                    if 'a:' not in element:
                        ele_write_data = get_elementdata(uid, i, element, soup)
                        update_csv(item['ID'], data['saveFileDir'], ele_write_data, 'element', eleruncnt)
                        eleruncnt += 1

                # Update Status
                statusdict['depth'] = depth
                statusdict['id'] = item['ID']
                statusdict['urls'] = list()
                statusdict['contid'] = -1
                rootLogger.info('Begin status save')
                if depth == data['depth']:
                    if urlno == (len(urls) - 1):
                        # Last depth last entry
                        rootLogger.info('All entries scraped')
                        statusdict['urls'] = 'Full Complete'
                    else:
                        # Last depth but not last entry
                        rootLogger.info('Current depth incomplete')
                        statusdict['urls'].extend(urls[urlno + 1:])
                else:
                    if urlno == (len(urls) - 1):
                        # Not last depth but last entry
                        rootLogger.info('Current depth fully scraped')
                        statusdict['urls'] = new_urls
                        statusdict['contid'] = urlid + 1
                        statusdict['depth'] += 1
                    else:
                        # Not last depth or last entry
                        rootLogger.info('Current depth incomplete')
                        statusdict['urls'].extend(urls[urlno + 1:])
                rootLogger.info('Writing to status file')
                update_status(statusfile, statusdict)

            rootLogger.info('new_urls before transfer: {}'.format(new_urls))
            urls = []
            urls.extend(new_urls)
            depth += 1
        rootLogger.info('Total time taken for scrape: {} minute(s)'.format(((datetime.now() - start_time).seconds/60)))