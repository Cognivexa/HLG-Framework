---
name: youtube-transcript
description: Given a YouTube URL, fetches the video's subtitle track and reformats it into clean, readable text while preserving timestamps at natural paragraph breaks. It removes caption artifacts like repeated filler and auto-caption noise.
argument-hint: [youtube-url]
---

# YouTube Transcript

Turns a wall of auto-generated captions into a readable transcript, instead of a jumble of timestamped fragments.

## Input

$ARGUMENTS

## How It Works

1. Extract the video ID from the supplied URL and fetch the available subtitle track.
2. Prefer manually created captions over auto-generated ones when both exist.
3. Merge fragmented caption lines into coherent sentences and paragraphs.
4. Strip filler artifacts such as repeated words and auto-caption noise markers.
5. Insert timestamp markers at paragraph breaks so sections remain navigable.