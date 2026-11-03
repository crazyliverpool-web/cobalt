"""Discover new videos via YouTube's public RSS feed (no API key needed)."""
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import certifi

_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "media": "http://search.yahoo.com/mrss/",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}


@dataclass
class VideoEntry:
    video_id: str
    title: str
    published: str
    url: str


def fetch_recent_videos(channel_id: str, limit: int = 10) -> list[VideoEntry]:
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    req = urllib.request.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15, context=_SSL_CONTEXT) as resp:
        content = resp.read()

    root = ET.fromstring(content)
    entries = []
    for entry in root.findall("atom:entry", NS)[:limit]:
        video_id = entry.find("yt:videoId", NS).text
        title = entry.find("atom:title", NS).text
        published = entry.find("atom:published", NS).text
        url = f"https://www.youtube.com/watch?v={video_id}"
        entries.append(VideoEntry(video_id=video_id, title=title, published=published, url=url))
    return entries
