---
name: youtube-downloader
description: Downloads YouTube videos and their subtitles with configurable resolution, format, and audio-only options, handling both single videos and full playlists. It manages format selection and output naming so batches of downloads stay organized.
argument-hint: [youtube-url-or-playlist]
---

# YouTube Downloader

Turns a YouTube link into a saved file on disk, instead of a page you can only watch once.

## Input

$ARGUMENTS

## How It Works

1. Parse the given URL to detect whether it points to a single video or a playlist.
2. Query available formats and resolve the requested quality and container format.
3. Fetch the video stream and, where available, the subtitle track in the requested language.
4. Name and organize output files consistently, numbering playlist entries in order.
5. Report any videos that failed to download along with the reason.