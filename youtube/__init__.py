# -*- coding: utf-8 -*-

'''Query and open YouTube videos and channels.

Synopsis: <trigger> <query>'''

import json
import re
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from albert import (Item, UrlAction, critical, iconLookup, info)  # pylint: disable=import-error


__title__ = 'Youtube'
__version__ = '0.4.1'
__triggers__ = 'yt '
__authors__ = 'manuelschneid3r'
__icon__ = iconLookup('youtube')  # path.dirname(__file__) + '/icons/YouTube.png'

DATA_REGEX = re.compile(r'^\s*(var\s|window\[")ytInitialData("\])?\s*=\s*(.*)\s*;\s*$', re.MULTILINE)

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36'
    )
}


def log_html(html):
    log_time = time.strftime('%Y%m%d-%H%M%S')
    log_name = 'albert.plugins.youtube_dump'
    log_path = Path(f'/tmp/{log_name}-{log_time}.html')

    with log_path.open('wb') as sr:
        sr.write(html)

    critical(f'The HTML output has been dumped to {log_path}')
    critical('If the page looks ok in a browser, please include the dump in a new issue:')
    critical('  https://www.github.com/albertlauncher/albert/issues/new')


def text_from(val):
    text = val['simpleText'] if 'runs' not in val else ''.join(str(v['text']) for v in val['runs'])

    return text.strip()


def entry_to_item(type_, data):
    match type_:
        case 'videoRenderer':
            subtext = ['Video']
            action = 'Watch on Youtube'
            link = f'watch?v={data["videoId"]}'
            if 'lengthText' in data:
                subtext.append(text_from(data['lengthText']))
            if 'shortViewCountText' in data:
                subtext.append(text_from(data['shortViewCountText']))
            if 'publishedTimeText' in data:
                subtext.append(text_from(data['publishedTimeText']))
        case 'channelRenderer':
            subtext = ['Channel']
            action = 'Show on Youtube'
            link = f'channel/{data["channelId"]}'
            if 'videoCountText' in data:
                subtext.append(text_from(data['videoCountText']))
            if 'subscriberCountText' in data:
                subtext.append(text_from(data['subscriberCountText']))
        case _:
            return None

    thumbnails = data['thumbnail']['thumbnails']
    return Item(
        id=__title__,
        icon=thumbnails[0]['url'].split('?', 1)[0] if thumbnails else __icon__,
        text=text_from(data['title']),
        subtext=' | '.join(subtext),
        actions=[UrlAction(action, 'https://www.youtube.com/' + link)],
    )


def handleQuery(query):
    if not query.isTriggered or not query.string.strip():
        return None

    # Avoid rate limiting
    time.sleep(0.2)
    if not query.isValid:
        return None

    info(f'Searching YouTube for \'{query.string}\'')
    url = f'https://www.youtube.com/results?{urlencode({"search_query": query.string.strip()})}'
    req = Request(headers=HEADERS, url=url)

    with urlopen(req) as response:
        response_bytes = response.read()
        match = re.search(DATA_REGEX, response_bytes.decode())
        if match is None:
            critical(
                'Failed to receive expected data from YouTube. This likely means API changes, but could just be a '
                'failed request.'
            )
            log_html(response_bytes)
            return None

        results = json.loads(match.group(3))
        primary_contents = results['contents']['twoColumnSearchResultsRenderer']['primaryContents']
        results = primary_contents['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents']
        items = []
        for result in results:
            for type_, data in result.items():
                try:
                    item = entry_to_item(type_, data)
                    if not item:
                        continue
                    items.append(item)
                except KeyError as e:
                    critical(e)
                    critical(json.dumps(result, indent=4))
        return items
