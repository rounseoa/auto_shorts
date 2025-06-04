from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from moviepy.video.io.ImageSequenceClip import ImageSequenceClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
from gtts import gTTS
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os, tempfile
import asyncio
import edge_tts

app = Flask(__name__)
CORS(app)

FONT_PATH = "fonts/나눔손글씨 사랑해 아들.ttf"

def get_font(size, bold):
    try:
        return ImageFont.truetype(FONT_PATH, size + 10)  # 얇은 글씨 대비 가시성 보정
    except:
        return ImageFont.load_default()

async def generate_edge_tts(text, voice, path):
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(path)

@app.route("/preview-voice", methods=["POST"])
def preview_voice():
    voice_engine = request.json.get("voiceEngine", "gtts")
    edge_voice = request.json.get("edgeVoice", "ko-KR-SunHiNeural")
    text = "안녕하세요. 테스트입니다."
    temp_dir = tempfile.mkdtemp()
    tts_path = os.path.join(temp_dir, "sample.mp3")

    try:
        if voice_engine in ["gtts", "google"]:
            gTTS(text=text, lang='ko').save(tts_path)
        elif voice_engine == "edge":
            asyncio.run(generate_edge_tts(text, edge_voice, tts_path))
        else:
            return jsonify({"error": "지원하지 않는 TTS 엔진"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return send_file(tts_path, mimetype="audio/mpeg")

@app.route("/generate", methods=["POST"])
def generate_video():
    try:
        texts = request.form.getlist("texts")
        positions = request.form.getlist("positions")
        bgColors = request.form.getlist("bgColors")
        fontColors = request.form.getlist("fontColors")
        fontSizes = request.form.getlist("fontSizes")
        bolds = request.form.getlist("bolds")
        titles = request.form.getlist("titles")
        titlePositions = request.form.getlist("titlePositions")
        titleColors = request.form.getlist("titleColors")
        titleBgColors = request.form.getlist("titleBgColors")
        titleSizes = request.form.getlist("titleSizes")
        titleBolds = request.form.getlist("titleBolds")
        images = request.files.getlist("images")
        voice_engine = request.form.get("voiceEngine", "gtts")
        edge_voice = request.form.get("edgeVoice", "ko-KR-SunHiNeural")

        if any(len(lst) != len(texts) for lst in [positions, bgColors, fontColors, fontSizes, bolds, titles, titlePositions, titleColors, titleBgColors, titleSizes, titleBolds]):
            return {"error": "입력 항목 갯수가 일치하지 않습니다."}, 400

        temp_dir = tempfile.mkdtemp()
        audio_path = os.path.join(temp_dir, "tts.mp3")
        output_path = os.path.join(temp_dir, "result.mp4")

        combined_text = ". ".join(texts)
        try:
            if voice_engine in ["gtts", "google"]:
                gTTS(text=combined_text, lang='ko').save(audio_path)
            elif voice_engine == "edge":
                asyncio.run(generate_edge_tts(combined_text, edge_voice, audio_path))
            else:
                return jsonify({"error": "지원하지 않는 TTS 엔진"}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        audio = AudioFileClip(audio_path)
        segment_duration = audio.duration / len(texts)
        fps = 24
        frames = []

        for i in range(len(texts)):
            img = Image.open(images[i]).convert("RGB")
            bg = Image.new("RGB", (608, 1080), color="black")
            img.thumbnail((608, 1080))
            x = (608 - img.width) // 2
            y = (1080 - img.height) // 2
            bg.paste(img, (x, y))
            draw = ImageDraw.Draw(bg)

            # 자막
            line = texts[i]
            font = get_font(int(fontSizes[i]), bolds[i] == 'true')
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = (608 - text_width) // 2
            text_y = int((1080 - text_height) * int(positions[i]) / 10)

            if bgColors[i] != 'transparent':
                draw.rectangle([
                    (text_x - 8, text_y - 4),
                    (text_x + text_width + 8, text_y + text_height + 4)
                ], fill=bgColors[i])

            draw.text((text_x, text_y), line, fill=fontColors[i], font=font)

            # 제목
            title = titles[i]
            if title:
                title_font = get_font(int(titleSizes[i]), titleBolds[i] == 'true')
                tbbox = draw.textbbox((0, 0), title, font=title_font)
                t_width = tbbox[2] - tbbox[0]
                t_height = tbbox[3] - tbbox[1]
                tx = (608 - t_width) // 2
                ty = int((1080 - t_height) * int(titlePositions[i]) / 10)

                if titleBgColors[i] != 'transparent':
                    draw.rectangle([
                        (tx - 8, ty - 4),
                        (tx + t_width + 8, ty + t_height + 4)
                    ], fill=titleBgColors[i])

                draw.text((tx, ty), title, fill=titleColors[i], font=title_font)

            frame_np = np.array(bg)
            frames.extend([frame_np] * int(segment_duration * fps))

        clip = ImageSequenceClip(frames, fps=fps)
        clip.audio = audio
        clip.write_videofile(output_path, fps=24)

        return send_file(output_path, as_attachment=True, download_name="shorts.mp4")

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}, 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)