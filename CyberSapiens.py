import streamlit as st
import yt_dlp
import requests
from PIL import Image
from io import BytesIO
import os
from urllib.parse import urlparse, parse_qs
import time
from pathlib import Path
import re


def get_youtube_id(url):
    """Extract YouTube video ID from URL"""
    if 'youtu.be' in url:
        return url.split('/')[-1]
    elif 'youtube.com' in url:
        query = parse_qs(urlparse(url).query)
        return query.get('v', [None])[0]
    return None


def get_video_info(url):
    """Get video information using yt-dlp"""
    try:
        ydl_opts = {
            'format': 'best',
            'extract_flat': True,
            'no_warnings': True,
            'quiet': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                'title': info.get('title', 'Unknown Title'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'description': info.get('description', 'No description available'),
                'uploader': info.get('uploader', 'Unknown uploader'),
                'view_count': info.get('view_count', 0),
            }
    except Exception as e:
        st.error(f"Error fetching video info: {str(e)}")
        return None


def setup_download_folders():
    """Create downloads folders if they don't exist"""
    downloads_path = Path.home() / "Downloads" / "StreamlitDownloads"
    video_path = downloads_path / "Videos"
    image_path = downloads_path / "Images"

    for path in [downloads_path, video_path, image_path]:
        path.mkdir(parents=True, exist_ok=True)

    return str(video_path), str(image_path)


def is_video_url(url):
    """Check if the URL is likely a video URL"""
    video_domains = ['youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com']
    parsed_url = urlparse(url)
    return any(domain in parsed_url.netloc for domain in video_domains)


def is_image_url(url):
    """Check if the URL points to an image"""
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    parsed_url = urlparse(url)
    return any(parsed_url.path.lower().endswith(ext) for ext in image_extensions)


def format_duration(seconds):
    """Format duration in seconds to HH:MM:SS"""
    if not seconds:
        return "Unknown duration"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def format_views(view_count):
    """Format view count with K, M, B suffixes"""
    if not view_count:
        return "No views"
    if view_count < 1000:
        return str(view_count)
    elif view_count < 1000000:
        return f"{view_count / 1000:.1f}K"
    elif view_count < 1000000000:
        return f"{view_count / 1000000:.1f}M"
    return f"{view_count / 1000000000:.1f}B"


def download_video(url, output_path):
    """Download video using yt-dlp"""
    try:
        ydl_opts = {
            'format': 'best',
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'progress_hooks': [lambda d: st.session_state.update(
                progress=d['downloaded_bytes'] / d['total_bytes'] if 'total_bytes' in d else 0
            ) if d['status'] == 'downloading' else None],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            st.session_state.progress = 0
            info = ydl.extract_info(url, download=True)
            return True, f"Successfully downloaded: {info['title']}"
    except Exception as e:
        return False, f"Error downloading video: {str(e)}"


def download_image(url, output_path):
    """Download image using requests"""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()

        filename = os.path.basename(urlparse(url).path)
        if not filename:
            filename = f"image_{int(time.time())}.jpg"

        filepath = os.path.join(output_path, filename)

        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024

        with open(filepath, 'wb') as f:
            if total_size == 0:
                f.write(response.content)
            else:
                downloaded = 0
                for data in response.iter_content(block_size):
                    downloaded += len(data)
                    f.write(data)
                    st.session_state.progress = downloaded / total_size

        return True, f"Successfully downloaded: {filename}"
    except Exception as e:
        return False, f"Error downloading image: {str(e)}"


def main():
    st.set_page_config(page_title="Media Downloader & Player", layout="wide")

    st.title("🌐 Online Media Downloader & Player")
    st.write("Enter a URL to preview and download videos or images")

    if 'progress' not in st.session_state:
        st.session_state.progress = 0

    video_path, image_path = setup_download_folders()

    with st.expander("Download Locations"):
        st.write(f"Videos will be saved to: {video_path}")
        st.write(f"Images will be saved to: {image_path}")

    url = st.text_input("Enter URL:")

    if url:
        if is_video_url(url):
            # Video preview section
            col1, col2 = st.columns([2, 1])

            with col1:
                youtube_id = get_youtube_id(url)
                if youtube_id:
                    st.components.v1.iframe(
                        f"https://www.youtube.com/embed/{youtube_id}",
                        height=400,
                        scrolling=False
                    )

            with col2:
                video_info = get_video_info(url)
                if video_info:
                    st.subheader(video_info['title'])
                    st.write(f"👤 {video_info['uploader']}")
                    st.write(f"⏱️ {format_duration(video_info['duration'])}")
                    st.write(f"👁️ {format_views(video_info['view_count'])} views")

                    if st.button("Download Video"):
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        status_text.text("Downloading video...")
                        success, message = download_video(url, video_path)
                        progress_bar.progress(1.0 if success else 0)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)

        elif is_image_url(url):
            try:
                response = requests.get(url)
                image = Image.open(BytesIO(response.content))
                st.image(image, caption="Image Preview", use_column_width=True)

                if st.button("Download Image"):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    status_text.text("Downloading image...")
                    success, message = download_image(url, image_path)
                    progress_bar.progress(1.0 if success else 0)
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
            except Exception as e:
                st.error(f"Error loading image preview: {str(e)}")

        else:
            st.warning("Unsupported URL format. Please enter a valid video or image URL.")

    # Display downloads
    with st.expander("View Downloads"):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📹 Videos")
            for file in sorted(os.listdir(video_path)):
                st.write(file)

        with col2:
            st.subheader("🖼️ Images")
            for file in sorted(os.listdir(image_path)):
                st.write(file)



if __name__ == "__main__":
    main()