import whisper
def transcribe(audio_path, language="ja", model_size="small"):
    model = whisper.load_model(model_size)
    result = model.transcribe(audio_path, language=language, verbose=False)
    segs = []
    for s in result.get("segments", []):
        segs.append({"start": float(s["start"]), "end": float(s["end"]), "text": s["text"].strip()})
    return segs
