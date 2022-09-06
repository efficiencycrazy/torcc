# -*- coding: utf-8 -*-
"""
A script parse the info page of a torrent and add torrent to the qbit client.
parse detail page to get imdb/douban id.
"""
import re
import argparse
import requests
from http.cookies import SimpleCookie
import urllib
import qbittorrentapi
import feedparser
import datetime

from humanbytes import HumanBytes
# from lxml import etree

DOWNLOAD_URL_RE = [
    r'https?://(\w+\.)?\w+\.\w+/download\.php\?id=(\d+)&downhash=(\w+)',
    r'https?://(\w+\.)?\w+\.\w+/download\.php\?id=(\d+)&passkey=(\w+)',
]


def rssGetDetailAndDownload(rsslink):
    feed = feedparser.parse(rsslink)
    rssSum = 0
    for item in feed.entries:
        if not hasattr(item, 'id'):
            print('No id')
            continue
        if not hasattr(item, 'title'):
            print('No title')
            continue

        rssSum += 1
        print("%d: %s -- %s " % (rssSum, item.title, datetime.datetime.now().strftime("%H:%M:%S")))

        if ARGS.regex:
            if not re.search(ARGS.regex, item.title, re.I):
                print(' Regex skip.')
                continue

        imdbstr = ''
        if hasattr(item, 'link'):
            if ARGS.cookie:
                imdbstr, downlink = parseDetailPage(item.link, ARGS.cookie)

        if hasattr(item, 'links') and len(item.links) > 1:
            rssDownloadLink = item.links[1]['href']
            rssSize = item.links[1]['length']
            # Download
            print('   %s (%s), %s' % (imdbstr, HumanBytes.format(int(rssSize)), rssDownloadLink))
            if ARGS.host and ARGS.username:
                r = addQbitWithTag(rssDownloadLink, imdbstr)
    print('Total: %d ' % rssSum)


def addQbitWithTag(downlink, imdbtag):
    qbClient = qbittorrentapi.Client(host=ARGS.host, port=ARGS.port, username=ARGS.username, password=ARGS.password)

    try:
        qbClient.auth_log_in()
    except qbittorrentapi.LoginFailed as e:
        print(e)

    if not qbClient:
        return False

    try:
        # curr_added_on = time.time()
        result = qbClient.torrents_add(
            urls=downlink,
            is_paused=False,
            # save_path=download_location,
            # download_path=download_location,
            # category=timestamp,
            tags=[imdbtag],
            use_auto_torrent_management=False)
        # breakpoint()
        if 'OK' in result.upper():
            print('Torrent added.')
        else:
            print('Torrent not added! something wrong with qb api ...')
    except Exception as e:
        print('Torrent not added! Exception: '+str(e))
        return False

    return True

    

def findConfig(infoUrl):
    hostnameList = urllib.parse.urlparse(infoUrl).netloc.split('.')
    abbrev = hostnameList[-2] if len(hostnameList) >= 2 else ''
    return next(filter(lambda ele: ele['host'] == abbrev, SITE_CONFIGS), None)
    # for i in range(len(SITE_CONFIGS)):
    #     if SITE_CONFIGS[i]['host'] == abbrev:
    #         return SITE_CONFIGS[i]
    # return None


def parseDetailPage(pageUrl, pageCookie):
    cookie = SimpleCookie()
    cookie.load(pageCookie)
    cookies = {k: v.value for k, v in cookie.items()}
    headers = {
        'User-Agent':
        'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
    }

    doc = requests.get(pageUrl, headers=headers, cookies=cookies).text

    # thisConfig = findConfig(pageUrl)
    # if not thisConfig:
    #     return None, None
    imdbstr = ''
    imdbRe = r'IMDb(链接)\s*(\<.[!>]*\>)?.*https://www\.imdb\.com/title/tt(\d+)'
    m1 = re.search(imdbRe, doc, flags=re.A)
    if m1:
        imdbstr = 'tt' + m1[3]
    # print(doc)

    for reUrl in DOWNLOAD_URL_RE:
        if re.search(reUrl, doc, flags=re.A):
            break
    # downlinkRe = thisConfig['downlinkRe']
    downlink = ''
    m2 = re.search(reUrl, doc, flags=re.A)
    if m2:
        downlink = m2[0]

    return imdbstr, downlink
    # html = etree.parse(doc, etree.HTMLParser())
    # lilist = html.xpath('//*[@id="torrent_dl_url"]/a')
    # print(lilist)


def loadArgs():
    parser = argparse.ArgumentParser(
        description=
        'torcp: a script hardlink media files and directories in Emby-happy naming and structs.'
    )
    parser.add_argument('-H', '--host', help='the qbittorrent host ip.')
    parser.add_argument('-P', '--port', help='the qbittorrent port.')
    parser.add_argument('-u', '--username', help='the qbittorrent usernmae.')
    parser.add_argument('-p', '--password', help='the qbittorrent password.')
    parser.add_argument('-R', '--rss', help='the rss link.')
    parser.add_argument('-i', '--info-url', help='the detail page contains imdb/douban id.')
    parser.add_argument('-c', '--cookie', help='the cookie to the detail page.')
    parser.add_argument('--regex', help='regex to match the rss title.')
    global ARGS
    ARGS = parser.parse_args()


def main():
    loadArgs()
    if ARGS.rss:
        rssGetDetailAndDownload(ARGS.rss)

    elif ARGS.info_url:
        if ARGS.cookie:
            imdbstr, downlink = parseDetailPage(ARGS.info_url, ARGS.cookie)
            if not (imdbstr and downlink):
                print("Error")
                return
            print(imdbstr, downlink)
            # Download
            r = addQbitWithTag(downlink, imdbstr)


if __name__ == '__main__':
    main()