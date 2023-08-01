from pytube import YouTube, Playlist
# from youtube_dl import YoutubeDL
from urllib import parse
from youtube_transcript_api import YouTubeTranscriptApi


def get_time_style(seconds, for_srt=False):
    hours, minutes, seconds = [seconds // 3600, (seconds % 3600) // 60, seconds % 60]
    if hours < 10 : hours = "0" + str(int(hours))
    if minutes < 10 : minutes = "0" + str(int(minutes))
    if seconds < 10 :
        seconds = "0" + str(format(round(seconds, 3), ".3f") if for_srt else round(seconds, 3))
    else:
        seconds = format(round(seconds, 3), ".3f") if for_srt else round(seconds, 3)
        seconds = str(seconds).replace(".", ",")
    str_duration = str(hours) + ":" + str(minutes) + ":" + seconds
    return str_duration

def fetch_playlist_title(playlist_url):
    return Playlist(playlist_url).title

def fetch_video_title(video_url):
    return YouTube(video_url).title

def fetch_video_id(video_url):
    try:
        return YouTube(video_url).video_id
    except:
        return False


def search_video_stream(video_streams, video_title, quality):
    video_download_url = False
    for stream in video_streams:
        if stream["qualityLabel"] == str(quality) + "p":
            video_download_url = stream["url"]
            video_download_url += "&title=" + parse.quote_plus(video_title).replace("+", " ")
            break
        video_download_url = False
    return video_download_url

def search_audio_stream(audio_streams, video_title, quality=None):
    audio_download_url = False
    for stream in audio_streams:
        audio_download_url = stream.url
        audio_download_url += "&title=" + parse.quote_plus(video_title).replace("+", " ")
        break
    return audio_download_url


def get_video_download_link(yt_url, quality, just_url=False, is_playlist=True):
    if is_playlist:
        try:
            playlist_data = Playlist(yt_url)
            playlist_title = playlist_data.title
            videos = []
            video_urls = playlist_data.video_urls
            for video_url in video_urls :
                videos.append(YouTube(video_url))
            download_urls = []
        except Exception as error:
            video_download_url = False
            video_title = "False"
            print("====== Error in Getting Playlist Data ======")
            print(error)
            if just_url:
                return video_download_url
            return video_title, video_download_url

        for video in videos:
            try:
                video_streams = video.streaming_data["formats"]
                video_download_url = search_video_stream(video_streams, video.title, quality)
                download_urls.append(video_download_url)
            except Exception as error:
                print("====== Error in Getting Video Data in a Playlist ======")
                print(error)
        return download_urls, playlist_title

    else:
        try:
            video = YouTube(yt_url)
            streams = video.streams.filter(progressive=True)
            video_download_url = False
            video_title = "False"
            for stream in streams:
                if stream.resolution == str(quality) + "p":
                    video_download_url = stream.url
                    video_download_url += "&title=" + parse.quote_plus(stream.title)
                    video_title = stream.title
                    break
        except Exception as error:
            video_download_url = False
            video_title = "False"
            print("====== Error in Getting Video Data ======")
            print(error)

    if just_url:
        return video_download_url
    return video_title, video_download_url


def get_audio_download_link(yt_url, just_url=False, is_playlist=True):
    if is_playlist:
        try:
            playlist_data = Playlist(yt_url)
            playlist_title = playlist_data.title
            videos = []
            video_urls = playlist_data.video_urls
            for video_url in video_urls:
                videos.append(YouTube(video_url))
            download_urls = []
        except Exception as error:
            video_download_url = False
            video_title = "False"
            print("====== Error in Getting Playlist Data ======")
            print(error)
            if just_url:
                return video_download_url
            return video_title, video_download_url

        for video in videos:
            try:
                audio_streams = video.streams.filter(abr="128kbps", mime_type="audio/mp4")
                audio_download_url = search_audio_stream(audio_streams, video.title)
                download_urls.append(audio_download_url)
            except Exception as error:
                print("====== Error in Getting Audio Data in a Playlist ======")
                print(error)
        return download_urls, playlist_title

    else:
        audio_download_url = False
        video_title = "False"
        try:
            video = YouTube(yt_url)
            audio_streams = video.streams.filter(abr="128kbps", mime_type="audio/mp4")
            audio_download_url = search_audio_stream(audio_streams, video.title)
            video_title = video.title
        except Exception as error:
            video_download_url = False
            video_title = "False"
            print("====== Error in Getting Video Data ======")
            print(error)

        if just_url:
            return audio_download_url
        return video_title, audio_download_url


def get_srt_file(video_id, filename, lang='en'):
    try:
        captions = YouTubeTranscriptApi.list_transcripts(video_id).find_transcript([lang]).fetch()
        srt_file = open(filename+".srt", "w")
        for index in range(len(captions) - 1):
            # Prepare data to write
            caption_data = captions[index]
            row_num = index + 1
            start = get_time_style(caption_data["start"], for_srt=True)
            end = get_time_style(captions[index + 1]["start"], for_srt=True)
            caption = caption_data["text"]

            # writing in file
            srt_file.write(str(row_num) + "\n")
            srt_file.write(f"{start} --> {end}" + "\n")
            srt_file.write(caption + "\n")
            srt_file.write("\n")

        # preparing and writing last caption
        cap_row = str(len(captions))
        cap_start = get_time_style(captions[-1]["start"], for_srt=True)
        cap_end = get_time_style(float(captions[-1]["start"]) + float(captions[-1]["duration"]), for_srt=True)
        cap_text = captions[-1]["text"]
        srt_file.write(cap_row + "\n")
        srt_file.write(f"{cap_start} --> {cap_end}" + "\n")
        srt_file.write(cap_text + "\n")

        # closing srt file
        srt_file.close()

        return True

    except Exception as error :
        print(f"==== Error in Getting {lang} Caption for Video With ID: {video_id} ====")
        # print(error)
        return False
