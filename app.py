from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from moviepy.editor import CompositeVideoClip, ImageClip, AudioFileClip, TextClip
from gtts import gTTS
import asyncio, edge_tts
from PIL import Image, ImageFont, ImageDraw
import numpy as np
import os, tempfile

app = Flask(__name__)
CORS(app)

FONT_PATH = "fonts/나눔손글씨 사랑해 아들.ttf"

def get_font(size):
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except:
        return ImageFont.load_default()

async def generate_edge_tts(text, voice, path):
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(path)

@app.route("/preview-voice", methods=["POST"])
def preview_voice():
    voice_engine = request.json.get("voiceEngine", "gtts")
    edge_voice = request.json.get("edgeVoice", "ko-KR-SunHiNeural")
    text = request.json.get("text", "안녕하세요. 테스트입니다.")
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
        starts = [float(x) for x in request.form.getlist("starts")]
        durations = [float(x) for x in request.form.getlist("durations")]
        positions = request.form.getlist("positions")
        fontSizes = request.form.getlist("fontSizes")
        fontColors = request.form.getlist("fontColors")
        bgColors = request.form.getlist("bgColors")
        bolds = request.form.getlist("bolds")

        title = request.form.get("title", "")
        author = request.form.get("author", "")
        views = request.form.get("views", "")
        titleSize = int(request.form.get("titleSize", "40"))
        titleColor = request.form.get("titleColor", "white")
        titlePosition = int(request.form.get("titlePosition", "1"))

        bg_image = request.files["background"]
        images = request.files.getlist("images")

        voice_engine = request.form.get("voiceEngine", "gtts")
        edge_voice = request.form.get("edgeVoice", "ko-KR-SunHiNeural")

        temp_dir = tempfile.mkdtemp()
        audio_path = os.path.join(temp_dir, "tts.mp3")
        output_path = os.path.join(temp_dir, "result.mp4")

        combined_text = ". ".join(texts)
        if voice_engine in ["gtts", "google"]:
            gTTS(text=combined_text, lang="ko").save(audio_path)
        elif voice_engine == "edge":
            asyncio.run(generate_edge_tts(combined_text, edge_voice, audio_path))
        else:
            return jsonify({"error": "지원하지 않는 TTS 엔진"}), 400

        audio = AudioFileClip(audio_path)
        max_time = max([starts[i] + durations[i] for i in range(len(texts))])
        duration = max(audio.duration, max_time)
        fps = 24

        bg_img = Image.open(bg_image).convert("RGB").resize((608, 1080))
        bg_base_np = np.array(bg_img)

        def draw_top_labels(img_np):
            img = Image.fromarray(img_np)
            draw = ImageDraw.Draw(img)
            font = get_font(titleSize)
            y = int((1080 - font.size) * titlePosition / 10)
            if title:
                draw.text((30, y), f"#{title}", font=font, fill=titleColor)
            if author:
                draw.text((30, y + 60), f"작성자: {author}", font=font, fill=titleColor)
            if views:
                draw.text((30, y + 120), f"조회수: {views}", font=font, fill=titleColor)
            return np.array(img)

        clips = []
        bg_with_text = draw_top_labels(bg_base_np)

        for i, line in enumerate(texts):
            frame = Image.fromarray(bg_with_text.copy())

            if i < len(images):
                over_img = Image.open(images[i]).convert("RGBA")
                over_img.thumbnail((600, 600))
                x = (608 - over_img.width) // 2
                y = (1080 - over_img.height) // 2
                frame.paste(over_img, (x, y), over_img)

            draw = ImageDraw.Draw(frame)
            font = get_font(int(fontSizes[i]))
            bbox = draw.textbbox((0, 0), line, font=font)
            text_x = (608 - (bbox[2] - bbox[0])) // 2
            text_y = int((1080 - (bbox[3] - bbox[1])) * int(positions[i]) / 10)
            if bgColors[i] != 'transparent':
                draw.rectangle([(text_x - 10, text_y - 10), (text_x + bbox[2] - bbox[0] + 10, text_y + bbox[3] - bbox[1] + 10)], fill=bgColors[i])
            draw.text((text_x, text_y), line, font=font, fill=fontColors[i])

            np_frame = np.array(frame.convert("RGB"))
            img_clip = ImageClip(np_frame).set_duration(durations[i]).set_start(starts[i])
            clips.append(img_clip)

        final = CompositeVideoClip(clips, size=(608, 1080)).set_audio(audio)
        final.write_videofile(output_path, fps=fps)

        return send_file(output_path, as_attachment=True, download_name="shorts.mp4")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}, 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
