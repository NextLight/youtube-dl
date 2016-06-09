# coding: utf-8
from __future__ import unicode_literals

from .common import InfoExtractor

import re


class VvvvidBaseIE(InfoExtractor):
    def _real_initialize(self):
        self.conn_id = self._download_json('https://www.vvvvid.it/user/login', None)['data']['conn_id']

    def get_episodes(self, show_id, season_id, format_suffix='', format_note=''):
        def get_real_manifest_url(url):
            if 'akamaihd' in url:
                return "%s?hdcore=3.6.0" % url
            else:
                return "http://wowzaondemand.top-ix.org/videomg/_definst_/mp4:%s/manifest.f4m" % url

        for d in self._download_json(
            "https://www.vvvvid.it/vvvvid/ondemand/%s/season/%s?conn_id=%s" % (show_id, season_id, self.conn_id), None
        )['data']:
            ret = {
                'id': str(d['video_id']),
                'series': d['show_title'],
                'title': "%s %s - %s" % (d['show_title'], d['number'], d['title']),
                'season_id': season_id,
                'season_number': d['season_number'],
                'episode': d['title'],
                'episode_number': int(d['number']),
                'episode_id': d['id'],
                'thumbnail': d['thumbnail'],
                'formats': []
            }
            fid = iter(['sd', 'hd'])
            for f in (d.get('embed_info_sd'), d.get('embed_info')):
                if f is not None:
                    # TODO: extract from manifest only if listing formats ?
                    info = self._extract_f4m_formats(get_real_manifest_url(f), d['video_id'])[0]
                    info['format_id'] = next(fid) + format_suffix
                    info['format_note'] = format_note
                    ret['formats'].append(info)
            yield ret


class VvvvidIE(VvvvidBaseIE):
    IE_NAME = 'vvvvid'
    _VALID_URL = r'^https?://(?:www\.)?vvvvid\.it/#!show/(?P<show_id>[0-9]+)/.+?/(?P<season_id>[0-9]+)/(?P<id>[0-9]+)'
    _TEST = {
        'url': 'https://www.vvvvid.it/#!show/372/ping-pong/373/482337/il-vento-copre-tutti-i-suoni',
        'info_dict': {
            'id': '482337',
            'ext': 'flv',
            'title': 'Ping Pong 01 - Il vento copre tutti i suoni',
            'thumbnail': 'https://static.vvvvid.it/img/thumbs/Dynit/PingPong/PingPong_Ep01-t.jpg'
        }
    }

    def _real_extract(self, url):
        m = re.match(self._VALID_URL, url)
        show_id = m.group('show_id')
        season_id = m.group('season_id')
        video_id = m.group('id')
        return next(d for d in self.get_episodes(show_id, season_id) if d['id'] == video_id)


class VvvvidShowPlaylistIE(VvvvidBaseIE):
    IE_NAME = 'vvvvid:playlist'
    _VALID_URL = r'^https?://(?:www\.)?vvvvid\.it/#!show/(?P<id>[0-9]+)/[^/]+?/?$'
    _TEST = {
        'url': 'https://www.vvvvid.it/#!show/114/l-attacco-dei-giganti',
        'info_dict': {
            'id': '114'
        },
        'playlist_count': 25
    }

    def _real_extract(self, url):
        show_id = self._match_id(url)
        seasons = [s for s in self._download_json(
            "https://www.vvvvid.it/vvvvid/ondemand/%s/seasons?conn_id=%s" % (show_id, self.conn_id), None
        )['data'] if s['name'].lower() != 'extra']
        if len(seasons) == 1:
            episodes = list(self.get_episodes(show_id, seasons[0]['season_id']))
            return self.playlist_result(episodes, show_id, episodes[0]['series'])

        ja = self.get_episodes(show_id, next(s for s in seasons if 'giapponese' in s['name'].lower())['season_id'], '-ja', 'Jap sub Ita')
        it = self.get_episodes(show_id, next(s for s in seasons if 'italiano' in s['name'].lower())['season_id'], '-it', 'Ita')

        def merge_formats(f_ja, f_it):
            ret = dict(f_ja, **f_it)
            ret['id'] = f_ja['id'] + '-' + f_it['id']
            ret['formats'].extend(f_ja['formats'])
            return ret

        episodes = map(merge_formats, ja, it)
        return self.playlist_result(episodes, show_id, episodes[0]['series'])
