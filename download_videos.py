import requests

def get_playlist_api(playlist_url, quality):
    data = requests.get("https://api.youtubemultidownloader.com/playlist?url=" + playlist_url).json()['items']
    videos_data = dict()
    cnt = 1
    for item in data:
        videos_data["video_"+str(cnt)] = get_video_api(item['url'], quality)
        cnt += 1

    return videos_data

def get_video_api(video_url, quality):
    data = requests.get("https://api.youtubemultidownloader.com/video?url=" + video_url).json()['format']

    width = 0
    if quality == 720:
        width = 1280
    elif quality == 360:
        width = 640

    for video_type in data:
        if video_type['size'] == 0 and (video_type["height"] == quality or video_type['width'] == width):
            return video_type

    return False


# def get_videos():
#     all_data = get_playlist_api("https://www.youtube.com/playlist?list=PLDoPjvoNmBAw4eOj58MZPakHjaO3frVMF", 360)
#     for key,values in all_data.items():
#         print(key)
#         for value in values:
#             print(value)
#
# get_videos()