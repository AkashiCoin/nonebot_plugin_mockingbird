import re
import httpx
from io import BytesIO
from typing import Optional
from pydub import AudioSegment
from pydub.silence import detect_silence


async def get_ai_voice(text, type=0) -> Optional[BytesIO]:
    mp3_url = await get_ai_voice_url(text, type)
    if not mp3_url:
        return None

    async with httpx.AsyncClient() as client:
        resp = await client.get(mp3_url)
        result = resp.content

    return await split_voice(BytesIO(result))


async def get_ai_voice_url(text, type=0) -> str:
    url = "https://cloud.ai-j.jp/demo/aitalk_demo.php"
    if type == 0:
        params = {
            "callback": "callback",
            "speaker_id": 555,
            "text": text,
            "ext": "mp3",
            "volume": 2.0,
            "speed": 1,
            "pitch": 1,
            "range": 1,
            "webapi_version": "v5",
        }
    else:
        params = {
            "callback": "callback",
            "speaker_id": 1214,
            "text": text,
            "ext": "mp3",
            "volume": 2.0,
            "speed": 1,
            "pitch": 1,
            "range": 1,
            "anger": 0,
            "sadness": 0,
            "joy": 0,
            "webapi_version": "v5",
        }

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params)
        result = resp.text

    match_obj = re.search(r'"url":"(.*?)"', result)
    if match_obj:
        mp3_url = "https:" + match_obj.group(1).replace(r"\/", "/")
        return mp3_url
    return ""


async def split_voice(input) -> Optional[BytesIO]:
    sound = AudioSegment.from_file(input)
    silent_ranges = detect_silence(sound, min_silence_len=500, silence_thresh=-40)
    if len(silent_ranges) >= 1:
        first_silent_end = silent_ranges[0][1] - 300
        result = sound[first_silent_end:] + AudioSegment.silent(300)
        output = BytesIO()
        result.export(output, format="mp3")
        return output
    return None

def is_number(s: str) -> bool:
    """
    说明：
        检测 s 是否为数字
    参数：
        :param s: 文本
    """
    try:
        float(s)
        return True
    except ValueError:
        pass
    try:
        import unicodedata

        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass
    return False
