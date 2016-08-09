import datetime


class Media:

    def __init__(self, media: dict):
        self.display_url = media.get("display_url")
        self.id = media.get("id")
        self.media_url = media.get("media_url_https")
        self.url = media.get("url")


class Hashtag:

    def __init__(self, hashtag: dict):
        self.text = hashtag.get("text")


class Url:
    def __init__(self, url: dict):
        self.display_url = url.get("display_url")
        self.expanded_url = url.get("expanded_url")


class ExtendedEntity:
    def __init__(self, extended_entities: dict):
        self.media = [Media(media) for media in extended_entities.get("media")]


class Entity:
    def __init__(self, entity: dict):
        self.hashtags = [Hashtag(hashtag) for hashtag in entity.get("hashtags")]
        self.media = [Media(media) for media in entity.get("media")]
        self.url = [Url(url) for url in entity.get("urls")]


class Metadata:

    def __init__(self, search_metadata: dict):
        self.count = search_metadata.get("count")
        self.max_id = search_metadata.get("max_id")
        self.next_results = search_metadata.get("next_results")


class Status:

    DATE_FORMAT = "%a %b %d %H:%M:%S %z %Y"

    def __init__(self, status: dict):
        self.id = status.get("id")
        self.created_at = self._to_datetime(status.get("created_at"))
        self.extended_entity = ExtendedEntity(status.get("extended_entities"))
        self.entity = Entity(status.get("entities"))

    def _to_datetime(self, created_at):
        try:
            return datetime.datetime.strptime(created_at, self.DATE_FORMAT)
        except (ValueError, TypeError):
            return created_at


class TwitterResponse:

    def __init__(self, response: dict):
        self.statuses = []

        self.metadata = Metadata(response.get("search_metadata"))

        self.statuses = [Status(status) for status in response.get("statuses")
                         if status.get("extended_entities")]

    def __iter__(self):
        self._start = 0
        self._count = len(self.statuses)
        return self

    def __next__(self):
        if self._count == self._start:
            raise StopIteration
        self._start += 1
        return self.statuses[self._start - 1]
