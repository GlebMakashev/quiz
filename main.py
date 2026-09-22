import os, io, json, random, threading
import tkinter as tk
from tkinter import messagebox
import sounddevice as sd
import scipy.io.wavfile as wav
import speech_recognition as sr
from googletrans import Translator
from gtts import gTTS

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

duration, sample_rate = 5, 44100
pygame.mixer.init()
recognizer, translator = sr.Recognizer(), Translator()

lang_code, speech_code, words_by_level = "en", "en-US", {}
words, word_iterator, current_word_foreign = [], None, ""
score, used_hint = 0, False  

BG_MAIN, FG_TEXT, ACCENT_BLUE = "#0d1117", "#ffffff", "#58a6ff"
COLOR_EASY, COLOR_MEDIUM, COLOR_HARD, BG_BTN_ACTIVE = "#56d364", "#f0883e", "#ff7b72", "#21262d"

def speak_word(text):
    try:
        tts = gTTS(text=text, lang=lang_code)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        pygame.mixer.music.load(fp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy(): pygame.time.Clock().tick(10)
    except Exception as e: print("Ошибка озвучки:", e)

def translate_word_async():
    global current_word_foreign
    try:
        res = translator.translate(current_word_foreign, src=lang_code, dest='ru')
        root.after(0, lambda: word_label.config(text=res.text.upper()))
        root.after(0, lambda: status_label.config(text="Назовите перевод на выбранном языке", fg="#8b949e"))
        root.after(0, lambda: btn_record.config(state=tk.NORMAL, bg=COLOR_HARD))
        root.after(0, lambda: btn_hint.config(state=tk.NORMAL, bg=COLOR_MEDIUM))
    except Exception as e:
        root.after(0, lambda: word_label.config(text=current_word_foreign.upper() + " (Ошибка сети)"))
        root.after(0, lambda: btn_record.config(state=tk.NORMAL, bg=COLOR_HARD))

def next_word():
    global current_word_foreign, used_hint
    try:
        current_word_foreign = next(word_iterator).lower().strip()
        used_hint = False  
        word_label.config(text="...")
        hint_label.config(text="")
        status_label.config(text="Загрузка перевода...", fg=ACCENT_BLUE)
        btn_record.config(state=tk.DISABLED, bg="#21262d")
        btn_hint.config(state=tk.DISABLED, bg="#21262d")
        threading.Thread(target=translate_word_async, daemon=True).start()
    except StopIteration:
        messagebox.showinfo("Конец раунда!", f"Игра окончена! Ваш счёт: {score} очков!")
        root.destroy()

def show_hint():
    global used_hint
    if used_hint: return
    w_len = len(current_word_foreign)
    if w_len <= 2:
        hint_label.config(text=current_word_foreign)
        return
    letters = list(current_word_foreign)
    hide_count = 1 if w_len < 5 else 2
    idxs = list(range(1, w_len - 1))
    if len(idxs) >= hide_count:
        for i in random.sample(idxs, hide_count): letters[i] = "_"
    hint_label.config(text=f"Подсказка: {' '.join(letters)}")
    used_hint = True
    btn_hint.config(state=tk.DISABLED, bg="#21262d")

def process_turn():
    global score
    btn_record.config(state=tk.DISABLED, bg="#21262d")
    btn_hint.config(state=tk.DISABLED, bg="#21262d")
    status_label.config(text="ГОВОРИТЕ...", fg=COLOR_HARD)
    rec = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")
    sd.wait()
    wav.write("output.wav", sample_rate, rec)
    status_label.config(text="Распознаём голос...", fg=ACCENT_BLUE)
    with sr.AudioFile("output.wav") as src: audio = recognizer.record(src)
    try:
        speech = recognizer.recognize_google(audio, language=speech_code).lower().strip()
        if speech == current_word_foreign:
            pts = 5 if used_hint else 10
            score += pts
            score_label.config(text=f"Очки: {score}")
            status_label.config(text=f"Верно! +{pts} очков. Вы сказали: '{speech}'", fg=COLOR_EASY)
        else:
            status_label.config(text=f"Неверно! Вы сказали: '{speech}'. Ожидалось: '{current_word_foreign}'", fg=COLOR_HARD)
            speak_word(current_word_foreign)
    except Exception:
        status_label.config(text=f"Речь не распознана. Ожидалось: '{current_word_foreign}'", fg=COLOR_HARD)
        speak_word(current_word_foreign)
    root.after(3000, next_word)

def start_recording_thread(): threading.Thread(target=process_turn, daemon=True).start()

def select_language(lang):
    global lang_code, speech_code, words_by_level
    mapping = {"en": ("en", "en-US", "words.txt"), "it": ("it", "it-IT", "words_IT.txt"), 
               "es": ("es", "es-ES", "words_ES.txt"), "fr": ("fr", "fr-FR", "words_FR.txt"),
               "de": ("de", "de-DE", "words_GER.txt"), "pt": ("pt", "pt-PT", "words_POR.txt")}
    lang_code, speech_code, file_name = mapping[lang]
    if not os.path.exists(file_name):
        messagebox.showerror("Ошибка!", f"Файл '{file_name}' не найден!")
        return
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if "words_by_level =" in content: content = content.split("words_by_level =", 1)[1].strip()
            words_by_level = json.loads(content)
        for w in start_window.winfo_children(): w.destroy()
        show_difficulty_selection()
    except Exception as e: messagebox.showerror("Ошибка!", f"Ошибка в {file_name}: {e}")

def start_game(lvl):
    global words, word_iterator
    words = words_by_level.get(lvl, [])
    if not words: return
    words = random.sample(words, 10) if len(words) > 10 else random.sample(words, len(words))
    word_iterator = iter(words)
    open_main_game_window()
    start_window.destroy()

def show_difficulty_selection():
    tk.Label(start_window, text="ВЫБОР СЛОЖНОСТИ", font=("Segoe UI", 18, "bold"), fg=ACCENT_BLUE, bg=BG_MAIN).pack(pady=20)
    tk.Label(start_window, text="Выберите уровень сложности:", font=("Segoe UI", 11), fg=FG_TEXT, bg=BG_MAIN).pack(pady=5)
    tk.Button(start_window, text="Easy", font=("Segoe UI", 11, "bold"), bg=COLOR_EASY, fg=BG_MAIN, width=22, bd=0, pady=6, command=lambda: start_game("easy")).pack(pady=8)
    tk.Button(start_window, text="Medium", font=("Arial", 11, "bold"), bg=COLOR_MEDIUM, fg=BG_MAIN, width=22, bd=0, pady=6, command=lambda: start_game("medium")).pack(pady=8)
    tk.Button(start_window, text="Hard", font=("Segoe UI", 11, "bold"), bg=COLOR_HARD, fg=BG_MAIN, width=22, bd=0, pady=6, command=lambda: start_game("hard")).pack(pady=8)

root, word_label, hint_label, status_label, score_label, btn_record, btn_hint = None, None, None, None, None, None, None

def open_main_game_window():
    global root, word_label, hint_label, status_label, score_label, btn_record, btn_hint
    root = tk.Toplevel()
    root.title("Language Learning Game")
    root.geometry("460x420")
    root.configure(bg=BG_MAIN)
    score_label = tk.Label(root, text=f"Очки: {score}", font=("Segoe UI", 14, "bold"), fg=ACCENT_BLUE, bg=BG_MAIN)
    score_label.pack(pady=10)
    word_label = tk.Label(root, text="", font=("Segoe UI", 28, "bold"), fg=FG_TEXT, bg=BG_MAIN)
    word_label.pack(pady=10)
    hint_label = tk.Label(root, text="", font=("Segoe UI", 16, "bold"), fg=COLOR_MEDIUM, bg=BG_MAIN)
    hint_label.pack(pady=5)
    status_label = tk.Label(root, text="", font=("Segoe UI", 11), fg="#8b949e", bg=BG_MAIN, wraplength=410)
    status_label.pack(pady=10)
    btn_record = tk.Button(root, text="ЗАПИСАТЬ ОТВЕТ", font=("Segoe UI", 12, "bold"), bg=COLOR_HARD, fg=BG_MAIN, bd=0, padx=25, pady=10, command=start_recording_thread)
    btn_record.pack(pady=10)
    btn_hint = tk.Button(root, text="ПОДСКАЗКА (-5 очков)", font=("Segoe UI", 11, "bold"), bg=COLOR_MEDIUM, fg=BG_MAIN, bd=0, padx=20, pady=8, command=show_hint)
    btn_hint.pack(pady=10)
    next_word()
    root.mainloop()

start_window = tk.Tk()
start_window.title("Настройки игры")
start_window.geometry("400x520")
start_window.configure(bg=BG_MAIN)
tk.Label(start_window, text="ВЫБОР ЯЗЫКА", font=("Segoe UI", 20, "bold"), fg=ACCENT_BLUE, bg=BG_MAIN).pack(pady=20)
tk.Label(start_window, text="Какой язык хотите учить?", font=("Segoe UI", 11), fg=FG_TEXT, bg=BG_MAIN).pack(pady=5)
tk.Button(start_window, text="ENGLISH", font=("Segoe UI", 11, "bold"), bg=ACCENT_BLUE, fg=BG_MAIN, width=24, bd=0, pady=6, command=lambda: select_language("en")).pack(pady=6)
tk.Button(start_window, text="ITALIANO", font=("Segoe UI", 11, "bold"), bg=COLOR_MEDIUM, fg=BG_MAIN, width=24, bd=0, pady=6, command=lambda: select_language("it")).pack(pady=6)
tk.Button(start_window, text="ESPAÑOL", font=("Segoe UI", 11, "bold"), bg=COLOR_EASY, fg=BG_MAIN, width=24, bd=0, pady=6, command=lambda: select_language("es")).pack(pady=6)
tk.Button(start_window, text="FRANÇAIS", font=("Segoe UI", 11, "bold"), bg="#a371f7", fg=BG_MAIN, width=24, bd=0, pady=6, command=lambda: select_language("fr")).pack(pady=6)
tk.Button(start_window, text="DEUTSCH", font=("Segoe UI", 11, "bold"), bg="#f1c40f", fg=BG_MAIN, width=24, bd=0, pady=6, command=lambda: select_language("de")).pack(pady=6)
tk.Button(start_window, text="PORTUGUÊS", font=("Segoe UI", 11, "bold"), bg="#1abc9c", fg=BG_MAIN, width=24, bd=0, pady=6, command=lambda: select_language("pt")).pack(pady=6)
start_window.mainloop()
