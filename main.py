import os
import re

from dataclasses import dataclass

from datetime import timedelta


@dataclass
class Item:
    title: str
    url: str
    duration: timedelta


hours_pattern = re.compile(r"(\d+)H")
minutes_pattern = re.compile(r"(\d+)M")
seconds_pattern = re.compile(r"(\d+)S")


def parse_args():
    import argparse

    parser = argparse.ArgumentParser(
        description="YouTube Playlist Formatter",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--playlist",
        type=str,
        required=True,
        help="YouTube Playlist ID",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=os.environ.get("YT_API_KEY"),
        required=False,
        help="YouTube API Key. If none is provided, the YT_API_KEY environment variable will be used.",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=("md", "csv"),
        default="md",
        required=False,
        help="Output format.",
    )
    parser.add_argument(
        "--include-total-duration",
        action="store_true",
        required=False,
        help="Include total duration of playlist.",
    )

    return parser.parse_args()


def get_api_handler(api_key):
    from googleapiclient.discovery import build

    return build("youtube", "v3", developerKey=api_key)


def get_video_ids(handler, playlist_id):
    video_ids = []

    nextPageToken = None
    while True:
        pl_request = handler.playlistItems().list(
            part="contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=nextPageToken,
        )

        pl_response = pl_request.execute()

        items = pl_response["items"]
        video_ids.extend([item["contentDetails"]["videoId"] for item in items])

        nextPageToken = pl_response.get("nextPageToken")

        if not nextPageToken:
            break

    return video_ids


def get_video_details(handler, video_ids):
    if isinstance(video_ids, str):
        video_ids = [video_ids]
    if isinstance(video_ids, list):
        video_ids = ",".join(video_ids)

    vid_request = handler.videos().list(
        part="snippet,contentDetails",
        id=video_ids,
    )

    vid_response = vid_request.execute()

    return vid_response["items"]


def _extract_duration(item):
    duration = item["contentDetails"]["duration"]

    hours = hours_pattern.search(duration)
    minutes = minutes_pattern.search(duration)
    seconds = seconds_pattern.search(duration)

    hours = int(hours.group(1)) if hours else 0
    minutes = int(minutes.group(1)) if minutes else 0
    seconds = int(seconds.group(1)) if seconds else 0

    return timedelta(hours=hours, minutes=minutes, seconds=seconds)


def _extract_title(item):
    return item["snippet"]["title"]


def _create_link(video_id):
    return f"https://www.youtube.com/watch?v={video_id}"


def get_total_duration(items):
    return sum([item.duration for item in items], timedelta())


def create_item(item, video_id):
    return Item(
        title=_extract_title(item),
        url=_create_link(video_id),
        duration=_extract_duration(item),
    )


def create_markdown_table(items):
    table = "| Title | Duration |\n"
    table += "| :--- | :---: |\n"

    for item in items:
        table += f"| [{item.title}]({item.url}) | {item.duration} |\n"

    return table


def main(args):
    handler = get_api_handler(args.api_key)

    video_ids = get_video_ids(handler, args.playlist)
    video_details = get_video_details(handler, video_ids)

    items = [
        create_item(item, video_id) for item, video_id in zip(video_details, video_ids)
    ]

    if args.include_total_duration:
        items.append(
            Item(
                title="Total Duration",
                url="",
                duration=get_total_duration(items),
            )
        )

    if args.format == "md":
        print(create_markdown_table(items))
    elif args.format == "csv":
        print("title,url,duration")
        for item in items:
            print(f'"{item.title}",{item.url},{item.duration}')


if __name__ == "__main__":
    args = parse_args()
    main(args)
