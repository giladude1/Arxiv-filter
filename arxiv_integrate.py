import urllib.request as libreq
import feedparser
import PyPDF2
from config import *
from dominate import document
from dominate.tags import *
from datetime import date, datetime
import os, collections, configparser, ast, time


def run_query(category):
    # input is the search category and maximum results of the query
    # returns a feed object with query results, ordered by latest
    query = config['Main']['query']
    max_results = config.getint('Main', 'MAX_QUERY_ENTRIES')
    in_query = query.format(max_results=max_results, category=category)
    with libreq.urlopen(in_query) as url:
        response = url.read()
    feed = feedparser.parse(response)
    return feed


def get_pdf_link_from_entry(entry):
    links = entry['links']
    for link_object in links:
        if 'pdf' in link_object['type']:
            return link_object['href']
    return 'NO PDF FILE'


def extract_relevant_entries_from_feed(feed):
    # input is a parsed atom feed (from arxiv query)
    # return list of entries (arxiv format) with pdf containing at least one keyword
    good_entries = []
    error_entries = []
    show_updates = config.getboolean('Main', 'SHOW_UPDATES')
    abstract_keywords = ast.literal_eval(config['Main']['ABSTRACT_KEYWORDS'])
    max_page_amount = config.getint('Main', 'MAX_PAGE_AMOUNT')
    search_words = ast.literal_eval(config['Main']['SEARCH_WORDS'])
    timeout_interval = config.getint('Main', 'TIMEOUT_INTERVAL')
    timeout_attempts = config.getint('Main', 'TIMEOUT_ATTEMPTS')
    for i, entry in enumerate(feed['entries']):

        if i % 20 == 0 and i != 0:
            print('finished %d entries out of %d' % (i, len(feed['entries'])))

        #  check whether the paper is a new release
        if not show_updates:
            if entry['updated'] != entry['published']:
                continue

        #  check abstract keywords
        if len(abstract_keywords) > 0:
            abstract_keyword_flag = check_abstract_keywords(entry['summary'], abstract_keywords)
            if not abstract_keyword_flag:
                continue

        #  check the pdf
        error_with_pdf_flag = False
        pdf_link = get_pdf_link_from_entry(entry)
        printed_entry_flag = False
        for attempt in range(timeout_attempts):
            try:
                with libreq.urlopen(pdf_link, timeout=timeout_interval) as url:
                    response = url.read()
                    break
            except Exception as e:
                if 'timed out' in str(e):
                    if not printed_entry_flag:
                        print(entry['title'])
                        printed_entry_flag = True
                    print('TIMEOUT ATTEMPT %d OUT OF %d' % (attempt + 1, timeout_attempts))
                    if attempt == timeout_attempts - 1:
                        error_entries.append(entry)
                        error_with_pdf_flag = True
                else:
                    print('problem with the paper: ', entry['title'])
                    print(e)
                    error_entries.append(entry)
                    error_with_pdf_flag = True

        if error_with_pdf_flag:
            continue

        with open('temp.pdf', 'wb') as output_file:
            output_file.write(response)
        try:
            with open('temp.pdf', 'rb') as pdf_file:
                reader = PyPDF2.PdfFileReader(pdf_file, strict=False)
                page_amount = reader.numPages
                text = ''
                for page in range(min(page_amount, max_page_amount)):
                    text += reader.getPage(page).extractText()
                if check_whether_entry_is_relevant(text, search_words):
                    good_entries.append(entry)
        except Exception as e:
            print('problem with the paper: ', entry['title'])
            print(e)
            error_entries.append(entry)

    if os.path.exists('temp.pdf'):
        os.remove('temp.pdf')
    return good_entries, error_entries


def check_whether_entry_is_relevant(text, search_words):
    for word in search_words:
        if text.count(word) >= search_words[word]:
            return True
    return False


def check_abstract_keywords(text, abstract_keywords):
    abstract_keyword_flag = False
    for word in abstract_keywords:
        if word in text:
            abstract_keyword_flag = True
            break
    return abstract_keyword_flag


def print_entries_to_html(entries, error_entries, category):
    # input is a list of entries (arxiv format)
    # create an html file formatted with all the entries
    with document(title='tryout') as doc:
        h3('Found %d relevant papers out of %d' % (len(entries), config.getint('Main', 'MAX_QUERY_ENTRIES')))
        for entry in entries:
            add_entry_to_html(entry)
        if len(error_entries) > 0:
            h3('Had an error with %d papers' % len(error_entries))
            for entry in error_entries:
                add_entry_to_html(entry)
    output_path = os.path.join(config['Main']['OUTPUT_HTML'], category +  '_' + str(date.today()) + '.html')
    with open(output_path, 'w', encoding='utf-8') as output_html:
        output_html.write(doc.render())


def add_entry_to_html(entry):
    h1(entry['title'])
    authors_string = ''
    for author in entry['authors']:
        authors_string += author['name'] + ', '
    h3(authors_string)
    p('published: ', entry['published'], ' updated: ', entry['updated'])
    h4('Abstract:')
    p(entry['summary'])
    a('abstract', href=entry['links'][0]['href'])
    a('pdf', href=entry['links'][1]['href'])


def run_arxiv_filter(category):

    # use arxiv api
    feed = run_query(category)
    extracted_amount = len(feed['entries'])
    print('Extracted %d entries from Arxiv' % extracted_amount)

    # extract relevant entries
    relevant_entries, error_entries = extract_relevant_entries_from_feed(feed)
    print('Found %d relevant entries' % len(relevant_entries))
    print('Had an Error with %d entries' % len(error_entries))

    # output relevant entries in html format
    print_entries_to_html(relevant_entries, error_entries, category)
    print('Finished')
    time.sleep(5)

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read(os.path.join(os.getcwd(), 'settings.ini'))
    categories = ast.literal_eval(config['Main']['GROUP'])
    for category in categories:
        run_arxiv_filter(category)
